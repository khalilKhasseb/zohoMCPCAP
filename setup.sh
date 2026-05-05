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

# ── Pre-flight: Claude Desktop installed? ────────────────────────────────────
# Not a hard block (the friend may install Claude after this script), but a
# clear warning beats a silent config-orphan they can't diagnose later.
CLAUDE_APP_FOUND=""
for path in "/Applications/Claude.app" "$HOME/Applications/Claude.app"; do
  if [[ -d "$path" ]]; then
    CLAUDE_APP_FOUND="$path"
    break
  fi
done

if [[ -z "$CLAUDE_APP_FOUND" ]]; then
  warn "Claude Desktop does not appear to be installed yet."
  echo "    Download it from: https://claude.ai/download"
  echo "    The script will continue — install Claude before the final step."
  echo ""
fi

# ── Pre-flight: basic internet reachability ──────────────────────────────────
# A bare 'curl | sh' for uv just dies silently with set -euo pipefail when
# the network is down. Catch it early with a friendly message.
if ! command -v uv &>/dev/null; then
  if ! curl -fsSI --max-time 5 https://astral.sh/uv/install.sh >/dev/null 2>&1; then
    die "Cannot reach the internet (or astral.sh is blocked). Connect to Wi-Fi or Ethernet and re-run this script."
  fi
fi

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
  # Wrap the install pipe in an explicit success-check so a network blip
  # produces a clear message instead of a silent set -e abort.
  set +e
  curl -LsSf https://astral.sh/uv/install.sh | sh
  INSTALL_RC=$?
  set -e
  # Add to current shell path
  export PATH="$HOME/.cargo/bin:$HOME/.local/bin:$PATH"
  if [[ $INSTALL_RC -ne 0 ]]; then
    die "Could not download uv. Please check your internet connection (Wi-Fi or Ethernet) and try again."
  fi
  if command -v uv &>/dev/null; then
    UV_CMD="uv"
    ok "uv installed successfully"
  else
    die "uv installed but isn't on PATH yet. Please close this Terminal window, open a new one, and re-run: bash setup.sh"
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
echo ""
info "Heads up: the next prompt will hide what you type for security."
info "Just paste your Client Secret and press ENTER — you won't see characters appear."
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

# Re-check now in case the friend installed Claude Desktop while OAuth ran.
if [[ -z "$CLAUDE_APP_FOUND" ]]; then
  for path in "/Applications/Claude.app" "$HOME/Applications/Claude.app"; do
    if [[ -d "$path" ]]; then
      CLAUDE_APP_FOUND="$path"
      break
    fi
  done
fi

if [[ -z "$CLAUDE_APP_FOUND" ]]; then
  echo "  IMPORTANT: Claude Desktop is not installed yet."
  echo ""
  echo "  Next steps:"
  echo "  1. Download Claude Desktop:  https://claude.ai/download"
  echo "  2. Install and open it once."
  echo "  3. Quit Claude Desktop completely (right-click Dock icon → Quit)."
  echo "  4. Reopen Claude Desktop."
  echo "  5. Start a new conversation and try:"
  echo "       'List my Zoho Campaigns mailing lists'"
else
  echo "  What to do next:"
  echo "  1. Quit Claude Desktop completely (right-click Dock icon → Quit, not just close the window)."
  echo "  2. Reopen Claude Desktop."
  echo "  3. Start a new conversation and try:"
  echo "       'List my Zoho Campaigns mailing lists'"
  echo "       'Show me my recent campaigns'"
fi

echo ""
echo "  If something goes wrong, re-run this script: bash setup.sh"
echo ""
