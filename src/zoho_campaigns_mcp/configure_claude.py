"""
Writes (or merges) the zoho-campaigns entry into Claude Desktop's
claude_desktop_config.json. Used by setup.ps1 / setup.sh after OAuth
succeeds, and re-runnable on its own.

Usage:
    python -m zoho_campaigns_mcp.configure_claude <uv_path> <project_dir>

Reads client_id / client_secret from ~/.zoho_campaigns_mcp/tokens.json
(written during OAuth) so credentials never need to be passed on the CLI.
"""

import json
import os
import platform
import sys
from pathlib import Path

from .auth import TOKEN_FILE


def claude_config_path() -> Path:
    if platform.system() == "Windows":
        base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        return Path(base) / "Claude" / "claude_desktop_config.json"
    if platform.system() == "Darwin":
        return Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    # Linux fallback (Claude Desktop is unofficial here, but keep it sensible)
    return Path.home() / ".config" / "Claude" / "claude_desktop_config.json"


def load_existing_config(path: Path) -> dict:
    if not path.exists():
        return {}
    raw = path.read_bytes()
    # Strip UTF-8 BOM if present (PowerShell's Set-Content -Encoding UTF8 writes one)
    if raw.startswith(b"\xef\xbb\xbf"):
        raw = raw[3:]
    text = raw.decode("utf-8").strip()
    if not text:
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        print(f"  Warning: existing config at {path} is not valid JSON ({e}).")
        print("  Backing it up and starting fresh.")
        backup = path.with_suffix(path.suffix + ".bak")
        path.replace(backup)
        print(f"  Backup written to: {backup}")
        return {}


def main(uv_path: str, project_dir: str) -> int:
    if not TOKEN_FILE.exists():
        print(f"  No tokens found at {TOKEN_FILE}. Run setup first to authenticate.")
        return 1

    with open(TOKEN_FILE) as f:
        tokens = json.load(f)

    client_id = tokens.get("client_id")
    client_secret = tokens.get("client_secret")
    if not client_id or not client_secret:
        print("  tokens.json is missing client_id / client_secret. Re-run setup.")
        return 1

    server_entry = {
        "command": uv_path,
        "args": ["run", "--project", project_dir, "--python", "3.11", "zoho-campaigns-mcp"],
        "env": {
            "ZOHO_CLIENT_ID": client_id,
            "ZOHO_CLIENT_SECRET": client_secret,
        },
    }

    config_path = claude_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)

    config = load_existing_config(config_path)
    config.setdefault("mcpServers", {})
    if not isinstance(config["mcpServers"], dict):
        # Existing value is malformed — replace it.
        config["mcpServers"] = {}
    config["mcpServers"]["zoho-campaigns"] = server_entry

    # Write WITHOUT a BOM so future merges (PowerShell or Python) round-trip cleanly.
    config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    print(f"  Claude Desktop config written: {config_path}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python -m zoho_campaigns_mcp.configure_claude <uv_path> <project_dir>")
        sys.exit(1)
    sys.exit(main(sys.argv[1], sys.argv[2]))
