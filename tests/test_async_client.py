from collections.abc import AsyncIterable
from datetime import datetime

import pytest

from pyargus.async_client import AsyncClient
from pyargus.models import Incident


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
            start_time=datetime.now(),
            tags={
                "host": "earth.example.org",
            },
        )
        result = await async_api_client.post_incident(post)
        assert isinstance(result, Incident)
        assert result.description == post.description
        assert result.pk


@pytest.fixture
def async_api_client(argus_api_url, argus_source_system_token):
    return AsyncClient(argus_api_url, argus_source_system_token)
