"""Slightly higher level Argus API client abstraction"""
from typing import List, Generic, TypeVar

from . import api
from . import models

IncidentType = TypeVar("IncidentType", int, models.Incident)


class Client:
    """High-level Argus API client.

    The low-level simple_rest_client API is available in the `api` instance variable.
    """

    def __init__(self, api_root_url: str, token: str, timeout: float = 2.0):
        self.api = api.connect(api_root_url, token, timeout)

    def get_incident(self, incident_id: int) -> models.Incident:
        """Retrieves an incident based on its Argus ID"""
        response = self.api.incidents.retrieve(incident_id)
        return models.Incident.from_json(response.body)

    def get_incidents(self, **filters) -> List[models.Incident]:
        """Retrieves a list of all incidents.

        Use keyword arguments for filtering, unless you want every last bit from the
        API.

        Usage example:
        >>> client.get_incidents(open=True, acked=False)
        [Incident(...), ...]
        """
        response = self.api.incidents.list(params=filters)
        return [models.Incident.from_json(record) for record in response.body]

    def get_my_incidents(self, **filters) -> List[models.Incident]:
        """Retrieves a list of all incidents that came from the Source System
        represented by this client.

        Use keyword arguments for filtering, unless you want every last bit from the
        API.

        Usage example:
        >>> client.get_my_incidents(open=True, acked=False)
        [Incident(...), ...]
        """
        response = self.api.incidents.list_mine(params=filters)
        return [models.Incident.from_json(record) for record in response.body]

    def get_incident_events(self, incident: IncidentType) -> List[models.Event]:
        """Returns a list of all events related to an Incident"""
        pk = incident["pk"] if isinstance(incident, models.Incident) else int(incident)
        response = self.api.events.list(pk)
        return [models.Event.from_json(record) for record in response.body]

    def get_incident_acknowledgements(
        self, incident: IncidentType
    ) -> List[models.Acknowledgement]:
        """Returns a list of all acknowledgements on an Incident"""
        pk = incident["pk"] if isinstance(incident, models.Incident) else int(incident)
        response = self.api.acknowledgements.list(pk)
        return [models.Acknowledgement.from_json(record) for record in response.body]
