from collections.abc import AsyncIterable
from unittest.mock import AsyncMock

import pytest
from simple_rest_client.exceptions import AuthError

from pyargus.async_client import AsyncClient
from pyargus.models import Incident
from pyargus.time import now as utcnow


class TestAsyncApiIntegration:
    @pytest.mark.asyncio
    async def test_incidents_list_should_return_async_iterable(self, async_api_client):
        incidents = async_api_client.get_incidents()
        assert isinstance(incidents, AsyncIterable)

    @pytest.mark.asyncio
    async def test_when_posting_incident_it_should_return_full_incident(
        self, async_api_client
    ):
        post = Incident(
            description="The earth was demolished to make way for a hyperspace bypass",
            start_time=utcnow(),
            tags={
                "host": "earth.example.org",
            },
        )
        result = await async_api_client.post_incident(post)
        assert isinstance(result, Incident)
        assert result.description == post.description
        assert result.pk

    # The heartbeat endpoint is unreleased as of Argus 2.9.1, the newest version
    # available for integration testing. A server without the endpoint answers
    # with 403, which pyargus surfaces as AuthError, so this test is expected to
    # fail until the suite runs against an Argus release that provides
    # sources/heartbeat/. Being strict, it will start failing (as XPASS) once
    # that happens -- at which point this marker should be removed.
    @pytest.mark.xfail(
        raises=AuthError,
        strict=True,
        reason="Argus <= 2.9.1 has no sources/heartbeat/ endpoint; returns 403",
    )
    @pytest.mark.asyncio
    async def test_when_authenticated_as_source_send_heartbeat_should_not_raise(
        self, async_api_client
    ):
        assert await async_api_client.send_heartbeat() is None


class TestAsyncSendHeartbeat:
    @pytest.mark.asyncio
    async def test_when_called_it_should_post_to_the_sources_heartbeat_action(self):
        client = AsyncClient("https://argus.example.org/api/v2", "token")
        client.api.sources.heartbeat = AsyncMock()
        result = await client.send_heartbeat()
        client.api.sources.heartbeat.assert_awaited_once_with()
        assert result is None


@pytest.fixture
def async_api_client(argus_api_url, argus_source_system_token):
    return AsyncClient(argus_api_url, argus_source_system_token)
