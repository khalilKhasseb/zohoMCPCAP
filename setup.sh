#!/usr/bin/env bash
# =============================================================================
#  Zoho Campaigns MCP Server — Setup Script
#  Run once: bash setup.sh
#  Works on macOS. No technical knowledge required.
# =============================================================================

set -euo pipefail

# ── Colours ──────────────────────────────────────────────────────────────────
BOLD="\033[1m"
GREEN="\033[0;32m"
YELLOW="\033[0;33m"
RED="\033[0;31m"
CYAN="\033[0;36m"
RESET="\033[0m"

ok()   { echo -e "  ${GREEN}✓${RESET}  $*"; }
info() { echo -e "  ${CYAN}→${RESET}  $*"; }
warn() { echo -e "  ${YELLOW}!${RESET}  $*"; }
die()  { echo -e "\n  ${RED}✗  Error:${RESET} $*\n"; exit 1; }

# ── Header ───────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}  ╔══════════════════════════════════════════╗${RESET}"
echo -e "${BOLD}  ║   Zoho Campaigns MCP — Setup Wizard      ║${RESET}"
echo -e "${BOLD}  ╚══════════════════════════════════════════╝${RESET}"
echo ""
info "This script will set up everything for you — no technical knowledge needed."
info "It will take about 2–3 minutes."
echo ""

# ── macOS check ──────────────────────────────────────────────────────────────
if [[ "$(uname)" != "Darwin" ]]; then
  die "This setup script is designed for macOS. Detected: $(uname)"
fi

# ── Locate the project directory ─────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ── Step 1: Check Python ──────────────────────────────────────────────────────
echo -e "${BOLD}  Step 1/5 — Checking Python${RESET}"

PYTHON=""
for cmd in python3.12 python3.11 python3.10 python3.9 python3.8 python3; do
  if command -v "$cmd" &>/dev/null; then
    VERSION=$("$cmd" --version 2>&1 | awk '{print $2}')
    MAJOR=$(echo "$VERSION" | cut -d. -f1)
    MINOR=$(echo "$VERSION" | cut -d. -f2)
    if [[ "$MAJOR" -ge 3 && "$MINOR" -ge 8 ]]; then
      PYTHON="$cmd"
      break
    fi
  fi
done

if [[ -z "$PYTHON" ]]; then
  warn "Python 3.8 or newer is required but was not found."
  echo ""
  echo "  Please install Python:"
  echo "  1. Open your browser and go to: https://www.python.org/downloads/"
  echo "  2. Click the big yellow 'Download Python' button"
  echo "  3. Open the downloaded file and follow the installer"
  echo "  4. Come back here and run: bash setup.sh"
  echo ""
  die "Python not found. Please install it and re-run this script."
fi

ok "Python found: $("$PYTHON" --version)"

# ── Step 2: Install uv ───────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}  Step 2/5 — Installing uv (Python package manager)${RESET}"

if command -v uv &>/dev/null; then
  ok "uv already installed: $(uv --version)"
  UV_CMD="uv"
else
  info "Installing uv..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  # Add to current shell path
  export PATH="$HOME/.cargo/bin:$HOME/.local/bin:$PATH"
  if command -v uv &>/dev/null; then
    UV_CMD="uv"
    ok "uv installed successfully"
  else
    die "uv installation failed. Please check your internet connection and try again."
  fi
fi

# ── Step 3: Install dependencies ─────────────────────────────────────────────
echo ""
echo -e "${BOLD}  Step 3/5 — Installing dependencies${RESET}"
info "This downloads the required Python packages..."

"$UV_CMD" sync --project "$SCRIPT_DIR" 2>&1 | sed 's/^/    /'
ok "Dependencies installed"

# ── Step 4: Zoho API client credentials ──────────────────────────────────────
echo ""
echo -e "${BOLD}  Step 4/5 — Zoho API Credentials${RESET}"
echo ""
echo "  You need to create a free Zoho API client. Here's how:"
echo ""
echo "  ┌─────────────────────────────────────────────────────────┐"
echo "  │  1. Your browser will open Zoho API Console             │"
echo "  │  2. Click  [ + ADD CLIENT ]                             │"
echo "  │  3. Click  [ Self Client ]  then  [ CREATE ]            │"
echo "  │  4. Under 'Client Details' you will see:                │"
echo "  │       • Client ID      ← copy this                      │"
echo "  │       • Client Secret  ← copy this                      │"
echo "  │  5. Come back here and paste them when asked            │"
echo "  └─────────────────────────────────────────────────────────┘"
echo ""

read -rp "  Press ENTER to open the Zoho API Console in your browser..."
open "https://api-console.zoho.com"

echo ""
echo "  (The page opened in your browser. Follow the 5 steps above.)"
echo ""

# Read Client ID
while true; do
  read -rp "  Paste your Client ID here and press ENTER: " CLIENT_ID
  CLIENT_ID="$(echo -e "${CLIENT_ID}" | tr -d '[:space:]')"
  if [[ -n "$CLIENT_ID" ]]; then
    break
  fi
  warn "Client ID cannot be empty. Please try again."
done

# Read Client Secret (masked)
while true; do
  read -rsp "  Paste your Client Secret here and press ENTER: " CLIENT_SECRET
  echo ""
  CLIENT_SECRET="$(echo -e "${CLIENT_SECRET}" | tr -d '[:space:]')"
  if [[ -n "$CLIENT_SECRET" ]]; then
    break
  fi
  warn "Client Secret cannot be empty. Please try again."
done

ok "Credentials received"

# ── Step 5: OAuth — open browser and capture token ───────────────────────────
echo ""
echo -e "${BOLD}  Step 5/5 — Connecting to your Zoho Account${RESET}"
echo ""
info "Your browser will open for Zoho login. Log in and click 'Accept'."
info "The script will finish automatically after you approve access."
echo ""

"$UV_CMD" run --project "$SCRIPT_DIR" python -m zoho_campaigns_mcp.auth "$CLIENT_ID" "$CLIENT_SECRET"

ok "Connected to Zoho Campaigns!"

# ── Configure Claude Desktop ──────────────────────────────────────────────────
echo ""
info "Configuring Claude Desktop..."

CLAUDE_CONFIG_DIR="$HOME/Library/Application Support/Claude"
CLAUDE_CONFIG_FILE="$CLAUDE_CONFIG_DIR/claude_desktop_config.json"
UV_PATH="$(command -v uv)"

# Find the installed zoho-campaigns-mcp script
MCP_SCRIPT="$SCRIPT_DIR/.venv/bin/zoho-campaigns-mcp"
if [[ ! -f "$MCP_SCRIPT" ]]; then
  # uv may place it in a different location
  MCP_SCRIPT="$("$UV_CMD" run --project "$SCRIPT_DIR" which zoho-campaigns-mcp 2>/dev/null || true)"
fi

# Build the server config entry as a JSON fragment
SERVER_ENTRY=$(cat <<EOF
{
  "command": "$UV_PATH",
  "args": ["run", "--project", "$SCRIPT_DIR", "zoho-campaigns-mcp"],
  "env": {
    "ZOHO_CLIENT_ID": "$CLIENT_ID",
    "ZOHO_CLIENT_SECRET": "$CLIENT_SECRET"
  }
}
EOF
)

# Create config dir if needed
mkdir -p "$CLAUDE_CONFIG_DIR"

if [[ ! -f "$CLAUDE_CONFIG_FILE" ]]; then
  # No config file yet — create a fresh one
  cat > "$CLAUDE_CONFIG_FILE" <<EOF
{
  "mcpServers": {
    "zoho-campaigns": $SERVER_ENTRY
  }
}
EOF
  ok "Created Claude Desktop config"
else
  # Config file exists — merge in our server entry using Python
  "$PYTHON" - <<PYEOF
import json, sys

config_file = "$CLAUDE_CONFIG_FILE"
with open(config_file) as f:
    config = json.load(f)

if "mcpServers" not in config:
    config["mcpServers"] = {}

config["mcpServers"]["zoho-campaigns"] = json.loads('''$SERVER_ENTRY''')

with open(config_file, "w") as f:
    json.dump(config, f, indent=2)

print("  Config updated successfully")
PYEOF
  ok "Updated Claude Desktop config"
fi

# ── Done! ────────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}${GREEN}  ══════════════════════════════════════════${RESET}"
echo -e "${BOLD}${GREEN}    Setup complete!                          ${RESET}"
echo -e "${BOLD}${GREEN}  ══════════════════════════════════════════${RESET}"
echo ""
echo "  What to do next:"
echo "  1. Quit Claude Desktop completely (if it's open)"
echo "  2. Reopen Claude Desktop"
echo "  3. Start a new conversation and try:"
echo "       'List my Zoho Campaigns mailing lists'"
echo "       'Show me my recent campaigns'"
echo ""
echo "  If something goes wrong, re-run this script: bash setup.sh"
echo ""
