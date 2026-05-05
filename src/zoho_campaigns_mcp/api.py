"""
Zoho Campaigns REST API client.

Base URL: https://campaigns.zoho.com/api/v1.1/
Auth:     Authorization: Zoho-oauthtoken <token>
Format:   resfmt=JSON on every request (case-sensitive — lowercase is silently
          ignored by some endpoints, e.g. getmailinglists, which then defaults to XML)
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
        p = {"resfmt": "JSON"}
        if params:
            p.update(params)
        resp = self._session.get(f"{BASE_URL}/{path}", headers=self._headers(), params=p, timeout=30)
        return self._parse(resp)

    def _post(self, path: str, data: Optional[Dict] = None, params: Optional[Dict] = None) -> Dict[str, Any]:
        p = {"resfmt": "JSON"}
        if params:
            p.update(params)
        resp = self._session.post(f"{BASE_URL}/{path}", headers=self._headers(), data=data, params=p, timeout=30)
        return self._parse(resp)

    def _delete(self, path: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        p = {"resfmt": "JSON"}
        if params:
            p.update(params)
        resp = self._session.delete(f"{BASE_URL}/{path}", headers=self._headers(), params=p, timeout=30)
        return self._parse(resp)

    def _parse(self, resp: requests.Response) -> Dict[str, Any]:
        body_snippet = (resp.text[:300] or "<empty body>").replace("\n", " ")

        try:
            data = resp.json()
        except ValueError:
            raise ZohoCampaignsError(
                f"Non-JSON response (HTTP {resp.status_code}) from "
                f"{resp.request.method} {resp.url} :: {body_snippet}"
            )

        # Zoho's failure envelopes are inconsistent across endpoints:
        #   - status="error" or status="failure"
        #   - sometimes only `code` is set (non-"0" means failure)
        #   - sometimes the message is empty even on failure
        # Surface ALL of these as clean ZohoCampaignsError so callers never
        # see a silently-passed-through failure dict (which previously
        # rendered as "empty error" on update_mailing_list).
        if isinstance(data, dict):
            status_raw = data.get("status")
            status = status_raw.lower() if isinstance(status_raw, str) else ""
            code = str(data.get("code", ""))
            is_failure = (
                status in ("error", "failure")
                or (code and code != "0")
            )
            if is_failure:
                msg = (
                    data.get("message")
                    or data.get("error_description")
                    or f"Zoho returned code={code or '?'} status={status_raw or '?'} from "
                       f"{resp.request.method} {resp.url} :: {body_snippet}"
                )
                raise ZohoCampaignsError(msg, code=code)

        if resp.status_code >= 400:
            raise ZohoCampaignsError(
                f"HTTP {resp.status_code} from {resp.request.method} "
                f"{resp.url} :: {body_snippet}"
            )

        return data

    # ------------------------------------------------------------------
    # Campaigns
    # ------------------------------------------------------------------

    def get_recent_campaigns(self, from_index: int = 1, range: int = 20) -> Dict:
        """List recent campaigns."""
        return self._get("recentcampaigns", {
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
        emails: List[str],
        signupform: str = "public",
        description: Optional[str] = None,
    ) -> Dict:
        """
        Create a new mailing list with 1-10 initial contacts.

        Zoho's addlistandcontacts endpoint requires every parameter in the URL
        query string and rejects calls with no email — there is no way to
        create an empty list via this endpoint. After creation, use
        add_contacts_to_list (also capped at 10 per call) to seed more contacts.

        Args:
            listname: Display name for the new list.
            emails: 1-10 contact emails. Required by Zoho.
            signupform: 'public' (open signup form, default) or 'private'
                        (admin-only).
            description: Optional list description.
        """
        if not emails:
            raise ValueError(
                "Zoho requires at least one email when creating a list. "
                "After creation, use add_contacts_to_list for more."
            )
        if len(emails) > 10:
            raise ValueError(
                "addlistandcontacts accepts a maximum of 10 emails per call. "
                "Create the list with up to 10, then add the rest in batches."
            )
        if signupform not in ("public", "private"):
            raise ValueError("signupform must be 'public' or 'private'.")

        params: Dict[str, Any] = {
            "listname": listname,
            "signupform": signupform,
            "mode": "newlist",
            "emailids": ",".join(emails),
        }
        if description:
            params["listdescription"] = description
        return self._post("addlistandcontacts", params=params)

    def update_list_details(
        self,
        listkey: str,
        new_name: str,
        signupform: str = "public",
    ) -> Dict:
        """
        Rename a mailing list. Zoho requires `newlistname` (not `listname`)
        and `signupform` ('public' or 'private') — every parameter goes in
        the URL query string.

        HTTP method note: Zoho's docs page header for updatelistdetails reads
        "Request Type: POST", but the side nav on the same page lists it as
        GET, and the live server returns INVALID_METHOD on POST. Same quirk
        as deletemailinglist (docs say POST, server only accepts GET). Use
        GET — confirmed empirically.
        """
        if signupform not in ("public", "private"):
            raise ValueError("signupform must be 'public' or 'private'.")
        return self._get("updatelistdetails", {
            "listkey": listkey,
            "newlistname": new_name,
            "signupform": signupform,
        })

    def delete_mailing_list(self, listkey: str, option: str = "retain") -> Dict:
        """
        Delete a mailing list.

        option: 'retain' keeps contacts in your account; 'delete' removes
                contacts that don't belong to any other list. Mapped onto
                Zoho's deletecontacts=off/on flag. The endpoint is GET, not POST.
        """
        if option not in ("retain", "delete"):
            raise ValueError("option must be 'retain' or 'delete'.")
        return self._get("deletemailinglist", {
            "listkey": listkey,
            "deletecontacts": "on" if option == "delete" else "off",
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
        """Subscribe a contact to a mailing list (POST, all params in query string)."""
        contact: Dict[str, str] = {"Contact Email": email}
        if first_name:
            contact["First Name"] = first_name
        if last_name:
            contact["Last Name"] = last_name
        if extra_fields:
            contact.update(extra_fields)

        # Note: listsubscribe and listunsubscribe REQUIRE "/json/" as a literal
        # URL path segment (per the Zoho docs sample requests). Sibling write
        # endpoints like addlistandcontacts and addlistsubscribersinbulk do
        # NOT — Zoho is inconsistent about this. Without /json/ the endpoint
        # 404s with "Unable to find the resource".
        return self._post("json/listsubscribe", params={
            "listkey": listkey,
            "contactinfo": json.dumps(contact),
        })

    def unsubscribe_contact(self, listkey: str, email: str) -> Dict:
        """Unsubscribe a contact from a mailing list (POST, all params in query string)."""
        # See note on listsubscribe — same /json/ path-segment requirement.
        return self._post("json/listunsubscribe", params={
            "listkey": listkey,
            "contactinfo": json.dumps({"Contact Email": email}),
        })

    def add_contacts_to_list(self, listkey: str, emails: List[str]) -> Dict:
        """
        Add up to 10 contacts (by email) to an existing list.

        Zoho's addlistsubscribersinbulk only accepts a comma-separated email
        list — it does NOT accept first/last name or other fields. For richer
        contact data, call subscribe_contact per-email instead. Callers with
        more than 10 emails should batch their input into chunks of 10.
        """
        if not emails:
            raise ValueError("emails list cannot be empty.")
        if len(emails) > 10:
            raise ValueError(
                "addlistsubscribersinbulk accepts a maximum of 10 emails per call. "
                "Batch your input into chunks of 10."
            )
        return self._post("addlistsubscribersinbulk", params={
            "listkey": listkey,
            "emailids": ",".join(emails),
        })

    def get_contact_fields(self) -> Dict:
        """Get all available contact field definitions."""
        return self._get("contact/allfields", {"type": "json"})

    # ------------------------------------------------------------------
    # Tags
    #
    # Note on endpoint paths: the Zoho tag-management docs index page calls
    # them createtag/deletetag/etc., but the actual URL paths are
    # /tag/add, /tag/delete, /tag/getalltags, /tag/associate, /tag/deassociate.
    # All five are GET, with every parameter in the query string.
    # ------------------------------------------------------------------

    def get_all_tags(self) -> Dict:
        """List every tag in the account, with owner, color, and tagged-contact count."""
        return self._get("tag/getalltags")

    def create_tag(
        self,
        tag_name: str,
        description: Optional[str] = None,
        color: Optional[str] = None,
    ) -> Dict:
        """
        Create a new tag.

        Args:
            tag_name: Display name for the tag.
            description: Optional short description.
            color: Optional hex color (e.g. '#ec676c'). Zoho defaults to '#ec676c'.
        """
        params: Dict[str, Any] = {"tagName": tag_name}
        if description:
            params["tagDesc"] = description
        if color:
            params["color"] = color
        return self._get("tag/add", params)

    def delete_tag(self, tag_name: str) -> Dict:
        """Delete a tag by name. Irreversible — also dissociates it from every contact."""
        return self._get("tag/delete", {"tagName": tag_name})

    def associate_tag(self, tag_name: str, email: str) -> Dict:
        """Attach a tag to a contact identified by email."""
        return self._get("tag/associate", {
            "tagName": tag_name,
            "lead_email": email,
        })

    def deassociate_tag(self, tag_name: str, email: str) -> Dict:
        """Remove a tag from a contact identified by email."""
        return self._get("tag/deassociate", {
            "tagName": tag_name,
            "lead_email": email,
        })
