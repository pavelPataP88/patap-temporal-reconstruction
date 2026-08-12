"""Data models used by PATAP."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class State:
    """A state and the identifiers it structurally records as predecessors."""

    id: str
    records: set[str] = field(default_factory=set)
    data: dict[str, Any] | None = None
