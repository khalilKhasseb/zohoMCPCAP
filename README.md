# Zoho Campaigns MCP Server

Control your Zoho Campaigns account directly from Claude — no technical knowledge required.

---

## What you can do

Once set up, just talk to Claude naturally:

- "List my mailing lists"
- "Show me my recent campaigns"
- "Create a mailing list called Newsletter with these contacts: alice@example.com, bob@example.com"
- "Add john@example.com to my Newsletter list"
- "Show me the open rate for my last campaign"
- "Schedule my Summer Sale campaign for June 15 at 10am"

---

## Requirements

- A Mac (macOS 10.15 or newer) **or** Windows 10/11
- An internet connection
- A Zoho Campaigns account (free or paid)
- Claude Desktop app installed

That's it. No coding experience needed.

---

## Setup — takes about 3 minutes

### Mac users

**Step 1 — Open Terminal**
Press **Command (⌘) + Space**, type **Terminal**, then press **Enter**.

**Step 2 — Go to this folder**
Type `cd ` (with a space after), then drag the **zohoMCPCAP** folder from Finder into the Terminal window. Press **Enter**.

**Step 3 — Run the setup script**
```
bash setup.sh
```

---

### Windows users

**Step 1 — Right-click `setup.ps1`** in the zohoMCPCAP folder

**Step 2 — Click "Run with PowerShell"**

If you see a blue security warning, click **"Run anyway"** — this is normal for scripts downloaded from the internet.

---

The script (on either platform) will:
- Install the required software automatically
- Open your browser to connect your Zoho account
- Configure Claude Desktop for you

### Final step (both platforms) — Restart Claude Desktop

Quit Claude Desktop and reopen it, then open a new conversation and type:

> List my Zoho Campaigns mailing lists

---

## Troubleshooting

**"Python not found"**
Install Python from [python.org/downloads](https://www.python.org/downloads/), then run `bash setup.sh` again.

**"No credentials found" error in Claude**
Run `bash setup.sh` again to re-authenticate.

**The browser didn't open automatically**
The script will print a URL. Copy and paste it into your browser manually.

**"Claude Desktop does not appear to be installed yet" (Mac)**
The setup script will warn you if it can't find Claude Desktop in `/Applications` or `~/Applications`. Download it from <https://claude.ai/download>, install it, then re-run `bash setup.sh` — or just continue setup and install Claude before the final restart step.

**"Cannot reach the internet" (Mac)**
Setup checks `astral.sh` reachability before installing uv. Connect to Wi-Fi or Ethernet and re-run `bash setup.sh`. Corporate Wi-Fi networks sometimes block `astral.sh` — try a personal hotspot if you hit this on a work network.

**The Client Secret prompt looks frozen (Mac)**
It isn't — the prompt hides what you type/paste for security. Just paste the secret and press ENTER. You won't see any characters appear, which is normal.

**Port 8080 is already in use** (or `WinError 10013` on Windows)
Setup will automatically fall back to another port (8090, 8765, 53682, …) if 8080 is taken — common on Windows when WSL or Docker is running. When that happens, the script prints the redirect URI it picked (e.g. `http://localhost:8090/callback`) and waits for you to add it as an **Authorized Redirect URI** in your Zoho client at <https://api-console.zoho.com>. Add it, save, then press ENTER to continue.

If you'd rather free port 8080 instead, on Windows run `wsl --shutdown` in PowerShell (kills WSL relays), or stop whatever Windows service is bound to it, then re-run setup.

**Claude doesn't show Zoho tools after restart**
Make sure you fully quit Claude Desktop (right-click the Dock icon → Quit) and reopen it — not just close the window.

---

## Available tools

| Tool | What it does |
|------|-------------|
| `list_campaigns` | Show all your recent campaigns |
| `get_campaign_details` | Get full info about one campaign |
| `create_campaign` | Create a new email campaign |
| `send_campaign` | Send a campaign right now |
| `schedule_campaign` | Schedule a campaign for later |
| `delete_campaign` | Delete a campaign permanently |
| `get_campaign_report` | See opens, clicks, bounces |
| `list_mailing_lists` | Show all your mailing lists |
| `create_mailing_list` | Create a new list |
| `update_mailing_list` | Rename a list |
| `delete_mailing_list` | Delete a list |
| `get_list_subscribers` | See who's on a list |
| `add_subscriber` | Add one contact to a list |
| `unsubscribe_contact` | Remove a contact from a list |
| `add_contacts_bulk` | Add up to 10 contacts at once (email-only) |
| `get_contact_fields` | See all available contact fields |
| `list_tags` | List every tag in the account |
| `create_tag` | Create a new tag (with optional color and description) |
| `delete_tag` | Delete a tag account-wide |
| `tag_contact` | Attach a tag to a contact by email |
| `untag_contact` | Remove a tag from a contact |

---

## Security

- Your Zoho credentials are stored only on your Mac, never uploaded anywhere.
- The OAuth tokens are saved at `~/.zoho_campaigns_mcp/tokens.json` with restricted file permissions.
- The token refreshes automatically — you won't need to log in again.
- To revoke access, go to [Zoho Connected Apps](https://accounts.zoho.com/u/h#sessions/connectedapps) and remove the entry.

---

## Re-running setup

If you ever need to re-authenticate (e.g. after revoking access), just run `bash setup.sh` again.
