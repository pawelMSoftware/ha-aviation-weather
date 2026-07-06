"""Tests for the TAF API client."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from aiohttp import ClientResponseError, ContentTypeError

from custom_components.aviation_weather.taf.api import TafApiClient


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


class TestGetTaf:
    """Tests for TafApiClient.get_taf."""

    async def test_returns_mapped_data_on_success(self) -> None:
        """A successful response is mapped into TafData."""
        session = _make_session(
            json_payload=[{"icaoId": "EPWA", "rawTAF": "TAF EPWA ..."}],
        )
        client = TafApiClient(session)

        result = await client.get_taf("EPWA")

        assert result.airport == "EPWA"
        assert result.raw_taf == "TAF EPWA ..."

    async def test_calls_correct_endpoint_with_params(self) -> None:
        """The request is made against the expected URL with correct params."""
        session = _make_session(json_payload=[{"icaoId": "EPWA"}])
        client = TafApiClient(session)

        await client.get_taf("EPWA")

        session.get.assert_called_once_with(
            TafApiClient.BASE_URL,
            params={"ids": "EPWA", "format": "json"},
        )

    async def test_empty_response_raises_value_error(self) -> None:
        """An empty list response raises a ValueError, not an IndexError."""
        session = _make_session(json_payload=[])
        client = TafApiClient(session)

        with pytest.raises(ValueError, match="No TAF data"):
            await client.get_taf("EPKK")

    async def test_http_error_propagates(self) -> None:
        """An HTTP error from raise_for_status propagates to the caller."""
        session = _make_session(
            json_payload=[],
            raise_for_status_error=ClientResponseError(
                request_info=MagicMock(), history=(), status=500
            ),
        )
        client = TafApiClient(session)

        with pytest.raises(ClientResponseError):
            await client.get_taf("EPWA")

    async def test_204_no_content_raises_value_error_not_crash(self) -> None:
        """A 204 response (airport has no current TAF report) is treated
        as a normal "no data" condition, not a crash."""
        session = _make_session(status=204, json_payload=None)
        client = TafApiClient(session)

        with pytest.raises(ValueError, match="No TAF data"):
            await client.get_taf("EDFE")

    async def test_unexpected_content_type_raises_value_error_not_crash(
        self,
    ) -> None:
        """A non-204 response with an unexpected (non-JSON) content type
        is also treated as "no data", not as an unhandled crash."""
        session = _make_session(
            status=200,
            json_error=ContentTypeError(
                request_info=MagicMock(),
                history=(),
            ),
        )
        client = TafApiClient(session)

        with pytest.raises(ValueError, match="No TAF data"):
            await client.get_taf("EDFE")
