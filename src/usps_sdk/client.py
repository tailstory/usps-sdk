"""Interacting with USPS."""

from typing import Any
from xml.sax.saxutils import quoteattr

import niquests
import xmltodict

PRODUCTION_URL = "https://secure.shippingapis.com/ShippingAPI.dll"


class USPSClient:
    """A class wrapping USPS's Web Tools API."""

    def __init__(self, user_id: str, *, base_url: str = PRODUCTION_URL, timeout: float = 60.0) -> None:
        """Initialize the USPSClient class.

        Parameters
        ----------
        user_id
            The Web Tools user ID.
        base_url
            The API endpoint.
        timeout
            Seconds to wait for USPS to answer.
        """
        self.base_url = base_url
        self.timeout = timeout
        self._user_id = user_id
        self._session = niquests.Session()

    def _request(self, api: str, xml: str) -> dict[str, Any]:
        """Call one Web Tools API and parse its XML answer.

        Parameters
        ----------
        api
            The API's name, such as ``TrackV2``.
        xml
            The request document.
        """
        response = self._session.request(
            "POST",
            self.base_url,
            params={"API": api, "XML": xml},
            timeout=self.timeout,
        )
        response.raise_for_status()
        return xmltodict.parse(response.text or "")

    def get_tracking(self, tracking_number: str) -> dict[str, Any]:
        """Read a package's tracking details.

        Parameters
        ----------
        tracking_number
            The package's tracking number.
        """
        xml = (
            f"<TrackRequest USERID={quoteattr(self._user_id)}><TrackID ID={quoteattr(tracking_number)}/></TrackRequest>"
        )
        return self._request("TrackV2", xml)
