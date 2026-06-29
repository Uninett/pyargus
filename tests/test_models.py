from pyargus.models import Incident
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
