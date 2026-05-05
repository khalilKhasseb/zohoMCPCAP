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

- A Mac (macOS 10.15 or newer)
- An internet connection
- A Zoho Campaigns account (free or paid)
- Claude Desktop app installed

That's it. No coding experience needed.

---

## Setup — takes about 3 minutes

### Step 1 — Open Terminal

Press **Command (⌘) + Space**, type **Terminal**, then press **Enter**.

### Step 2 — Go to this folder

In the Terminal window, type `cd ` (with a space after), then drag the **zohoMCPCAP** folder from Finder into the Terminal window. Press **Enter**.

### Step 3 — Run the setup script

Type this and press **Enter**:

```
bash setup.sh
```

The script will guide you through everything step by step. It will:
- Install the required software automatically
- Open your browser to connect your Zoho account
- Configure Claude Desktop for you

### Step 4 — Restart Claude Desktop

Quit Claude Desktop and reopen it.

### Step 5 — Try it

Open a new Claude conversation and type:

> List my Zoho Campaigns mailing lists

---

## Troubleshooting

**"Python not found"**
Install Python from [python.org/downloads](https://www.python.org/downloads/), then run `bash setup.sh` again.

**"No credentials found" error in Claude**
Run `bash setup.sh` again to re-authenticate.

**The browser didn't open automatically**
The script will print a URL. Copy and paste it into your browser manually.

**Port 8080 is already in use**
Another app is using that port. Quit any local web servers you have running, then re-run `bash setup.sh`.

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
| `add_contacts_bulk` | Add many contacts at once |
| `get_contact_fields` | See all available contact fields |

---

## Security

- Your Zoho credentials are stored only on your Mac, never uploaded anywhere.
- The OAuth tokens are saved at `~/.zoho_campaigns_mcp/tokens.json` with restricted file permissions.
- The token refreshes automatically — you won't need to log in again.
- To revoke access, go to [Zoho Connected Apps](https://accounts.zoho.com/u/h#sessions/connectedapps) and remove the entry.

---

## Re-running setup

If you ever need to re-authenticate (e.g. after revoking access), just run `bash setup.sh` again.
