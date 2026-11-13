from collections.abc import Iterable
from unittest.mock import MagicMock

import pytest
from simple_rest_client.exceptions import AuthError, ClientError, NotFoundError

from pyargus import api
from pyargus.client import Client, PublicClient
from pyargus.models import ExpiringToken, Incident
from pyargus.time import now as utcnow


class TestApiIntegration:
    def test_incidents_list_should_return_iterable(self, api_client):
        incidents = api_client.get_incidents()
        assert isinstance(incidents, Iterable)

    def test_when_posting_incident_it_should_return_full_incident(self, api_client):
        post = Incident(
            description="The earth was demolished to make way for a hyperspace bypass",
            start_time=utcnow(),
            tags={
                "host": "earth.example.org",
            },
        )
        result = api_client.post_incident(post)
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
    def test_when_authenticated_as_source_send_heartbeat_should_not_raise(
        self, api_client
    ):
        assert api_client.send_heartbeat() is None

    # supports_heartbeat() returns False against Argus <= 2.9.1 (no endpoint,
    # GET -> 404). Asserting the supporting-server result (True) keeps this test
    # symmetric with the send_heartbeat xfail above: it is expected to fail until
    # the suite runs against an Argus that provides sources/heartbeat/, at which
    # point (being strict) it flips to a failure prompting removal of the marker.
    @pytest.mark.xfail(
        strict=True,
        reason="Argus <= 2.9.1 has no sources/heartbeat/ endpoint; detection is False",
    )
    def test_when_server_provides_endpoint_supports_heartbeat_should_be_true(
        self, api_client
    ):
        assert api_client.supports_heartbeat() is True


class TestSendHeartbeat:
    def test_when_called_it_should_post_to_the_sources_heartbeat_action(self):
        client = Client("https://argus.example.org/api/v2", "token")
        client.api.sources.heartbeat = MagicMock()
        result = client.send_heartbeat()
        client.api.sources.heartbeat.assert_called_once_with()
        assert result is None


class TestSupportsHeartbeat:
    def test_when_server_answers_2xx_it_should_return_true(self):
        client = self._client_with_probe(return_value=object())
        assert client.supports_heartbeat() is True
        client.api.sources.heartbeat_probe.assert_called_once_with()

    def test_when_server_answers_404_it_should_return_false(self):
        client = self._client_with_probe(side_effect=NotFoundError("not found", None))
        assert client.supports_heartbeat() is False

    def test_when_get_is_not_allowed_it_should_return_true(self):
        client = self._client_with_probe(side_effect=ClientError("405", None))
        assert client.supports_heartbeat() is True

    def test_when_credentials_are_invalid_it_should_raise(self):
        client = self._client_with_probe(side_effect=AuthError("401", None))
        with pytest.raises(AuthError):
            client.supports_heartbeat()

    def _client_with_probe(self, side_effect=None, return_value=None):
        client = Client("https://argus.example.org/api/v2", "token")
        client.api.sources.heartbeat_probe = MagicMock(
            side_effect=side_effect, return_value=return_value
        )
        return client


# unit
class TestRefreshToken:
    def test_when_called_it_should_post_to_the_tokens_refresh_action(self):
        dummy_body = {
            "token": "vfbgnhuhgvfhnj",
            "expiry": "1970-01-01T00:00:00+01:00",
        }
        mock = MagicMock()
        mock.body = dummy_body
        client = self._client_with_probe(return_value=mock)
        result = client.refresh_token()
        client.api.tokens.refresh.assert_called_once_with()
        assert result

    def test_when_credentials_are_invalid_it_should_raise(self):
        client = self._client_with_probe(side_effect=AuthError("401", None))
        with pytest.raises(AuthError):
            client.refresh_token()

    def _client_with_probe(self, side_effect=None, return_value=None):
        client = Client("https://argus.example.org/api/v2", "token")
        client.api.tokens.refresh = MagicMock(
            side_effect=side_effect, return_value=return_value
        )
        return client


class TestLogin:
    def test_when_credentials_are_accepted_it_should_use_the_new_token(
        self, fake_public_api
    ):
        client = Client.login("https://argus.example.org/api/v2", "user", "secret")
        assert client.api.headers["Authorization"] == "Token fresh-token"

    def test_when_called_it_should_send_username_and_password(self, fake_public_api):
        Client.login("https://argus.example.org/api/v2", "user", "secret")
        body = fake_public_api.tokens.login.call_args.kwargs["body"]
        assert body == {"username": "user", "password": "secret"}

    def test_when_credentials_are_rejected_it_should_raise(self, fake_public_api):
        fake_public_api.tokens.login.side_effect = AuthError("403", None)
        with pytest.raises(AuthError):
            Client.login("https://argus.example.org/api/v2", "user", "wrong")


# unit
class TestPublicClient:
    def test_when_repr_of_the_instance_it_should_return_the_correct_format(self):
        url = "hlhl/v45"
        client = PublicClient(url)
        assert repr(client) == f"<PublicClient '{url}'>"

    def test_when_calling_login_tt_should_delegate_to_login_function(
        self, fake_public_api
    ):
        result = PublicClient("blbl").login("a", "b", "c")
        fake_public_api.tokens.login.assert_called_once()
        assert isinstance(result, ExpiringToken)


@pytest.fixture
def fake_public_api(monkeypatch):
    public_api = MagicMock()
    public_api.tokens.login.return_value.body = {
        "token": "fresh-token",
        "expiry": "2026-10-31T08:00:00+11:00",
    }
    monkeypatch.setattr(api, "public_connect", MagicMock(return_value=public_api))
    return public_api


@pytest.fixture
def api_client(argus_api_url, argus_source_system_token):
    return Client(argus_api_url, argus_source_system_token)


@pytest.fixture
def public_api_client(argus_api_url):
    return PublicClient(argus_api_url)
