from aktreader.artifact import first_json_difference


def test_first_json_difference_uses_stable_sorted_object_keys() -> None:
    expected = {"z": 1, "a": {"value": 1}}
    observed = {"z": 2, "a": {"value": 2}}

    assert first_json_difference(expected, observed) == "/a/value"


def test_first_json_difference_escapes_json_pointer_parts() -> None:
    assert first_json_difference({"a/b": 1}, {"a/b": 2}) == "/a~1b"
    assert first_json_difference({"a~b": 1}, {"a~b": 2}) == "/a~0b"


def test_first_json_difference_reports_list_length_and_root_type_changes() -> None:
    assert first_json_difference({"items": [1]}, {"items": [1, 2]}) == "/items/1"
    assert first_json_difference({}, []) == "/"
    assert first_json_difference({"same": [1]}, {"same": [1]}) is None
