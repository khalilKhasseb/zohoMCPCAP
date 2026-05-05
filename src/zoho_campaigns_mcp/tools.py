"""
MCP tool definitions for Zoho Campaigns.

Each function is registered as an MCP tool. Tools are grouped into:
  - Campaigns (list, get, create, send, schedule, delete, report)
  - Mailing Lists (list, create, update, delete)
  - Contacts (list subscribers, add, unsubscribe, bulk add, get fields)
"""

from typing import Any, Dict, List, Optional

from mcp.server import Server
from mcp.types import TextContent, Tool

from .api import ZohoCampaignsAPI, ZohoCampaignsError


def _ok(data: Any) -> List[TextContent]:
    import json
    return [TextContent(type="text", text=json.dumps(data, indent=2, ensure_ascii=False))]


def _err(msg: str) -> List[TextContent]:
    return [TextContent(type="text", text=f"Error: {msg}")]


def register_tools(server: Server, api: ZohoCampaignsAPI) -> None:
    """Register all Zoho Campaigns tools on the MCP server."""

    # ------------------------------------------------------------------
    # Tool schemas
    # ------------------------------------------------------------------

    @server.list_tools()
    async def list_tools() -> List[Tool]:
        return [
            Tool(
                name="list_campaigns",
                description="List your recent Zoho Campaigns email campaigns with their status and dates.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "from_index": {"type": "integer", "description": "Starting position (default 1)", "default": 1},
                        "range": {"type": "integer", "description": "Number of campaigns to return, max 100 (default 20)", "default": 20},
                    },
                },
            ),
            Tool(
                name="get_campaign_details",
                description="Get full details of a specific campaign including subject, sender, status, and mailing list.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "campaignkey": {"type": "string", "description": "The unique campaign key (visible in list_campaigns output)"},
                    },
                    "required": ["campaignkey"],
                },
            ),
            Tool(
                name="create_campaign",
                description="Create a new email campaign in Zoho Campaigns.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "campaign_name": {"type": "string", "description": "Internal name for the campaign"},
                        "subject": {"type": "string", "description": "Email subject line that recipients will see"},
                        "from_name": {"type": "string", "description": "Sender display name (e.g. 'John from Acme')"},
                        "from_email": {"type": "string", "description": "Sender email address (must be verified in Zoho)"},
                        "reply_to": {"type": "string", "description": "Reply-to email address"},
                        "listkey": {"type": "string", "description": "Mailing list key to send to (get from list_mailing_lists)"},
                        "content": {"type": "string", "description": "HTML content of the email body (optional)"},
                    },
                    "required": ["campaign_name", "subject", "from_name", "from_email", "reply_to", "listkey"],
                },
            ),
            Tool(
                name="send_campaign",
                description="Send a campaign immediately to its mailing list. Cannot be undone.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "campaignkey": {"type": "string", "description": "The campaign key to send"},
                    },
                    "required": ["campaignkey"],
                },
            ),
            Tool(
                name="schedule_campaign",
                description="Schedule a campaign to be sent at a specific date and time.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "campaignkey": {"type": "string", "description": "The campaign key to schedule"},
                        "schedule_time": {"type": "string", "description": "Date and time in format 'YYYY-MM-DD HH:MM:SS' (your Zoho account timezone)"},
                    },
                    "required": ["campaignkey", "schedule_time"],
                },
            ),
            Tool(
                name="delete_campaign",
                description="Permanently delete a campaign. This cannot be undone.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "campaignkey": {"type": "string", "description": "The campaign key to delete"},
                    },
                    "required": ["campaignkey"],
                },
            ),
            Tool(
                name="get_campaign_report",
                description="Get performance metrics for a campaign: opens, clicks, bounces, unsubscribes.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "campaignkey": {"type": "string", "description": "The campaign key"},
                    },
                    "required": ["campaignkey"],
                },
            ),
            Tool(
                name="list_mailing_lists",
                description="List all mailing lists in your Zoho Campaigns account.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "from_index": {"type": "integer", "description": "Starting position (default 1)", "default": 1},
                        "range": {"type": "integer", "description": "Number of lists to return (default 20)", "default": 20},
                    },
                },
            ),
            Tool(
                name="create_mailing_list",
                description=(
                    "Create a new mailing list with 1-10 initial email contacts. "
                    "Zoho requires at least one email and accepts at most 10 — "
                    "use add_contacts_bulk afterwards to add the rest."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "listname": {"type": "string", "description": "Name for the new mailing list"},
                        "emails": {
                            "type": "array",
                            "description": "1-10 contact email addresses to seed the list. Required.",
                            "items": {"type": "string"},
                            "minItems": 1,
                            "maxItems": 10,
                        },
                        "signupform": {
                            "type": "string",
                            "description": "'public' for an open signup form (default), 'private' for admin-only.",
                            "enum": ["public", "private"],
                            "default": "public",
                        },
                        "description": {
                            "type": "string",
                            "description": "Optional list description.",
                        },
                    },
                    "required": ["listname", "emails"],
                },
            ),
            Tool(
                name="update_mailing_list",
                description="Rename a mailing list. Zoho requires the signup-form mode on every update.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "listkey": {"type": "string", "description": "The list key to update (get from list_mailing_lists)"},
                        "new_name": {"type": "string", "description": "New name for the mailing list"},
                        "signupform": {
                            "type": "string",
                            "description": "'public' (open signup form, default) or 'private' (admin-only).",
                            "enum": ["public", "private"],
                            "default": "public",
                        },
                    },
                    "required": ["listkey", "new_name"],
                },
            ),
            Tool(
                name="delete_mailing_list",
                description="Delete a mailing list. Choose whether to keep or remove the contacts.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "listkey": {"type": "string", "description": "The list key to delete"},
                        "option": {
                            "type": "string",
                            "description": "'retain' to keep contacts in other lists (default), 'delete' to remove them entirely",
                            "enum": ["retain", "delete"],
                            "default": "retain",
                        },
                    },
                    "required": ["listkey"],
                },
            ),
            Tool(
                name="get_list_subscribers",
                description="Get the contacts subscribed to a mailing list.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "listkey": {"type": "string", "description": "The mailing list key"},
                        "from_index": {"type": "integer", "description": "Starting position (default 1)", "default": 1},
                        "range": {"type": "integer", "description": "Number of contacts to return, max 100 (default 20)", "default": 20},
                    },
                    "required": ["listkey"],
                },
            ),
            Tool(
                name="add_subscriber",
                description="Add a single contact to a mailing list.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "listkey": {"type": "string", "description": "The mailing list key"},
                        "email": {"type": "string", "description": "Contact's email address"},
                        "first_name": {"type": "string", "description": "Contact's first name (optional)"},
                        "last_name": {"type": "string", "description": "Contact's last name (optional)"},
                        "extra_fields": {
                            "type": "object",
                            "description": "Additional contact fields as key-value pairs (optional)",
                        },
                    },
                    "required": ["listkey", "email"],
                },
            ),
            Tool(
                name="unsubscribe_contact",
                description="Remove a contact from a mailing list (unsubscribe them).",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "listkey": {"type": "string", "description": "The mailing list key"},
                        "email": {"type": "string", "description": "Contact's email address to unsubscribe"},
                    },
                    "required": ["listkey", "email"],
                },
            ),
            Tool(
                name="add_contacts_bulk",
                description=(
                    "Add up to 10 email contacts to a mailing list at once. "
                    "Zoho's bulk endpoint only supports email addresses (no first/last name) "
                    "and is capped at 10 per call — for >10, call this tool repeatedly. "
                    "For richer contact data (names, custom fields), use add_subscriber per contact."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "listkey": {"type": "string", "description": "The mailing list key"},
                        "emails": {
                            "type": "array",
                            "description": "1-10 contact email addresses to add.",
                            "items": {"type": "string"},
                            "minItems": 1,
                            "maxItems": 10,
                        },
                    },
                    "required": ["listkey", "emails"],
                },
            ),
            Tool(
                name="get_contact_fields",
                description="List all available contact fields (e.g. First Name, Last Name, Phone, custom fields).",
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
            Tool(
                name="list_tags",
                description="List every tag in the account, with owner, color, description, and tagged-contact counts.",
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
            Tool(
                name="create_tag",
                description="Create a new tag. Tags are account-wide and can later be attached to contacts.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "tag_name": {"type": "string", "description": "Display name for the tag."},
                        "description": {"type": "string", "description": "Optional short description."},
                        "color": {
                            "type": "string",
                            "description": "Optional hex color code (e.g. '#ec676c'). Zoho defaults to '#ec676c' if omitted.",
                        },
                    },
                    "required": ["tag_name"],
                },
            ),
            Tool(
                name="delete_tag",
                description=(
                    "Delete a tag by name. Irreversible: the tag is removed account-wide "
                    "and dissociated from every contact it was attached to."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "tag_name": {"type": "string", "description": "The exact tag name to delete."},
                    },
                    "required": ["tag_name"],
                },
            ),
            Tool(
                name="tag_contact",
                description="Attach an existing tag to a contact, identified by email.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "tag_name": {"type": "string", "description": "The tag to attach (must already exist — use create_tag first)."},
                        "email": {"type": "string", "description": "Contact's email address."},
                    },
                    "required": ["tag_name", "email"],
                },
            ),
            Tool(
                name="untag_contact",
                description="Remove a tag from a contact (the tag itself stays — only the association is dropped).",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "tag_name": {"type": "string", "description": "The tag to remove from the contact."},
                        "email": {"type": "string", "description": "Contact's email address."},
                    },
                    "required": ["tag_name", "email"],
                },
            ),
        ]

    # ------------------------------------------------------------------
    # Tool handlers
    # ------------------------------------------------------------------

    @server.call_tool()
    async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
        try:
            if name == "list_campaigns":
                result = api.get_recent_campaigns(
                    from_index=arguments.get("from_index", 1),
                    range=arguments.get("range", 20),
                )
                return _ok(result)

            elif name == "get_campaign_details":
                result = api.get_campaign_details(arguments["campaignkey"])
                return _ok(result)

            elif name == "create_campaign":
                result = api.create_campaign(
                    campaign_name=arguments["campaign_name"],
                    subject=arguments["subject"],
                    from_name=arguments["from_name"],
                    from_email=arguments["from_email"],
                    reply_to=arguments["reply_to"],
                    listkey=arguments["listkey"],
                    content=arguments.get("content", ""),
                )
                return _ok(result)

            elif name == "send_campaign":
                result = api.send_campaign(arguments["campaignkey"])
                return _ok(result)

            elif name == "schedule_campaign":
                result = api.schedule_campaign(
                    campaignkey=arguments["campaignkey"],
                    schedule_time=arguments["schedule_time"],
                )
                return _ok(result)

            elif name == "delete_campaign":
                result = api.delete_campaign(arguments["campaignkey"])
                return _ok(result)

            elif name == "get_campaign_report":
                result = api.get_campaign_report(arguments["campaignkey"])
                return _ok(result)

            elif name == "list_mailing_lists":
                result = api.get_mailing_lists(
                    from_index=arguments.get("from_index", 1),
                    range=arguments.get("range", 20),
                )
                return _ok(result)

            elif name == "create_mailing_list":
                result = api.create_list_with_contacts(
                    listname=arguments["listname"],
                    emails=arguments["emails"],
                    signupform=arguments.get("signupform", "public"),
                    description=arguments.get("description"),
                )
                return _ok(result)

            elif name == "update_mailing_list":
                result = api.update_list_details(
                    listkey=arguments["listkey"],
                    new_name=arguments["new_name"],
                    signupform=arguments.get("signupform", "public"),
                )
                return _ok(result)

            elif name == "delete_mailing_list":
                result = api.delete_mailing_list(
                    listkey=arguments["listkey"],
                    option=arguments.get("option", "retain"),
                )
                return _ok(result)

            elif name == "get_list_subscribers":
                result = api.get_list_subscribers(
                    listkey=arguments["listkey"],
                    from_index=arguments.get("from_index", 1),
                    range=arguments.get("range", 20),
                )
                return _ok(result)

            elif name == "add_subscriber":
                result = api.subscribe_contact(
                    listkey=arguments["listkey"],
                    email=arguments["email"],
                    first_name=arguments.get("first_name", ""),
                    last_name=arguments.get("last_name", ""),
                    extra_fields=arguments.get("extra_fields"),
                )
                return _ok(result)

            elif name == "unsubscribe_contact":
                result = api.unsubscribe_contact(
                    listkey=arguments["listkey"],
                    email=arguments["email"],
                )
                return _ok(result)

            elif name == "add_contacts_bulk":
                result = api.add_contacts_to_list(
                    listkey=arguments["listkey"],
                    emails=arguments["emails"],
                )
                return _ok(result)

            elif name == "get_contact_fields":
                result = api.get_contact_fields()
                return _ok(result)

            elif name == "list_tags":
                result = api.get_all_tags()
                return _ok(result)

            elif name == "create_tag":
                result = api.create_tag(
                    tag_name=arguments["tag_name"],
                    description=arguments.get("description"),
                    color=arguments.get("color"),
                )
                return _ok(result)

            elif name == "delete_tag":
                result = api.delete_tag(tag_name=arguments["tag_name"])
                return _ok(result)

            elif name == "tag_contact":
                result = api.associate_tag(
                    tag_name=arguments["tag_name"],
                    email=arguments["email"],
                )
                return _ok(result)

            elif name == "untag_contact":
                result = api.deassociate_tag(
                    tag_name=arguments["tag_name"],
                    email=arguments["email"],
                )
                return _ok(result)

            else:
                return _err(f"Unknown tool: {name}")

        except ZohoCampaignsError as e:
            return _err(str(e))
        except ValueError as e:
            return _err(str(e))
        except KeyError as e:
            return _err(f"Missing required argument: {e}")
        except Exception as e:
            return _err(f"Unexpected error: {e}")
