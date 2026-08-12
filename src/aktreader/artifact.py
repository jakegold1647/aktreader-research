"""Shared deterministic helpers for replay-verifiable JSON artifacts."""

from __future__ import annotations

from typing import Any


def _json_pointer_part(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")


def first_json_difference(expected: Any, observed: Any, *, pointer: str = "") -> str | None:
    """Return the first stable JSON Pointer whose value does not reproduce."""

    if type(expected) is not type(observed):
        return pointer or "/"
    if isinstance(expected, dict):
        for key in sorted(set(expected) | set(observed)):
            child_pointer = f"{pointer}/{_json_pointer_part(key)}"
            if key not in expected or key not in observed:
                return child_pointer
            difference = first_json_difference(
                expected[key],
                observed[key],
                pointer=child_pointer,
            )
            if difference is not None:
                return difference
        return None
    if isinstance(expected, list):
        common_length = min(len(expected), len(observed))
        for index in range(common_length):
            difference = first_json_difference(
                expected[index],
                observed[index],
                pointer=f"{pointer}/{index}",
            )
            if difference is not None:
                return difference
        if len(expected) != len(observed):
            return f"{pointer}/{common_length}"
        return None
    return None if expected == observed else pointer or "/"
