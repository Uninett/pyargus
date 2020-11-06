"""Slightly higher level Argus API client abstraction"""
from __future__ import annotations

from datetime import datetime
from typing import List, TypeVar, Iterator, Callable, Tuple
from urllib.parse import urlparse, parse_qs

from simple_rest_client.models import Response

from . import api
from . import models

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
        for response, results in paginated_query(
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
        for response, results in paginated_query(
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
        description: str = None,
        timestamp: datetime = None,
    ) -> models.Incident:
        """Resolves an Argus Incident

        :param description: An optional event description to post.
        :param timestamp: When the event happened. Defaults to the current datetime.
        :returns: A full Event description as returned from the API.
        """
        if timestamp is None:
            timestamp = datetime.now()
        end_event = models.Event(
            description=description, timestamp=timestamp, type="END"
        )
        return self.post_incident_event(incident, end_event)

    def post_incident_event(self, incident: IncidentType, event: models.Event):
        """Posts a new Incident Event to Argus

        :returns: A full Event description as returned from the API.
        """
        incident_pk = incident if isinstance(incident, int) else incident.pk
        body = event.to_json()
        response = self.api.events.create(incident_pk, body=body)
        return models.Event.from_json(response.body)


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
