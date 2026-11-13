"""Defines a low-level API interface for Argus using simple_rest_client"""

from urllib.parse import urljoin

from simple_rest_client.api import API
from simple_rest_client.resource import Resource

DEFAULT_TIMEOUT = 2.0


def server_root_url(api_root_url: str) -> str:
    """Returns the URL one level above the versioned API root"""
    return urljoin(api_root_url.rstrip("/") + "/", "..")


def connect(
    api_root_url: str, token: str = "", timeout: float = DEFAULT_TIMEOUT
) -> API:
    """Connects to an Argus API instance.

    :returns: A connected simple_rest_client API object
    """
    headers = {"Authorization": "Token " + token} if token else None
    argusapi = configure_api_object(
        api_root_url=api_root_url,
        headers=headers,
        timeout=timeout,
    )
    argusapi.add_resource(resource_name="incidents", resource_class=IncidentResource)
    argusapi.add_resource(resource_name="events", resource_class=IncidentEventResource)
    argusapi.add_resource(
        resource_name="acknowledgements", resource_class=IncidentAcknowledgementResource
    )
    argusapi.add_resource(resource_name="sources", resource_class=SourceSystemResource)
    argusapi.add_resource(resource_name="tokens", resource_class=ExpiringTokenResource)
    argusapi.add_resource(
        resource_name="metadata",
        resource_class=ServerMetadataResource,
        api_root_url=server_root_url(api_root_url),
    )
    return argusapi


def configure_api_object(
    api_root_url: str,
    headers: dict | None = None,
    timeout: float = DEFAULT_TIMEOUT,
    json_encode_body: bool = True,
    append_slash: bool = True,
):
    if headers is None:
        headers = {}
    return API(
        api_root_url=api_root_url,
        headers=headers,
        timeout=timeout,
        json_encode_body=json_encode_body,
        append_slash=append_slash,
    )


class IncidentResource(Resource):
    actions = {
        "list": {"method": "GET", "url": "incidents"},
        "list_mine": {"method": "GET", "url": "incidents/mine"},
        "list_open": {"method": "GET", "url": "incidents/open"},
        "list_open_unacked": {"method": "GET", "url": "incidents/open+unacked"},
        "create": {"method": "POST", "url": "incidents"},
        "retrieve": {"method": "GET", "url": "incidents/{}"},
        "update": {"method": "PATCH", "url": "incidents/{}"},
        "set_ticket_url": {"method": "PUT", "url": "incidents/{}/ticket_url/"},
    }


class IncidentEventResource(Resource):
    actions = {
        "list": {"method": "GET", "url": "incidents/{}/events"},
        "create": {"method": "POST", "url": "incidents/{}/events"},
        "retrieve": {"method": "GET", "url": "incidents/{}/events/{}"},
    }


class IncidentAcknowledgementResource(Resource):
    actions = {
        "list": {"method": "GET", "url": "incidents/{}/acks"},
        "create": {"method": "POST", "url": "incidents/{}/acks"},
        "retrieve": {"method": "GET", "url": "incidents/{}/acks/{}"},
    }


class SourceSystemResource(Resource):
    actions = {
        # The Argus source system endpoints are served under the incident app,
        # hence the "incidents/" URL prefix.
        "heartbeat": {"method": "POST", "url": "incidents/sources/heartbeat/"},
        # A GET against the same URL is used only to probe for endpoint support:
        # the endpoint accepts POST only, so it answers non-404 (405 today) when
        # present and 404 when absent on older servers. See supports_heartbeat().
        "heartbeat_probe": {"method": "GET", "url": "incidents/sources/heartbeat/"},
    }


class ExpiringTokenResource(Resource):
    actions = {
        # When accessed with a token, takes an empty JSON body or nothing
        "refresh": {"method": "POST", "url": "auth/token/login/"},
        # When accessed without a token, takes a JSON body with username/password:
        # { "username": "somestring", "password": "someothernonencryptedstring" }
        "login": {"method": "POST", "url": "auth/token/login/"},
    }


class ServerMetadataResource(Resource):
    actions = {
        "metadata": {"method": "GET", "url": ""},
    }
