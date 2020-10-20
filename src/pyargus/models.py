from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from iso8601 import parse_date


@dataclass
class SourceSystem:
    """Class for describing an Argus Source system"""

    pk: int = None
    name: str = None
    type: str = None
    user: int = None
    base_url: str = None

    @classmethod
    def from_json(cls, data: dict) -> SourceSystem:
        """Returns a SourceSystem object initalized from an Argus JSON dict"""
        kwargs = data.copy()
        kwargs["type"] = kwargs["type"]["name"]
        return cls(**kwargs)


@dataclass
class Incident:
    """Class for describing an Argus Incident"""

    pk: int = None
    start_time: datetime = None
    end_time: datetime = None
    source: SourceSystem = None
    source_incident_id: str = None
    details_url: str = None
    description: str = None
    ticket_url: str = None
    tags: dict = None
    stateful: bool = None
    open: bool = None
    acked: bool = None

    @classmethod
    def from_json(cls, data: dict) -> Incident:
        """Returns an Incident object initalized from an Argus JSON dict"""
        kwargs = data.copy()
        if kwargs["start_time"]:
            kwargs["start_time"] = parse_date(kwargs["start_time"])
        if kwargs["end_time"]:
            kwargs["end_time"] = (
                parse_date(kwargs["end_time"])
                if kwargs["end_time"] != "infinity"
                else datetime.max
            )
        kwargs["source"] = SourceSystem.from_json(kwargs["source"])

        tags = [tag["tag"] for tag in kwargs["tags"]]
        tags = dict(tag.split("=", maxsplit=1) for tag in tags)
        kwargs["tags"] = tags

        return cls(**kwargs)


@dataclass
class Event:
    """Class for describing an Argus Incident Event"""

    pk: int = None
    actor: str = None
    description: str = None
    incident: int = None
    received: datetime = None
    timestamp: datetime = None
    type: str = None

    @classmethod
    def from_json(cls, data: dict) -> Event:
        """Returns an Event object initalized from an Argus JSON dict"""
        kwargs = data.copy()
        kwargs["actor"] = kwargs.get("actor", {}).get("username")
        if kwargs["received"]:
            kwargs["received"] = parse_date(kwargs["received"])
        if kwargs["timestamp"]:
            kwargs["timestamp"] = parse_date(kwargs["timestamp"])
        kwargs["type"] = kwargs["type"]["value"]
        return cls(**kwargs)


@dataclass
class Acknowledgement:
    """Class for describing an Argus Acknowledgement"""

    pk: int = None
    expiration: datetime = None
    event: Event = None

    @classmethod
    def from_json(cls, data: dict) -> Acknowledgement:
        """Returns an Acknowledgement object initalized from an Argus JSON dict"""
        kwargs = {
            "pk": data["pk"],
            "event": Event.from_json(data["event"]),
            "expiration": parse_date(data["expiration"])
            if data["expiration"]
            else None,
        }
        return cls(**kwargs)
