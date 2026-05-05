"""
Zoho Campaigns REST API client.

Base URL: https://campaigns.zoho.com/api/v1.1/
Auth:     Authorization: Zoho-oauthtoken <token>
Format:   resfmt=json on every request
"""

import json
from typing import Any, Dict, List, Optional

import requests

from .auth import TokenStore, get_valid_token

BASE_URL = "https://campaigns.zoho.com/api/v1.1"


class ZohoCampaignsError(Exception):
    """Raised when the Zoho API returns an error response."""
    def __init__(self, message: str, code: Optional[str] = None):
        self.code = code
        super().__init__(message)


class ZohoCampaignsAPI:
    """
    Thin wrapper around the Zoho Campaigns REST API.
    Handles auth headers and token refresh transparently.
    """

    def __init__(self):
        self._store = TokenStore()
        self._session = requests.Session()

    def _headers(self) -> Dict[str, str]:
        token = get_valid_token(self._store)
        return {"Authorization": f"Zoho-oauthtoken {token}"}

    def _get(self, path: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        p = {"resfmt": "json"}
        if params:
            p.update(params)
        resp = self._session.get(f"{BASE_URL}/{path}", headers=self._headers(), params=p, timeout=30)
        return self._parse(resp)

    def _post(self, path: str, data: Optional[Dict] = None, params: Optional[Dict] = None) -> Dict[str, Any]:
        p = {"resfmt": "json"}
        if params:
            p.update(params)
        resp = self._session.post(f"{BASE_URL}/{path}", headers=self._headers(), data=data, params=p, timeout=30)
        return self._parse(resp)

    def _delete(self, path: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        p = {"resfmt": "json"}
        if params:
            p.update(params)
        resp = self._session.delete(f"{BASE_URL}/{path}", headers=self._headers(), params=p, timeout=30)
        return self._parse(resp)

    def _parse(self, resp: requests.Response) -> Dict[str, Any]:
        try:
            data = resp.json()
        except ValueError:
            raise ZohoCampaignsError(f"Non-JSON response ({resp.status_code}): {resp.text[:200]}")

        # Zoho wraps responses — unwrap if needed
        if isinstance(data, dict):
            status = data.get("status", "")
            if status == "error" or (isinstance(status, str) and status.lower() == "error"):
                msg = data.get("message", data.get("error_description", str(data)))
                raise ZohoCampaignsError(msg, code=str(data.get("code", "")))
            # Some endpoints nest under a key — return the full dict for callers to handle
        return data

    # ------------------------------------------------------------------
    # Campaigns
    # ------------------------------------------------------------------

    def get_recent_campaigns(self, from_index: int = 1, range: int = 20) -> Dict:
        """List recent campaigns."""
        return self._get("getrecentcampaigns", {
            "fromindex": from_index,
            "range": range,
        })

    def get_campaign_details(self, campaignkey: str) -> Dict:
        """Get details for a specific campaign."""
        return self._get("getcampaigndetails", {"campaignkey": campaignkey})

    def create_campaign(
        self,
        campaign_name: str,
        subject: str,
        from_name: str,
        from_email: str,
        reply_to: str,
        listkey: str,
        content: str = "",
    ) -> Dict:
        """Create a new email campaign."""
        return self._post("createcampaign", data={
            "campaignname": campaign_name,
            "subject": subject,
            "from_name": from_name,
            "from_email": from_email,
            "reply_to": reply_to,
            "listkey": listkey,
            "content": content,
        })

    def send_campaign(self, campaignkey: str) -> Dict:
        """Send a campaign immediately."""
        return self._post("sendcampaign", data={"campaignkey": campaignkey})

    def schedule_campaign(self, campaignkey: str, schedule_time: str) -> Dict:
        """
        Schedule a campaign.
        schedule_time format: 'yyyy-MM-dd HH:mm:ss' in the account's timezone.
        """
        return self._post("schedulecampaign", data={
            "campaignkey": campaignkey,
            "schedule_time": schedule_time,
        })

    def delete_campaign(self, campaignkey: str) -> Dict:
        """Delete a campaign."""
        return self._post("deletecampaign", data={"campaignkey": campaignkey})

    def get_campaign_report(self, campaignkey: str) -> Dict:
        """Get performance report for a campaign."""
        return self._get("campaignreport", {"campaignkey": campaignkey})

    def get_campaign_recipients_data(self, campaignkey: str, from_index: int = 1, range: int = 20) -> Dict:
        """Get recipient-level data for a campaign."""
        return self._post("getcampaignrecipientsdata", data={
            "campaignkey": campaignkey,
            "fromindex": from_index,
            "range": range,
        })

    # ------------------------------------------------------------------
    # Mailing Lists
    # ------------------------------------------------------------------

    def get_mailing_lists(self, from_index: int = 1, range: int = 20) -> Dict:
        """List all mailing lists."""
        return self._get("getmailinglists", {
            "fromindex": from_index,
            "range": range,
        })

    def create_list_with_contacts(
        self,
        listname: str,
        contacts: Optional[List[Dict]] = None,
    ) -> Dict:
        """
        Create a new mailing list, optionally with initial contacts.
        contacts: list of dicts with keys like 'Contact Email', 'First Name', 'Last Name'.
        """
        data: Dict[str, Any] = {"listname": listname}
        if contacts:
            data["contactinfo"] = json.dumps(contacts)
        return self._post("addlistandcontacts", data=data)

    def update_list_details(self, listkey: str, new_name: str) -> Dict:
        """Rename a mailing list."""
        return self._post("updatelistdetails", data={
            "listkey": listkey,
            "listname": new_name,
        })

    def delete_mailing_list(self, listkey: str, option: str = "retain") -> Dict:
        """
        Delete a mailing list.
        option: 'retain' keeps contacts in other lists, 'delete' removes them everywhere.
        """
        return self._post("deletemailinglist", data={
            "listkey": listkey,
            "option": option,
        })

    # ------------------------------------------------------------------
    # Contacts & Subscriptions
    # ------------------------------------------------------------------

    def get_list_subscribers(
        self,
        listkey: str,
        from_index: int = 1,
        range: int = 20,
        sort: str = "asc",
    ) -> Dict:
        """Get contacts subscribed to a mailing list."""
        return self._get("getlistsubscribers", {
            "listkey": listkey,
            "fromindex": from_index,
            "range": range,
            "sort": sort,
        })

    def subscribe_contact(
        self,
        listkey: str,
        email: str,
        first_name: str = "",
        last_name: str = "",
        extra_fields: Optional[Dict[str, str]] = None,
    ) -> Dict:
        """Subscribe a contact to a mailing list."""
        contact: Dict[str, str] = {"Contact Email": email}
        if first_name:
            contact["First Name"] = first_name
        if last_name:
            contact["Last Name"] = last_name
        if extra_fields:
            contact.update(extra_fields)

        return self._post("listsubscribe", data={
            "listkey": listkey,
            "contactinfo": json.dumps(contact),
        })

    def unsubscribe_contact(self, listkey: str, email: str) -> Dict:
        """Unsubscribe a contact from a mailing list."""
        return self._post("listunsubscribe", data={
            "listkey": listkey,
            "contactinfo": json.dumps({"Contact Email": email}),
        })

    def add_contacts_to_list(self, listkey: str, contacts: List[Dict]) -> Dict:
        """
        Add multiple contacts to an existing list.
        contacts: list of dicts with at minimum 'Contact Email'.
        """
        return self._post("addlistsubscribersinbulk", data={
            "listkey": listkey,
            "contactinfo": json.dumps(contacts),
        })

    def get_contact_fields(self) -> Dict:
        """Get all available contact field definitions."""
        return self._get("contact/allfields", {"type": "json"})
