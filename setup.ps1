# =============================================================================
#  Zoho Campaigns MCP Server — Windows Setup Script
#  How to run: Right-click this file → "Run with PowerShell"
#  Or in PowerShell: powershell -ExecutionPolicy Bypass -File setup.ps1
# =============================================================================

Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force
$ErrorActionPreference = "Stop"

# ── Helpers ───────────────────────────────────────────────────────────────────
function Write-Ok   { param($msg) Write-Host "  [OK]  $msg" -ForegroundColor Green }
function Write-Info { param($msg) Write-Host "  -->   $msg" -ForegroundColor Cyan }
function Write-Warn { param($msg) Write-Host "  [!]   $msg" -ForegroundColor Yellow }
function Write-Die  { param($msg) Write-Host "`n  [ERR] $msg`n" -ForegroundColor Red; Read-Host "Press ENTER to exit"; exit 1 }

# ── Header ────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "  +==========================================+" -ForegroundColor White
Write-Host "  |   Zoho Campaigns MCP - Setup Wizard      |" -ForegroundColor White
Write-Host "  +==========================================+" -ForegroundColor White
Write-Host ""
Write-Info "This script will set up everything for you - no technical knowledge needed."
Write-Info "It will take about 2-3 minutes."
Write-Host ""

# ── Windows check ─────────────────────────────────────────────────────────────
if ($env:OS -ne "Windows_NT") {
    Write-Die "This script is for Windows. Mac users should run: bash setup.sh"
}

# ── Locate project directory ──────────────────────────────────────────────────
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

# ── Step 1: Check Python (uv will manage it, but note any existing install) ───
Write-Host "  Step 1/5 - Checking Python" -ForegroundColor White

$PythonCmd = $null
foreach ($cmd in @("python3", "python")) {
    if (Get-Command $cmd -ErrorAction SilentlyContinue) {
        $PythonCmd = $cmd
        break
    }
}

if ($PythonCmd) {
    $PythonVersion = (& $PythonCmd --version 2>&1).ToString().Trim()
    Write-Ok "Python found: $PythonVersion (uv will use Python 3.11 for the server)"
} else {
    Write-Ok "No system Python found - uv will download Python 3.11 automatically"
}

# ── Step 2: Install uv ────────────────────────────────────────────────────────
Write-Host ""
Write-Host "  Step 2/5 - Installing uv (Python package manager)" -ForegroundColor White

$UvCmd = $null
if (Get-Command uv -ErrorAction SilentlyContinue) {
    $UvCmd = "uv"
    Write-Ok "uv already installed: $(uv --version)"
} else {
    Write-Info "Installing uv..."
    try {
        Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression
        # Refresh PATH for current session
        $UserPath = [System.Environment]::GetEnvironmentVariable("PATH", "User")
        $env:PATH = "$UserPath;$env:PATH"
        if (Get-Command uv -ErrorAction SilentlyContinue) {
            $UvCmd = "uv"
            Write-Ok "uv installed successfully"
        } else {
            Write-Die "uv was installed but could not be found. Please restart PowerShell and re-run this script."
        }
    } catch {
        Write-Die "uv installation failed: $_. Please check your internet connection and try again."
    }
}

# ── Step 3: Install dependencies ──────────────────────────────────────────────
Write-Host ""
Write-Host "  Step 3/5 - Installing dependencies" -ForegroundColor White
Write-Info "Downloading Python 3.11 and required packages (first run may take ~1 minute)..."

& $UvCmd python install 3.11
if ($LASTEXITCODE -ne 0) { Write-Die "Failed to install Python 3.11. Check your internet connection." }

& $UvCmd sync --project $ScriptDir --python 3.11
if ($LASTEXITCODE -ne 0) { Write-Die "Failed to install dependencies." }

Write-Ok "Dependencies installed"

# ── Step 4: Zoho API credentials ──────────────────────────────────────────────
Write-Host ""
Write-Host "  Step 4/5 - Zoho API Credentials" -ForegroundColor White
Write-Host ""
Write-Host "  You need to create a free Zoho API client. Here's how:"
Write-Host ""
Write-Host "  +----------------------------------------------------------+"
Write-Host "  |  1. Your browser will open Zoho API Console              |"
Write-Host "  |  2. Click  [ + ADD CLIENT ]                              |"
Write-Host "  |  3. Click  [ Self Client ]  then  [ CREATE ]             |"
Write-Host "  |  4. Under 'Client Details' you will see:                 |"
Write-Host "  |       * Client ID      <- copy this                      |"
Write-Host "  |       * Client Secret  <- copy this                      |"
Write-Host "  |  5. Come back here and paste them when asked             |"
Write-Host "  +----------------------------------------------------------+"
Write-Host ""

Read-Host "  Press ENTER to open the Zoho API Console in your browser"
Start-Process "https://api-console.zoho.com"

Write-Host ""
Write-Host "  (The page opened in your browser. Follow the 5 steps above.)"
Write-Host ""

# Read Client ID
$ClientId = ""
while (-not $ClientId) {
    $ClientId = (Read-Host "  Paste your Client ID here and press ENTER").Trim()
    if (-not $ClientId) { Write-Warn "Client ID cannot be empty. Please try again." }
}

# Read Client Secret (masked)
$ClientSecret = ""
while (-not $ClientSecret) {
    $SecureInput = Read-Host "  Paste your Client Secret here and press ENTER" -AsSecureString
    $ClientSecret = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
        [Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecureInput)
    )
    $ClientSecret = $ClientSecret.Trim()
    if (-not $ClientSecret) { Write-Warn "Client Secret cannot be empty. Please try again." }
}

Write-Ok "Credentials received"

# ── Step 5: OAuth — open browser and capture token ────────────────────────────
Write-Host ""
Write-Host "  Step 5/5 - Connecting to your Zoho Account" -ForegroundColor White
Write-Host ""
Write-Info "Your browser will open for Zoho login. Log in and click 'Accept'."
Write-Info "The script will finish automatically after you approve access."
Write-Host ""

& $UvCmd run --project $ScriptDir --python 3.11 python -m zoho_campaigns_mcp.auth $ClientId $ClientSecret
if ($LASTEXITCODE -ne 0) { Write-Die "OAuth authentication failed. Please re-run this script and try again." }

Write-Ok "Connected to Zoho Campaigns!"

# ── Configure Claude Desktop ──────────────────────────────────────────────────
Write-Host ""
Write-Info "Configuring Claude Desktop..."

$UvPath = (Get-Command uv -ErrorAction SilentlyContinue).Source
if (-not $UvPath) { $UvPath = "uv" }

# JSON merge in pure PowerShell is fragile (BOM, PSCustomObject vs hashtable,
# property ordering). Delegate to a Python helper that reads tokens.json and
# writes claude_desktop_config.json deterministically.
& $UvCmd run --project $ScriptDir --python 3.11 python -m zoho_campaigns_mcp.configure_claude $UvPath $ScriptDir
if ($LASTEXITCODE -ne 0) {
    Write-Warn "Could not update Claude Desktop config automatically."
    Write-Host ""
    Write-Host "  You can finish manually by editing:"
    Write-Host "    $env:APPDATA\Claude\claude_desktop_config.json"
    Write-Host "  and adding under 'mcpServers':"
    Write-Host ""
    Write-Host "    `"zoho-campaigns`": {"
    Write-Host "      `"command`": `"$UvPath`","
    Write-Host "      `"args`": [`"run`", `"--project`", `"$ScriptDir`", `"--python`", `"3.11`", `"zoho-campaigns-mcp`"],"
    Write-Host "      `"env`": { `"ZOHO_CLIENT_ID`": `"<your id>`", `"ZOHO_CLIENT_SECRET`": `"<your secret>`" }"
    Write-Host "    }"
} else {
    Write-Ok "Claude Desktop config updated"
}

# ── Done! ─────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "  ==========================================" -ForegroundColor Green
Write-Host "    Setup complete!" -ForegroundColor Green
Write-Host "  ==========================================" -ForegroundColor Green
Write-Host ""
Write-Host "  What to do next:"
Write-Host "  1. Quit Claude Desktop completely (if it's open)"
Write-Host "  2. Reopen Claude Desktop"
Write-Host "  3. Start a new conversation and try:"
Write-Host "       'List my Zoho Campaigns mailing lists'"
Write-Host "       'Show me my recent campaigns'"
Write-Host ""
Write-Host "  If something goes wrong, re-run: powershell -ExecutionPolicy Bypass -File setup.ps1"
Write-Host ""
Read-Host "Press ENTER to close this window"
