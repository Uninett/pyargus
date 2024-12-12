from collections.abc import Iterable
from datetime import datetime

import pytest

from pyargus.client import Client
from pyargus.models import Incident


class TestApiIntegration:
    def test_incidents_list_should_return_iterable(self, api_client):
        incidents = api_client.get_incidents()
        assert isinstance(incidents, Iterable)

    @pytest.mark.xfail(
        reason="We must add a source system to Argus to do this properly"
    )
    def test_when_posting_incident_it_should_return_full_incident(self, api_client):
        post = Incident(
            description="The earth was demolished to make way for a hyperspace bypass",
            start_time=datetime.now(),
            tags={
                "host": "earth.example.org",
            },
        )
        result = api_client.post_incident(post)
        assert isinstance(result, Incident)
        assert result.description == post.description
        assert result.pk


@pytest.fixture
def api_client(argus_api):
    url, token = argus_api
    return Client(url, token)
