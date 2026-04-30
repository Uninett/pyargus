"""Tests for async API module"""

import pytest

from pyargus import async_api


def test_async_connect_should_return_api_client():
    client = async_api.async_connect("random", "token")
    assert client


@pytest.mark.asyncio
async def test_async_api_client_with_bad_args_should_fail():
    client = async_api.async_connect("random", "token")
    with pytest.raises(Exception):
        await client.incidents.list_open_unacked()
