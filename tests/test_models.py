from datetime import datetime

from pyargus.models import ExpiringToken, Incident, ServerMetadata
from pyargus.multivaluedict import MultiValueDict


def make_api_incident(tags):
    """A minimal Argus API incident payload carrying the given ``tags`` list."""
    return {
        "start_time": "2021-01-01T00:00:00+00:00",
        "end_time": None,
        "source": {"type": {"name": "test"}},
        "tags": tags,
    }


class TestIncidentFromJson:
    def test_when_tags_have_duplicate_keys_it_should_preserve_all_values(self):
        data = make_api_incident([{"tag": "host=a"}, {"tag": "host=b"}])
        incident = Incident.from_json(data)
        assert isinstance(incident.tags, MultiValueDict)
        assert incident.tags.getlist("host") == ["a", "b"]

    def test_when_tag_value_contains_equals_it_should_split_only_once(self):
        data = make_api_incident([{"tag": "url=https://example.org/?a=b"}])
        incident = Incident.from_json(data)
        assert incident.tags.getlist("url") == ["https://example.org/?a=b"]


class TestIncidentToJson:
    def test_when_tags_have_duplicate_values_it_should_emit_all(self):
        incident = Incident(tags=MultiValueDict([("host", "a"), ("host", "b")]))
        assert incident.to_json()["tags"] == [
            {"tag": "host=a"},
            {"tag": "host=b"},
        ]

    def test_when_tags_is_plain_dict_it_should_emit_list(self):
        incident = Incident(tags={"host": "earth.example.org"})
        assert incident.to_json()["tags"] == [{"tag": "host=earth.example.org"}]

    def test_when_tags_have_several_keys_it_should_group_values_by_key(self):
        incident = Incident(
            tags=MultiValueDict([("host", "a"), ("loc", "oslo"), ("host", "b")])
        )
        assert incident.to_json()["tags"] == [
            {"tag": "host=a"},
            {"tag": "host=b"},
            {"tag": "loc=oslo"},
        ]

    def test_when_tags_empty_it_should_emit_empty_list(self):
        assert Incident(tags=MultiValueDict()).to_json()["tags"] == []

    def test_when_tags_none_it_should_emit_empty_list(self):
        assert Incident().to_json()["tags"] == []


class TestIncidentTagRoundTrip:
    def test_when_round_tripped_duplicate_keys_should_survive(self):
        original = Incident(tags=MultiValueDict([("host", "a"), ("host", "b")]))
        data = make_api_incident(original.to_json()["tags"])
        restored = Incident.from_json(data)
        assert restored.tags.getlist("host") == ["a", "b"]


class TestExpiringToken:
    def test_when_parsing_response_with_expiry_set_should_return_a_tokenobj_with_expiry_set(
        self,
    ):
        dummy_json = {
            "token": "vfbgnhuhgvfhnj",
            "expiry": "1970-01-01T00:00:00+01:00",
        }
        tokenobj = ExpiringToken.from_json(dummy_json)
        assert tokenobj.token == dummy_json["token"]
        assert tokenobj.expiry == datetime.fromisoformat(dummy_json["expiry"])

    def test_when_parsing_response_with_no_expiry_should_return_a_tokenobj_with_expiry_set_to_none(
        self,
    ):
        dummy_json = {
            "token": "vfbgnhuhgvfhnj",
            "expiry": None,
        }
        tokenobj = ExpiringToken.from_json(dummy_json)
        assert tokenobj.token == dummy_json["token"]
        assert tokenobj.expiry is None


class TestServerMetadata:
    response = {
        "server-version": "2.10.2",
        "api-version": {"stable": "v2"},
        "jsonapi-schema": {
            "stable": "/api/schema/",
            "v2": "/api/v2/schema/",
            "v3": "/api/v3/schema/",
        },
        "ticket_plugin": "argus_ticket_rt.RequestTrackerPlugin",
        "destination_plugins": [
            "argus.notificationprofile.media.email.EmailNotification",
            "argus.notificationprofile.media.sms_as_email.SMSNotification",
        ],
    }
    expected = (
        "available_api_versions",
        "jsonapi_schema",
        "server_version",
        "stable_api_version",
    )
    metadata = ServerMetadata.from_json(response)

    def test_when_parsing_response_then_ensure_we_have_the_right_structure(self):
        for key in self.expected:
            assert hasattr(self.metadata, key)

        # copied without change
        assert self.metadata.jsonapi_schema == self.response["jsonapi-schema"]
        assert self.metadata.server_version == self.response["server-version"]

    def test_when_parsing_available_api_versions_then_stable_is_removed(self):
        assert "stable" not in self.metadata.available_api_versions

    def test_when_parsing_stable_api_version_then_flatten_the_structure(self):
        assert (
            self.metadata.stable_api_version == self.response["api-version"]["stable"]
        )
