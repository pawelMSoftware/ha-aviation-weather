"""Tests for the SIGMET API client."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from aiohttp import ClientResponseError, ContentTypeError

from custom_components.aviation_weather.sigmet.api import SigmetApiClient


def _make_session(
    *,
    json_payload=None,
    raise_for_status_error: Exception | None = None,
    status: int = 200,
    json_error: Exception | None = None,
):
    """Build a mock aiohttp ClientSession returning the given JSON payload."""
    response = MagicMock()
    response.status = status

    if json_error is not None:
        response.json = AsyncMock(side_effect=json_error)
    else:
        response.json = AsyncMock(return_value=json_payload)

    if raise_for_status_error is not None:
        response.raise_for_status = MagicMock(side_effect=raise_for_status_error)
    else:
        response.raise_for_status = MagicMock()

    context_manager = MagicMock()
    context_manager.__aenter__ = AsyncMock(return_value=response)
    context_manager.__aexit__ = AsyncMock(return_value=False)

    session = MagicMock()
    session.get = MagicMock(return_value=context_manager)

    return session


def _raw_sigmet(fir_id: str = "EPWW") -> dict:
    return {
        "firId": fir_id,
        "firName": "WARSZAWA FIR",
        "hazard": "TURB",
        "qualifier": "SEV",
        "base": "FL180",
        "top": "FL360",
        "validTimeFrom": "2026-07-03T10:00:00Z",
        "validTimeTo": "2026-07-03T14:00:00Z",
        "coords": [],
        "rawSigmet": "WSPL31 EPWW 031000",
    }


class TestGetSigmets:
    """Tests for SigmetApiClient.get_sigmets."""

    async def test_returns_mapped_data_on_success(self) -> None:
        """A successful response is mapped into Sigmet objects for the FIR."""
        session = _make_session(json_payload=[_raw_sigmet()])
        client = SigmetApiClient(session)

        result = await client.get_sigmets("EPWW")

        assert len(result) == 1
        assert result[0].fir_id == "EPWW"

    async def test_filters_out_other_firs(self) -> None:
        """SIGMETs for other FIRs are excluded from the result."""
        session = _make_session(
            json_payload=[_raw_sigmet("EPWW"), _raw_sigmet("LFFF")],
        )
        client = SigmetApiClient(session)

        result = await client.get_sigmets("EPWW")

        assert len(result) == 1
        assert result[0].fir_id == "EPWW"

    async def test_calls_correct_endpoint_with_params(self) -> None:
        """The request is made against the expected URL with correct params."""
        session = _make_session(json_payload=[])
        client = SigmetApiClient(session)

        await client.get_sigmets("EPWW")

        session.get.assert_called_once_with(
            SigmetApiClient.BASE_URL,
            params={"format": "json"},
        )

    async def test_empty_response_returns_empty_list_not_error(self) -> None:
        """An empty list response is a normal state, not an error.

        Unlike METAR/TAF, a FIR having no active SIGMET is the common
        case, so this must not raise.
        """
        session = _make_session(json_payload=[])
        client = SigmetApiClient(session)

        result = await client.get_sigmets("EPWW")

        assert result == []

    async def test_http_error_propagates(self) -> None:
        """An HTTP error from raise_for_status propagates to the caller."""
        session = _make_session(
            json_payload=[],
            raise_for_status_error=ClientResponseError(
                request_info=MagicMock(), history=(), status=500
            ),
        )
        client = SigmetApiClient(session)

        with pytest.raises(ClientResponseError):
            await client.get_sigmets("EPWW")

    async def test_204_no_content_returns_empty_list(self) -> None:
        """A 204 response is treated as "no active SIGMETs", not a crash."""
        session = _make_session(status=204, json_payload=None)
        client = SigmetApiClient(session)

        result = await client.get_sigmets("EPWW")

        assert result == []

    async def test_unexpected_content_type_returns_empty_list_not_crash(self) -> None:
        """A non-204 response with an unexpected (non-JSON) content type
        is also treated as "no data", not as an unhandled crash."""
        session = _make_session(
            status=200,
            json_error=ContentTypeError(
                request_info=MagicMock(),
                history=(),
            ),
        )
        client = SigmetApiClient(session)

        result = await client.get_sigmets("EPWW")

        assert result == []
