"""Shared immutable validator contracts."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): _freeze(child) for key, child in value.items()})
    if isinstance(value, list | tuple):
        return tuple(_freeze(child) for child in value)
    return value


def _thaw(value: Any) -> Any:
    """Return a JSON-safe copy of one frozen validator value."""

    if isinstance(value, Mapping):
        return {str(key): _thaw(child) for key, child in value.items()}
    if isinstance(value, list | tuple):
        return [_thaw(child) for child in value]
    return value


@dataclass(frozen=True)
class ValidationFinding:
    """A non-mutating mechanical flag with provenance."""

    code: str
    message: str
    record_ids: tuple[str, ...]
    field_paths: tuple[str, ...]
    severity: str = "FLAG"
    blocks_confident: bool = True
    evidence: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        object.__setattr__(self, "evidence", _freeze(self.evidence))

    def as_dict(self) -> dict[str, Any]:
        """Serialize the complete finding without exposing immutable internals."""

        return {
            "code": self.code,
            "message": self.message,
            "record_ids": list(self.record_ids),
            "field_paths": list(self.field_paths),
            "severity": self.severity,
            "blocks_confident": self.blocks_confident,
            "evidence": _thaw(self.evidence),
        }
