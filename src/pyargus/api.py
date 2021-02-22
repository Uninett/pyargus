"""Defines a low-level API interface for Argus using simple_rest_client"""
from simple_rest_client.api import API
from simple_rest_client.resource import Resource


def connect(api_root_url: str, token: str, timeout: float = 2.0) -> API:
    """Connects to an Argus API instance.

    :returns: A connected simple_rest_client API object
    """
    headers = {"Authorization": "Token " + token}
    argusapi = API(
        api_root_url=api_root_url,
        headers=headers,
        timeout=timeout,
        json_encode_body=True,
        append_slash=True,
    )
    argusapi.add_resource(resource_name="incidents", resource_class=IncidentResource)
    argusapi.add_resource(resource_name="events", resource_class=IncidentEventResource)
    argusapi.add_resource(
        resource_name="acknowledgements", resource_class=IncidentAcknowledgementResource
    )
    return argusapi


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
