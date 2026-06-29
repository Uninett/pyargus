import copy
import json
import pickle
import warnings

import pytest

from pyargus.multivaluedict import MultiValueDict


def assert_no_warning(func):
    """Call ``func`` and fail if it emits a DeprecationWarning."""
    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        return func()


def assert_invariant(d):
    """Assert the collapsed base and the ``_lists`` store agree.

    This is the structural contract every mutation must preserve: the two stores
    hold the same keys, no value list is empty, and the collapsed value for each
    key is the last of its values.
    """
    assert set(d.keys()) == set(d._lists.keys())
    for key, values in d._lists.items():
        assert values, f"empty value list for {key!r}"
        assert dict.__getitem__(d, key) == values[-1]


class TestMultiValueDictConstruction:
    def test_when_given_no_args_it_should_be_empty(self):
        d = MultiValueDict()
        assert len(d) == 0
        assert d.lists() == []

    def test_when_given_pairs_with_repeated_key_it_should_preserve_all_values(self):
        d = MultiValueDict([("host", "a"), ("host", "b")])
        assert d.getlist("host") == ["a", "b"]

    def test_when_given_pairs_with_repeated_key_collapsed_should_be_last(self):
        d = MultiValueDict([("host", "a"), ("host", "b")])
        assert dict(d) == {"host": "b"}

    def test_when_given_plain_dict_it_should_store_single_values(self):
        d = MultiValueDict({"host": "a", "loc": "oslo"})
        assert d.getlist("host") == ["a"]
        assert d.getlist("loc") == ["oslo"]

    def test_when_given_another_multivaluedict_it_should_copy_all_values(self):
        source = MultiValueDict([("host", "a"), ("host", "b")])
        d = MultiValueDict(source)
        assert d.getlist("host") == ["a", "b"]

    def test_when_copied_from_multivaluedict_it_should_be_independent(self):
        source = MultiValueDict([("host", "a")])
        d = MultiValueDict(source)
        d.add("host", "b")
        assert source.getlist("host") == ["a"]

    def test_when_given_keyword_args_it_should_store_single_values(self):
        d = MultiValueDict(host="a", loc="oslo")
        assert d.getlist("host") == ["a"]
        assert d.getlist("loc") == ["oslo"]

    def test_when_given_mapping_and_kwargs_it_should_apply_kwargs_last(self):
        d = MultiValueDict({"host": "a"}, host="b")
        assert dict(d) == {"host": "b"}

    def test_when_given_more_than_one_positional_arg_it_should_raise_typeerror(self):
        with pytest.raises(TypeError):
            MultiValueDict({"a": "1"}, {"b": "2"})

    def test_when_given_generator_of_pairs_it_should_preserve_repeated_keys(self):
        d = MultiValueDict(pair for pair in [("host", "a"), ("host", "b")])
        assert d.getlist("host") == ["a", "b"]

    def test_when_given_mapping_like_with_keys_it_should_treat_as_mapping(self):
        # Anything exposing keys() is treated as a mapping (the dict.update rule),
        # not as a pairs iterable.
        class MappingLike:
            def keys(self):
                return ["host"]

            def __getitem__(self, key):
                return "a"

        d = MultiValueDict(MappingLike())
        assert d.getlist("host") == ["a"]


class TestMultiValueDictCollapsedView:
    def test_when_key_has_multiple_values_collapsed_value_should_be_last(self):
        d = MultiValueDict([("host", "a"), ("host", "b")])
        assert assert_no_warning(lambda: dict(d)["host"]) == "b"

    def test_when_iterated_it_should_yield_each_key_once(self):
        d = MultiValueDict([("host", "a"), ("host", "b"), ("loc", "oslo")])
        assert list(d) == ["host", "loc"]

    def test_when_dumped_to_json_it_should_emit_collapsed_view(self):
        d = MultiValueDict([("host", "a"), ("host", "b")])
        assert json.loads(json.dumps(d)) == {"host": "b"}

    def test_when_len_called_it_should_count_distinct_keys(self):
        d = MultiValueDict([("host", "a"), ("host", "b"), ("loc", "oslo")])
        assert len(d) == 2

    def test_when_empty_it_should_be_falsy(self):
        assert not MultiValueDict()

    def test_when_nonempty_it_should_be_truthy(self):
        assert MultiValueDict([("host", "a")])

    def test_when_str_called_it_should_show_expanded_structure(self):
        d = MultiValueDict([("host", "a"), ("host", "b")])
        assert str(d) == repr(d)


class TestMultiValueDictMultiAccessors:
    def test_when_getlist_called_it_should_return_copy_of_values(self):
        d = MultiValueDict([("host", "a"), ("host", "b")])
        values = d.getlist("host")
        values.append("c")
        assert d.getlist("host") == ["a", "b"]

    def test_when_getlist_called_on_missing_key_it_should_return_empty_list(self):
        assert MultiValueDict().getlist("nope") == []

    def test_when_add_called_it_should_append_and_update_collapsed(self):
        d = MultiValueDict([("host", "a")])
        d.add("host", "b")
        assert d.getlist("host") == ["a", "b"]
        assert assert_no_warning(lambda: dict(d)["host"]) == "b"

    def test_when_setlist_called_it_should_replace_all_values(self):
        d = MultiValueDict([("host", "a"), ("host", "b")])
        d.setlist("host", ["x", "y", "z"])
        assert d.getlist("host") == ["x", "y", "z"]

    def test_when_setlist_called_on_absent_key_it_should_add_it(self):
        d = MultiValueDict()
        d.setlist("host", ["a", "b"])
        assert d.getlist("host") == ["a", "b"]

    def test_when_setlist_called_with_empty_it_should_remove_key(self):
        d = MultiValueDict([("host", "a")])
        d.setlist("host", [])
        assert "host" not in d

    def test_when_setlist_called_with_empty_on_absent_key_it_should_noop(self):
        d = MultiValueDict()
        d.setlist("host", [])
        assert "host" not in d

    def test_when_lists_called_it_should_return_pairs_of_key_and_value_list(self):
        d = MultiValueDict([("host", "a"), ("host", "b"), ("loc", "oslo")])
        assert d.lists() == [("host", ["a", "b"]), ("loc", ["oslo"])]

    def test_when_returned_lists_mutated_it_should_not_affect_internal_state(self):
        d = MultiValueDict([("host", "a")])
        d.lists()[0][1].append("b")
        assert d.getlist("host") == ["a"]

    def test_when_allitems_called_it_should_return_every_pair_including_repeats(self):
        d = MultiValueDict([("host", "a"), ("host", "b"), ("loc", "oslo")])
        assert d.allitems() == [("host", "a"), ("host", "b"), ("loc", "oslo")]

    def test_when_allitems_called_it_should_not_warn_on_multivalued_keys(self):
        d = MultiValueDict([("host", "a"), ("host", "b")])
        assert assert_no_warning(d.allitems) == [("host", "a"), ("host", "b")]


class TestMultiValueDictAssignmentAndDeletion:
    def test_when_item_assigned_it_should_replace_prior_values(self):
        d = MultiValueDict([("host", "a"), ("host", "b")])
        d["host"] = "x"
        assert d.getlist("host") == ["x"]

    def test_when_del_item_it_should_remove_key_and_all_values(self):
        d = MultiValueDict([("host", "a"), ("host", "b")])
        del d["host"]
        assert "host" not in d
        assert d.getlist("host") == []

    def test_when_pop_called_it_should_return_collapsed_scalar_and_remove_key(self):
        d = MultiValueDict([("host", "a"), ("host", "b")])
        assert assert_no_warning(lambda: d.pop("host")) == "b"
        assert "host" not in d

    def test_when_pop_missing_with_default_it_should_return_default(self):
        assert MultiValueDict().pop("nope", "fallback") == "fallback"

    def test_when_pop_missing_without_default_it_should_raise_keyerror(self):
        with pytest.raises(KeyError):
            MultiValueDict().pop("nope")

    def test_when_popitem_called_it_should_remove_a_key_entirely(self):
        d = MultiValueDict([("host", "a"), ("host", "b")])
        key, value = d.popitem()
        assert key == "host"
        assert d.getlist("host") == []

    def test_when_clear_called_it_should_empty_both_stores(self):
        d = MultiValueDict([("host", "a"), ("loc", "oslo")])
        d.clear()
        assert len(d) == 0
        assert d.lists() == []

    def test_when_remove_called_it_should_drop_one_occurrence(self):
        d = MultiValueDict([("host", "a"), ("host", "b")])
        d.remove("host", "a")
        assert d.getlist("host") == ["b"]

    def test_when_remove_last_occurrence_it_should_delete_key(self):
        d = MultiValueDict([("host", "a")])
        d.remove("host", "a")
        assert "host" not in d

    def test_when_remove_drops_last_value_collapsed_should_recompute(self):
        d = MultiValueDict([("host", "a"), ("host", "b")])
        d.remove("host", "b")
        assert assert_no_warning(lambda: dict(d)["host"]) == "a"

    def test_when_remove_value_absent_it_should_raise_valueerror(self):
        d = MultiValueDict([("host", "a")])
        with pytest.raises(ValueError):
            d.remove("host", "nope")

    def test_when_poplist_called_it_should_return_all_values_and_remove_key(self):
        d = MultiValueDict([("host", "a"), ("host", "b")])
        assert d.poplist("host") == ["a", "b"]
        assert "host" not in d

    def test_when_poplist_missing_it_should_raise_keyerror(self):
        with pytest.raises(KeyError):
            MultiValueDict().poplist("nope")

    def test_when_setdefault_on_missing_it_should_set_and_return_default(self):
        d = MultiValueDict()
        assert d.setdefault("host", "a") == "a"
        assert d.getlist("host") == ["a"]

    def test_when_setdefault_on_present_it_should_return_existing_collapsed(self):
        d = MultiValueDict([("host", "a"), ("host", "b")])
        assert assert_no_warning(lambda: d.setdefault("host", "x")) == "b"
        assert d.getlist("host") == ["a", "b"]

    def test_when_update_with_mapping_it_should_replace_and_stay_synced(self):
        d = MultiValueDict([("host", "a"), ("host", "b")])
        d.update({"host": "x", "loc": "oslo"})
        assert d.getlist("host") == ["x"]
        assert d.getlist("loc") == ["oslo"]
        assert_invariant(d)

    def test_when_update_with_multivaluedict_it_should_carry_all_values(self):
        d = MultiValueDict([("host", "a")])
        d.update(MultiValueDict([("host", "x"), ("host", "y")]))
        assert d.getlist("host") == ["x", "y"]
        assert assert_no_warning(lambda: dict(d)["host"]) == "y"
        assert_invariant(d)

    def test_when_remove_missing_key_it_should_raise_keyerror(self):
        with pytest.raises(KeyError):
            MultiValueDict().remove("nope", "x")


class TestMultiValueDictLossyReadWarning:
    def test_when_key_has_multiple_values_getitem_should_warn(self):
        d = MultiValueDict([("host", "a"), ("host", "b")])
        with pytest.warns(DeprecationWarning):
            assert d["host"] == "b"

    def test_when_key_has_single_value_getitem_should_not_warn(self):
        d = MultiValueDict([("loc", "oslo")])
        assert assert_no_warning(lambda: d["loc"]) == "oslo"

    def test_when_key_has_multiple_values_get_should_warn(self):
        d = MultiValueDict([("host", "a"), ("host", "b")])
        with pytest.warns(DeprecationWarning):
            assert d.get("host") == "b"

    def test_when_key_has_single_value_get_should_not_warn(self):
        d = MultiValueDict([("loc", "oslo")])
        assert assert_no_warning(lambda: d.get("loc")) == "oslo"

    def test_when_get_with_default_on_multivalued_key_it_should_warn_and_return_last(
        self,
    ):
        d = MultiValueDict([("host", "a"), ("host", "b")])
        with pytest.warns(DeprecationWarning):
            assert d.get("host", "fallback") == "b"

    def test_when_get_with_default_on_missing_key_it_should_return_default(self):
        d = MultiValueDict([("host", "a")])
        assert assert_no_warning(lambda: d.get("nope", "fallback")) == "fallback"

    def test_when_lossy_read_warning_should_point_at_caller(self):
        d = MultiValueDict([("host", "a"), ("host", "b")])
        with pytest.warns(DeprecationWarning) as record:
            d["host"]
        assert record[0].filename == __file__


class TestMultiValueDictEquality:
    def test_when_same_multivalues_two_instances_should_be_equal(self):
        a = MultiValueDict([("host", "a"), ("host", "b")])
        b = MultiValueDict([("host", "a"), ("host", "b")])
        assert a == b

    def test_when_collapsed_equal_but_multivalues_differ_should_not_be_equal(self):
        a = MultiValueDict([("host", "a"), ("host", "b")])
        b = MultiValueDict([("host", "b")])
        assert a != b
        assert not (a == b)

    def test_when_compared_to_equal_plain_dict_it_should_equal_collapsed_view(self):
        a = MultiValueDict([("host", "a"), ("host", "b")])
        assert a == {"host": "b"}
        assert not (a != {"host": "b"})

    def test_when_compared_to_unequal_object_it_should_not_be_equal(self):
        assert MultiValueDict([("host", "a")]) != "not a dict"

    def test_when_compared_to_equal_plain_dict_subclass_it_should_be_equal(self):
        class CustomDict(dict):
            pass

        a = MultiValueDict([("host", "a"), ("host", "b")])
        assert a == CustomDict(host="b")


class TestMultiValueDictCopyPickleReprUnion:
    def test_when_copy_method_called_it_should_return_independent_multivaluedict(self):
        src = MultiValueDict([("host", "a"), ("host", "b")])
        clone = src.copy()
        assert isinstance(clone, MultiValueDict)
        assert clone.getlist("host") == ["a", "b"]
        clone.add("host", "c")
        assert src.getlist("host") == ["a", "b"]

    def test_when_copy_copy_called_it_should_preserve_multivalues(self):
        src = MultiValueDict([("host", "a"), ("host", "b")])
        assert copy.copy(src).getlist("host") == ["a", "b"]

    def test_when_deepcopy_called_it_should_preserve_multivalues_and_be_independent(
        self,
    ):
        src = MultiValueDict([("host", "a"), ("host", "b")])
        clone = copy.deepcopy(src)
        assert clone.getlist("host") == ["a", "b"]
        clone.add("host", "c")
        assert src.getlist("host") == ["a", "b"]

    def test_when_pickled_and_unpickled_it_should_preserve_multivalues(self):
        src = MultiValueDict([("host", "a"), ("host", "b")])
        restored = pickle.loads(pickle.dumps(src))
        assert isinstance(restored, MultiValueDict)
        assert restored.getlist("host") == ["a", "b"]

    def test_when_repr_called_it_should_round_trip_via_constructor(self):
        src = MultiValueDict([("host", "a"), ("host", "b"), ("loc", "oslo")])
        assert eval(repr(src)) == src

    def test_when_union_operator_used_it_should_return_multivaluedict(self):
        result = MultiValueDict([("host", "a")]) | {"host": "b", "loc": "oslo"}
        assert isinstance(result, MultiValueDict)
        assert result.getlist("host") == ["b"]
        assert result.getlist("loc") == ["oslo"]

    def test_when_reverse_union_with_plain_mapping_it_should_return_multivaluedict(
        self,
    ):
        class Mapping(dict):
            pass

        result = MultiValueDict([("host", "b")]).__ror__(Mapping(host="a"))
        assert isinstance(result, MultiValueDict)
        assert result.getlist("host") == ["b"]

    def test_when_inplace_union_used_with_multivaluedict_it_should_carry_values(self):
        d = MultiValueDict([("a", "1")])
        d |= MultiValueDict([("a", "2"), ("a", "3")])
        assert d.getlist("a") == ["2", "3"]

    def test_when_fromkeys_used_it_should_build_multivaluedict(self):
        d = MultiValueDict.fromkeys(["a", "b"], 0)
        assert isinstance(d, MultiValueDict)
        assert dict(d) == {"a": 0, "b": 0}


class TestMultiValueDictInvariant:
    def test_when_mutated_through_a_sequence_it_should_stay_consistent(self):
        # Drive the structure through every mutating operation and assert the
        # collapsed base never drifts from the _lists store along the way.
        d = MultiValueDict([("host", "a"), ("host", "b")])
        operations = [
            lambda: d.add("host", "c"),
            lambda: d.add("loc", "oslo"),
            lambda: d.__setitem__("host", "z"),
            lambda: d.setlist("host", ["1", "2", "3"]),
            lambda: d.remove("host", "2"),
            lambda: d.update(MultiValueDict([("host", "x"), ("host", "y")])),
            lambda: d.update({"loc": "bergen"}),
            lambda: d.__ior__(MultiValueDict([("env", "prod"), ("env", "test")])),
            lambda: d.poplist("host"),
            lambda: d.pop("loc"),
            lambda: d.setdefault("new", "val"),
            lambda: d.popitem(),
        ]
        for operation in operations:
            operation()
            assert_invariant(d)
