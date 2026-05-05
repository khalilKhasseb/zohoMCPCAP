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

# Look for an explicitly-versioned python3.X. We avoid bare `python3` because
# on macOS Catalina (2012-iMac territory) without Xcode Command Line Tools
# installed, /usr/bin/python3 is a stub that pops up a blocking GUI install
# dialog the moment you invoke it. uv will pin its own Python 3.11 anyway,
# so we don't actually need a system Python — this check is informational.
PYTHON=""
for cmd in python3.13 python3.12 python3.11 python3.10 python3.9 python3.8; do
  if command -v "$cmd" &>/dev/null; then
    PYTHON="$cmd"
    break
  fi
done

if [[ -n "$PYTHON" ]]; then
  PY_VERSION="$("$PYTHON" --version 2>/dev/null || true)"
  if [[ -n "$PY_VERSION" ]]; then
    ok "Python found: $PY_VERSION (uv will use its own Python 3.11 for the server)"
  else
    ok "uv will install Python 3.11 (no usable system Python detected)"
  fi
else
  ok "uv will install Python 3.11 automatically (no system Python needed)"
fi

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
info "This downloads Python 3.11 and required packages (first run may take ~1 minute)..."

"$UV_CMD" python install 3.11 2>&1 | sed 's/^/    /'
"$UV_CMD" sync --project "$SCRIPT_DIR" --python 3.11 2>&1 | sed 's/^/    /'
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

"$UV_CMD" run --project "$SCRIPT_DIR" --python 3.11 python -m zoho_campaigns_mcp.auth "$CLIENT_ID" "$CLIENT_SECRET"

ok "Connected to Zoho Campaigns!"

# ── Configure Claude Desktop ──────────────────────────────────────────────────
echo ""
info "Configuring Claude Desktop..."

UV_PATH="$(command -v uv)"

# JSON merge in shell + heredoc-Python is fragile (quoting, BOMs, system python
# being a Catalina/CLT stub). Delegate to the configure_claude module, which
# reads tokens.json on disk and writes claude_desktop_config.json
# deterministically. We call it through uv's pinned Python 3.11 so we never
# rely on whatever /usr/bin/python3 happens to be.
if "$UV_CMD" run --project "$SCRIPT_DIR" --python 3.11 \
      python -m zoho_campaigns_mcp.configure_claude "$UV_PATH" "$SCRIPT_DIR"; then
  ok "Claude Desktop config updated"
else
  warn "Could not update Claude Desktop config automatically."
  echo ""
  echo "  Add this manually under 'mcpServers' in:"
  echo "    $HOME/Library/Application Support/Claude/claude_desktop_config.json"
  echo ""
  echo "    \"zoho-campaigns\": {"
  echo "      \"command\": \"$UV_PATH\","
  echo "      \"args\": [\"run\", \"--project\", \"$SCRIPT_DIR\", \"--python\", \"3.11\", \"zoho-campaigns-mcp\"],"
  echo "      \"env\": { \"ZOHO_CLIENT_ID\": \"<your id>\", \"ZOHO_CLIENT_SECRET\": \"<your secret>\" }"
  echo "    }"
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
