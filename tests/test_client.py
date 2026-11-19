"""Tests for the USPS client. No call leaves the machine; numbers and names are invented."""

from http import HTTPStatus
from typing import Any

import pytest
import xmltodict
from niquests import HTTPError, Response

from usps_sdk import USPSClient

TRACKING_NUMBER = "9400100000000000000000"

TRACKED = (
    f'<TrackResponse><TrackInfo ID="{TRACKING_NUMBER}">'
    "<TrackSummary>Your item was delivered.</TrackSummary>"
    "</TrackInfo></TrackResponse>"
)


def _response(status_code: int, body: str = "") -> Response:
    """Build a niquests Response without touching the network."""
    response = Response()
    response.status_code = status_code
    response._content = body.encode()  # noqa: SLF001 -- no public way to seed a canned body
    return response


class _SessionRecorder:
    """Stand-in for ``Session.request`` serving one canned response and recording calls."""

    def __init__(self, response: Response) -> None:
        self.response = response
        self.calls: list[dict[str, Any]] = []

    def request(self, method: str, url: str, **kwargs: Any) -> Response:  # noqa: ANN401 -- mirrors Session.request
        self.calls.append({"method": method, "url": url, **kwargs})
        return self.response


def _client(response: Response) -> tuple[USPSClient, _SessionRecorder]:
    """Build a client whose session answers with ``response``."""
    client = USPSClient("user-one", base_url="https://usps.invalid/api")
    recorder = _SessionRecorder(response)
    client._session = recorder  # type: ignore[assignment]  # noqa: SLF001 -- the session is the seam
    return client, recorder


def test_tracking_answer_is_parsed() -> None:
    """The XML answer comes back as nested dictionaries."""
    client, _ = _client(_response(HTTPStatus.OK, TRACKED))

    tracking = client.get_tracking(TRACKING_NUMBER)

    assert tracking["TrackResponse"]["TrackInfo"]["@ID"] == TRACKING_NUMBER
    assert tracking["TrackResponse"]["TrackInfo"]["TrackSummary"] == "Your item was delivered."


def test_tracking_request_names_the_user_and_the_package() -> None:
    """The request asks the tracking API about this package as this user."""
    client, recorder = _client(_response(HTTPStatus.OK, TRACKED))

    client.get_tracking(TRACKING_NUMBER)

    (call,) = recorder.calls
    request = xmltodict.parse(call["params"]["XML"])["TrackRequest"]
    assert call["url"] == "https://usps.invalid/api"
    assert call["params"]["API"] == "TrackV2"
    assert request["@USERID"] == "user-one"
    assert request["TrackID"]["@ID"] == TRACKING_NUMBER


def test_tracking_number_cannot_break_out_of_the_request() -> None:
    """A tracking number with markup in it stays a value."""
    client, recorder = _client(_response(HTTPStatus.OK, TRACKED))
    hostile = '1"/><Other ID="2'

    client.get_tracking(hostile)

    (call,) = recorder.calls
    request = xmltodict.parse(call["params"]["XML"])["TrackRequest"]
    assert request["TrackID"]["@ID"] == hostile
    assert "Other" not in request


def test_failed_request_raises() -> None:
    """An HTTP error from USPS is raised, not parsed."""
    client, _ = _client(_response(HTTPStatus.INTERNAL_SERVER_ERROR))

    with pytest.raises(HTTPError):
        client.get_tracking(TRACKING_NUMBER)
