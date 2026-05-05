"""
OAuth 2.0 authentication for Zoho Campaigns.

On first run (setup mode), opens your browser to log in to Zoho and
automatically captures the token. Subsequent runs auto-refresh the token
silently — you never need to log in again.
"""

import json
import os
import sys
import time
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from threading import Event
from typing import Optional

import requests

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ZOHO_ACCOUNTS_URL = "https://accounts.zoho.com"
TOKEN_ENDPOINT = f"{ZOHO_ACCOUNTS_URL}/oauth/v2/token"
AUTH_ENDPOINT = f"{ZOHO_ACCOUNTS_URL}/oauth/v2/auth"

SCOPES = "ZohoCampaigns.campaign.ALL,ZohoCampaigns.contact.ALL"
REDIRECT_URI = "http://localhost:8080/callback"
CALLBACK_PORT = 8080

TOKEN_DIR = Path.home() / ".zoho_campaigns_mcp"
TOKEN_FILE = TOKEN_DIR / "tokens.json"


# ---------------------------------------------------------------------------
# Token storage
# ---------------------------------------------------------------------------

class TokenStore:
    """Persists OAuth tokens to ~/.zoho_campaigns_mcp/tokens.json."""

    def load(self) -> dict:
        if TOKEN_FILE.exists():
            try:
                with open(TOKEN_FILE) as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                return {}
        return {}

    def save(self, data: dict) -> None:
        TOKEN_DIR.mkdir(parents=True, exist_ok=True)
        with open(TOKEN_FILE, "w") as f:
            json.dump(data, f, indent=2)
        try:
            TOKEN_FILE.chmod(0o600)  # restrict read access (no-op on Windows)
        except (AttributeError, NotImplementedError, OSError):
            pass


# ---------------------------------------------------------------------------
# OAuth callback HTTP handler
# ---------------------------------------------------------------------------

_auth_code: Optional[str] = None
_auth_error: Optional[str] = None
_done_event = Event()


class _CallbackHandler(BaseHTTPRequestHandler):
    """Tiny HTTP server that captures the OAuth callback from Zoho."""

    def do_GET(self):
        global _auth_code, _auth_error
        parsed = urllib.parse.urlparse(self.path)
        params = dict(urllib.parse.parse_qsl(parsed.query))

        if parsed.path == "/callback":
            if "code" in params:
                _auth_code = params["code"]
                body = b"<html><body><h2>Success!</h2><p>Authorization complete. You can close this tab and return to the terminal.</p></body></html>"
                self.send_response(200)
            else:
                _auth_error = params.get("error", "unknown error")
                body = b"<html><body><h2>Authorization failed</h2><p>Please close this tab and check the terminal for details.</p></body></html>"
                self.send_response(400)

            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            _done_event.set()
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, fmt, *args):
        pass  # suppress request logs


# ---------------------------------------------------------------------------
# OAuth flow
# ---------------------------------------------------------------------------

def run_oauth_flow(client_id: str, client_secret: str) -> dict:
    """
    Opens the browser for Zoho login, waits for the callback, and returns
    a dict with access_token, refresh_token, and expires_at.
    """
    global _auth_code, _auth_error, _done_event
    _auth_code = None
    _auth_error = None
    _done_event = Event()

    # Build authorization URL
    auth_params = {
        "response_type": "code",
        "client_id": client_id,
        "scope": SCOPES,
        "redirect_uri": REDIRECT_URI,
        "access_type": "offline",
        "prompt": "consent",
    }
    auth_url = AUTH_ENDPOINT + "?" + urllib.parse.urlencode(auth_params)

    # Start local callback server
    server = HTTPServer(("localhost", CALLBACK_PORT), _CallbackHandler)
    server.timeout = 1  # 1-second poll so we can check _done_event

    print("\n  Opening your browser to log in to Zoho...")
    print("  If the browser does not open, copy this URL and paste it manually:")
    print(f"\n  {auth_url}\n")
    webbrowser.open(auth_url)

    print("  Waiting for you to authorize in the browser...", flush=True)
    timeout = 300  # 5 minutes
    elapsed = 0
    while not _done_event.is_set() and elapsed < timeout:
        server.handle_request()
        elapsed += 1

    server.server_close()

    if _auth_error:
        print(f"\n  Error from Zoho: {_auth_error}")
        sys.exit(1)
    if not _auth_code:
        print("\n  Timed out waiting for authorization. Please run setup.sh again.")
        sys.exit(1)

    # Exchange code for tokens
    print("  Authorization received! Exchanging for tokens...", flush=True)
    resp = requests.post(TOKEN_ENDPOINT, data={
        "grant_type": "authorization_code",
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": REDIRECT_URI,
        "code": _auth_code,
    }, timeout=30)

    if resp.status_code != 200:
        print(f"\n  Token exchange failed ({resp.status_code}): {resp.text}")
        sys.exit(1)

    token_data = resp.json()
    if "error" in token_data:
        print(f"\n  Token error: {token_data['error']}")
        sys.exit(1)

    expires_in = int(token_data.get("expires_in", 3600))
    return {
        "access_token": token_data["access_token"],
        "refresh_token": token_data["refresh_token"],
        "expires_at": time.time() + expires_in - 60,  # 60s buffer
        "client_id": client_id,
        "client_secret": client_secret,
    }


# ---------------------------------------------------------------------------
# Token refresh
# ---------------------------------------------------------------------------

def refresh_access_token(tokens: dict) -> dict:
    """Uses the refresh token to get a new access token. Updates tokens dict."""
    resp = requests.post(TOKEN_ENDPOINT, data={
        "grant_type": "refresh_token",
        "client_id": tokens["client_id"],
        "client_secret": tokens["client_secret"],
        "refresh_token": tokens["refresh_token"],
    }, timeout=30)

    if resp.status_code != 200:
        raise RuntimeError(f"Token refresh failed ({resp.status_code}): {resp.text}")

    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"Token refresh error: {data['error']}")

    expires_in = int(data.get("expires_in", 3600))
    tokens["access_token"] = data["access_token"]
    tokens["expires_at"] = time.time() + expires_in - 60
    return tokens


def get_valid_token(store: TokenStore) -> str:
    """
    Returns a valid access token, refreshing automatically if expired.
    Raises RuntimeError if no tokens are saved (setup not run yet).
    """
    tokens = store.load()
    if not tokens or "access_token" not in tokens:
        raise RuntimeError(
            "No credentials found. Please run setup.sh first to authenticate with Zoho."
        )

    if time.time() >= tokens.get("expires_at", 0):
        tokens = refresh_access_token(tokens)
        store.save(tokens)

    return tokens["access_token"]


# ---------------------------------------------------------------------------
# CLI entry point (called by setup.sh)
# ---------------------------------------------------------------------------

def setup_command(client_id: str, client_secret: str) -> None:
    """Run the full OAuth flow and save tokens. Called during setup."""
    tokens = run_oauth_flow(client_id, client_secret)
    store = TokenStore()
    store.save(tokens)
    print(f"\n  Tokens saved to {TOKEN_FILE}")


if __name__ == "__main__":
    if len(sys.argv) == 3:
        setup_command(sys.argv[1], sys.argv[2])
    else:
        print("Usage: python -m zoho_campaigns_mcp.auth <client_id> <client_secret>")
        sys.exit(1)
