from collections.abc import AsyncIterable
from unittest.mock import AsyncMock

import pytest
from simple_rest_client.exceptions import AuthError, ClientError, NotFoundError

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

    # supports_heartbeat() returns False against Argus <= 2.9.1 (no endpoint,
    # GET -> 404). Asserting the supporting-server result (True) keeps this test
    # symmetric with the send_heartbeat xfail above: it is expected to fail until
    # the suite runs against an Argus that provides sources/heartbeat/, at which
    # point (being strict) it flips to a failure prompting removal of the marker.
    @pytest.mark.xfail(
        strict=True,
        reason="Argus <= 2.9.1 has no sources/heartbeat/ endpoint; detection is False",
    )
    @pytest.mark.asyncio
    async def test_when_server_provides_endpoint_supports_heartbeat_should_be_true(
        self, async_api_client
    ):
        assert await async_api_client.supports_heartbeat() is True


class TestAsyncSendHeartbeat:
    @pytest.mark.asyncio
    async def test_when_called_it_should_post_to_the_sources_heartbeat_action(self):
        client = AsyncClient("https://argus.example.org/api/v2", "token")
        client.api.sources.heartbeat = AsyncMock()
        result = await client.send_heartbeat()
        client.api.sources.heartbeat.assert_awaited_once_with()
        assert result is None


class TestAsyncSupportsHeartbeat:
    @pytest.mark.asyncio
    async def test_when_server_answers_2xx_it_should_return_true(self):
        client = self._client_with_probe(return_value=object())
        assert await client.supports_heartbeat() is True
        client.api.sources.heartbeat_probe.assert_awaited_once_with()

    @pytest.mark.asyncio
    async def test_when_server_answers_404_it_should_return_false(self):
        client = self._client_with_probe(side_effect=NotFoundError("not found", None))
        assert await client.supports_heartbeat() is False

    @pytest.mark.asyncio
    async def test_when_get_is_not_allowed_it_should_return_true(self):
        client = self._client_with_probe(side_effect=ClientError("405", None))
        assert await client.supports_heartbeat() is True

    @pytest.mark.asyncio
    async def test_when_credentials_are_invalid_it_should_raise(self):
        client = self._client_with_probe(side_effect=AuthError("401", None))
        with pytest.raises(AuthError):
            await client.supports_heartbeat()

    def _client_with_probe(self, side_effect=None, return_value=None):
        client = AsyncClient("https://argus.example.org/api/v2", "token")
        client.api.sources.heartbeat_probe = AsyncMock(
            side_effect=side_effect, return_value=return_value
        )
        return client


@pytest.fixture
def async_api_client(argus_api_url, argus_source_system_token):
    return AsyncClient(argus_api_url, argus_source_system_token)
