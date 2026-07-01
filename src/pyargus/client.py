"""Slightly higher level Argus API client abstraction"""

from __future__ import annotations

from datetime import datetime
from typing import Callable, Iterator, List, Optional, Tuple, TypeVar
from urllib.parse import parse_qs, urlparse

from simple_rest_client.exceptions import AuthError, ClientError, NotFoundError
from simple_rest_client.models import Response

from . import api, models
from .time import now as utcnow

__all__ = ["Client"]


IncidentType = TypeVar("IncidentType", int, models.Incident)


class Client:
    """High-level Argus API client.

    The low-level simple_rest_client API is available in the `api` instance variable.
    """

    def __init__(self, api_root_url: str, token: str, timeout: float = 2.0):
        self.api = api.connect(api_root_url, token, timeout)

    def __repr__(self):
        return f"<{self.__class__.__name__} {self.api.api_root_url!r}>"

    def get_incident(self, incident_id: int) -> models.Incident:
        """Retrieves an incident based on its Argus ID"""
        response = self.api.incidents.retrieve(incident_id)
        return models.Incident.from_json(response.body)

    def get_incidents(self, **filters) -> Iterator[models.Incident]:
        """Retrieves Argus Incidents as a generator.

        Use keyword arguments for filtering, unless you want every last bit from the
        API.

        Usage example:
        >>> list(client.get_incidents(open=True, acked=False))
        [Incident(...), ...]
        """
        for _response, results in paginated_query(
            self.api.incidents.list, params=filters
        ):
            for record in results:
                yield models.Incident.from_json(record)

    def get_my_incidents(self, **filters) -> Iterator[models.Incident]:
        """Retrieves all Incidents that came from the Source System represented by
        this client, returning them as a generator.

        Use keyword arguments for filtering, unless you want every last bit from the
        API.

        Usage example:
        >>> list(client.get_my_incidents(open=True, acked=False))
        [Incident(...), ...]
        """
        for _response, results in paginated_query(
            self.api.incidents.list_mine, params=filters
        ):
            for record in results:
                yield models.Incident.from_json(record)

    def get_incident_events(self, incident: IncidentType) -> List[models.Event]:
        """Returns a list of all events related to an Incident"""
        pk = incident.pk if isinstance(incident, models.Incident) else int(incident)
        response = self.api.events.list(pk)
        return [models.Event.from_json(record) for record in response.body]

    def get_incident_acknowledgements(
        self, incident: IncidentType
    ) -> List[models.Acknowledgement]:
        """Returns a list of all acknowledgements on an Incident"""
        pk = incident.pk if isinstance(incident, models.Incident) else int(incident)
        response = self.api.acknowledgements.list(pk)
        return [models.Acknowledgement.from_json(record) for record in response.body]

    def post_incident(self, incident: models.Incident) -> models.Incident:
        """Posts a new Incident to Argus.

        :returns: A full Incident description as returned from the API.
        """
        body = incident.to_json()
        response = self.api.incidents.create(body=body)
        return models.Incident.from_json(response.body)

    def update_incident(self, incident: models.Incident) -> models.Incident:
        """Updates an Argus Incident.

        :returns: A full Incident description as returned from the API.
        """
        pk = incident.pk
        body = incident.to_json()
        # The API takes the primary key as part of the URL, not as part of the body
        if "pk" in body:
            del body["pk"]
        response = self.api.incidents.update(pk, body=body)
        return models.Incident.from_json(response.body)

    def resolve_incident(
        self,
        incident: IncidentType,
        description: Optional[str] = None,
        timestamp: Optional[datetime] = None,
    ) -> models.Event:
        """Resolves an Argus Incident

        :param description: An optional event description to post.
        :param timestamp: When the event happened. Defaults to the current datetime.
        :returns: A full Event description as returned from the API.
        """
        if timestamp is None:
            timestamp = utcnow()
        end_event = models.Event(
            description=description, timestamp=timestamp, type="END"
        )
        return self.post_incident_event(incident, end_event)

    def restart_incident(
        self,
        incident: IncidentType,
        description: Optional[str] = None,
        timestamp: Optional[datetime] = None,
    ) -> models.Event:
        """Restarts an Argus Incident

        :param description: An optional event description to post.
        :param timestamp: When the event happened. Defaults to the current datetime.
        :returns: A full Event description as returned from the API.
        """
        if timestamp is None:
            timestamp = utcnow()
        restart_event = models.Event(
            description=description, timestamp=timestamp, type="RES"
        )
        return self.post_incident_event(incident, restart_event)

    def post_incident_event(
        self, incident: IncidentType, event: models.Event
    ) -> models.Event:
        """Posts a new Incident Event to Argus

        :returns: A full Event description as returned from the API.
        """
        incident_pk = incident if isinstance(incident, int) else incident.pk
        body = event.to_json()
        response = self.api.events.create(incident_pk, body=body)
        return models.Event.from_json(response.body)

    def supports_heartbeat(self) -> bool:
        """Detects whether the connected Argus server provides the heartbeat endpoint.

        Probes the endpoint with a GET request: a server that has it answers with
        a non-404 status (currently 405, as the endpoint only accepts POST), while
        a server too old to provide it answers with 404. Use this to decide whether
        to call `send_heartbeat()` at all.

        :returns: True if the server provides the heartbeat endpoint, else False.
        :raises AuthError: if the token is missing or invalid (HTTP 401); support
            cannot be determined without authenticating.
        """
        try:
            self.api.sources.heartbeat_probe()
            return True  # 2xx: the endpoint exists
        except NotFoundError:
            return False  # 404: the endpoint is absent (older Argus)
        except AuthError:
            raise  # 401: cannot determine support without valid credentials
        except ClientError:
            return True  # e.g. 405: the endpoint exists but GET is not allowed

    def send_heartbeat(self) -> None:
        """Sends a heartbeat to Argus to signal that this source system is alive.

        This updates the source system's `last_seen` timestamp server-side without
        posting an incident. Every glue service should send heartbeats on a regular
        schedule to prove it is alive: a source with nothing to report looks exactly
        like a source that has died, and a steady heartbeat is what lets Argus tell
        the two apart.

        On a non-2xx response it raises an exception from `simple_rest_client`, the
        underlying HTTP library (for example `AuthError` if the token does not
        belong to a source system). Note that an Argus server too old to provide
        this endpoint typically answers with a 403 as well, which is
        indistinguishable from a genuine authentication failure; use
        `supports_heartbeat()` to detect endpoint support up front rather than
        inferring it from this method's failure.
        """
        self.api.sources.heartbeat()

    def refresh_token(self) -> models.ExpiringToken:
        """Post w/o body to get a new token and its expiration timestamp

        It will be necessary to re-initialize the client as the old token has
        been rendered invalid.

        Store the new token (and the returned expiration datetime) where your
        program can load it on next run: environment variable, config file or
        secrets file.
        """
        response = self.api.tokens.refresh()
        return models.ExpiringToken.from_json(response.body)


def paginated_query(method: Callable, *args, **kwargs) -> Iterator[Tuple]:
    """Extracts paginated results from a simple_rest_client API call.

    This function is a generator that produces subsequent results for each page
    retrieved. Non-paginated results are also supported. Each generated value is a
    two-tuple of the form `(response, results)`, where `response` is the
    simple_rest_client response object and `results` is the list of results extracted
    from the response body.

    :type method: An API instance method to call
    :type args: Arguments to pass to method
    :type kwargs: Keyword arguments to pass to method

    """
    response = method(*args, **kwargs)
    if is_paginated_response(response):
        yield response, response.body["results"]

        while has_next_page(response):
            next_url = response.body["next"]
            kwargs["params"] = extract_params(next_url)
            response = method(*args, **kwargs)
            yield response, response.body["results"]

    else:
        yield response, response.body


def is_paginated_response(response: Response):
    """Returns True if the API response appears to be a paginated result"""
    return (
        isinstance(response.body, dict)
        and "next" in response.body
        and "results" in response.body
    )


def has_next_page(response: Response) -> bool:
    """Returns True if a paginated API response appears to have further result pages"""
    return bool(response.body.get("next"))


def extract_params(url: str) -> dict:
    """Extracts only the query parameters from a URL, return them as a dictionary"""
    parsed = urlparse(url)
    return parse_qs(parsed.query)
