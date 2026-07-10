"""Pyargus time related functions"""

from datetime import datetime, timezone

LOCAL_INFINITY = datetime.max.replace(tzinfo=timezone.utc)


def now() -> datetime:
    """Returns current time as UTC time with timezone information"""
    return datetime.now(timezone.utc)
