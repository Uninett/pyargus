"""Defines an async low-level API interface for Argus using simple_rest_client"""

from simple_rest_client.api import API
from simple_rest_client.resource import AsyncResource

from .api import (
    DEFAULT_TIMEOUT,
    ExpiringTokenResource,
    IncidentAcknowledgementResource,
    IncidentEventResource,
    IncidentResource,
    PublicExpiringTokenResource,
    ServerMetadataResource,
    SourceSystemResource,
    configure_api_object,
)


def async_connect(
    api_root_url: str, token: str, timeout: float = DEFAULT_TIMEOUT
) -> API:
    """Connects to an Argus API instance using async resources.

    :returns: A connected simple_rest_client API object with async resources
    """
    headers = {"Authorization": "Token " + token}
    argusapi = configure_api_object(
        api_root_url=api_root_url,
        headers=headers,
        timeout=timeout,
    )
    argusapi.add_resource(
        resource_name="incidents", resource_class=AsyncIncidentResource
    )
    argusapi.add_resource(
        resource_name="events", resource_class=AsyncIncidentEventResource
    )
    argusapi.add_resource(
        resource_name="acknowledgements",
        resource_class=AsyncIncidentAcknowledgementResource,
    )
    argusapi.add_resource(
        resource_name="sources", resource_class=AsyncSourceSystemResource
    )
    argusapi.add_resource(
        resource_name="tokens", resource_class=AsyncExpiringTokenResource
    )
    return argusapi


def async_public_connect(api_root_url: str, timeout: float = DEFAULT_TIMEOUT) -> API:
    """Connects to an Argus public API instance using async resources.

    :returns: A connected simple_rest_client API object for public endpoints
    with async resources
    """
    argusapi = configure_api_object(
        api_root_url=api_root_url,
        timeout=timeout,
    )
    argusapi.add_resource(
        resource_name="tokens", resource_class=AsyncPublicExpiringTokenResource
    )
    argusapi.add_resource(
        resource_name="metadata", resource_class=AsyncServerMetadataResource
    )
    return argusapi


class AsyncIncidentResource(AsyncResource):
    actions = IncidentResource.actions


class AsyncIncidentEventResource(AsyncResource):
    actions = IncidentEventResource.actions


class AsyncIncidentAcknowledgementResource(AsyncResource):
    actions = IncidentAcknowledgementResource.actions


class AsyncSourceSystemResource(AsyncResource):
    actions = SourceSystemResource.actions


class AsyncExpiringTokenResource(AsyncResource):
    actions = ExpiringTokenResource.actions


class AsyncPublicExpiringTokenResource(AsyncResource):
    actions = PublicExpiringTokenResource.actions


class AsyncServerMetadataResource(AsyncResource):
    actions = ServerMetadataResource.actions
