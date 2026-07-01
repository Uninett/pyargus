import pytest

from pyargus import api


def test_connect_should_return_api_client():
    client = api.connect("random", "token")
    assert client


def test_api_client_with_bad_args_should_fail():
    client = api.connect("random", "token")
    with pytest.raises(Exception):
        client.incidents.list_open_unacked()


def test_connect_should_expose_source_heartbeat_action():
    client = api.connect("random", "token")
    action = client.sources.actions["heartbeat"]
    assert action["method"] == "POST"
    assert action["url"] == "incidents/sources/heartbeat/"
