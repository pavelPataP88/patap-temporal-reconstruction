"""Dependency-only partial-order reconstruction."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterable

from .models import State


class ValidationError(ValueError):
    """Raised when a graph refers to states that do not exist."""


class UnknownStateError(KeyError):
    """Raised when an operation names a state absent from the graph."""


class CycleError(ValidationError):
    """Raised when structural dependencies contain a directed cycle."""


class PATAP:
    """Reconstruct a partial order exclusively from declared dependencies.

    A record in state ``Y`` of state ``X`` declares ``X -> Y``.  Values in
    ``data`` are deliberately opaque and never participate in reconstruction.
    """

    def __init__(self) -> None:
        self._states: dict[str, State] = {}

    def add_state(
        self, state_id: str, records: Iterable[str] | None = None,
        data: dict[str, Any] | None = None,
    ) -> "PATAP":
        """Add or update a state. Unknown records remain forward references."""
        if not isinstance(state_id, str) or not state_id:
            raise ValueError("state_id must be a non-empty string")
        record_set = set(records or ())
        if not all(isinstance(record, str) and record for record in record_set):
            raise ValueError("records must contain non-empty string identifiers")
        self._states[state_id] = State(state_id, record_set, data)
        return self

    def add_dependency(self, predecessor: str, successor: str) -> "PATAP":
        """Declare a structural dependency ``predecessor -> successor``."""
        if successor not in self._states:
            self.add_state(successor)
        self._states[successor].records.add(predecessor)
        return self

    def _require_state(self, state_id: str) -> None:
        if state_id not in self._states:
            raise UnknownStateError(f"unknown state: {state_id}")

    def _parents(self) -> dict[str, set[str]]:
        return {state_id: set(state.records) for state_id, state in self._states.items()}

    def _children(self) -> dict[str, set[str]]:
        children: dict[str, set[str]] = defaultdict(set)
        for state_id, state in self._states.items():
            for parent in state.records:
                children[parent].add(state_id)
        return children

    def validate(self) -> None:
        """Ensure all references resolve and the dependency graph is acyclic."""
        missing = sorted({record for state in self._states.values() for record in state.records if record not in self._states})
        if missing:
            raise ValidationError("unknown state references: " + ", ".join(missing))
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(node: str, trail: list[str]) -> None:
            if node in visiting:
                start = trail.index(node)
                raise CycleError("dependency cycle: " + " -> ".join(trail[start:] + [node]))
            if node in visited:
                return
            visiting.add(node)
            for parent in sorted(self._parents()[node]):
                visit(parent, trail + [node])
            visiting.remove(node)
            visited.add(node)

        for state_id in sorted(self._states):
            visit(state_id, [])

    def direct_past_of(self, state_id: str) -> set[str]:
        """Return immediately recorded predecessors of a state."""
        self.validate()
        self._require_state(state_id)
        return set(self._states[state_id].records)

    def past_of(self, state_id: str) -> set[str]:
        """Return the transitive structural ancestry of a state."""
        self.validate()
        self._require_state(state_id)
        past: set[str] = set()
        stack = list(self._states[state_id].records)
        while stack:
            node = stack.pop()
            if node not in past:
                past.add(node)
                stack.extend(self._states[node].records)
        return past

    def reconstruct_order(self) -> list[list[str]]:
        """Return dependency layers, preserving concurrency within each layer.

        The outer layer order follows the partial order. Items in one layer are
        sorted only for deterministic display; that sort does not assert order.
        """
        self.validate()
        parents = self._parents()
        remaining = set(self._states)
        layers: list[list[str]] = []
        while remaining:
            ready = sorted(node for node in remaining if not (parents[node] & remaining))
            if not ready:  # Defensive; validate() already gives a useful cycle error.
                raise CycleError("dependency cycle")
            layers.append(ready)
            remaining.difference_update(ready)
        return layers

    def layers(self) -> list[list[str]]:
        """Alias for :meth:`reconstruct_order`."""
        return self.reconstruct_order()

    def incomparable_pairs(self) -> set[tuple[str, str]]:
        """Return unordered pairs whose members have no dependency path either way."""
        self.validate()
        identifiers = sorted(self._states)
        ancestry = {node: self.past_of(node) for node in identifiers}
        return {
            (left, right)
            for index, left in enumerate(identifiers)
            for right in identifiers[index + 1 :]
            if left not in ancestry[right] and right not in ancestry[left]
        }

    def observer_view(self, state_id: str) -> dict[str, Any]:
        """Return only what a local observer at ``state_id`` can structurally know."""
        self.validate()
        self._require_state(state_id)
        visible = self.past_of(state_id) | {state_id}
        return {
            "present": state_id,
            "past": sorted(visible - {state_id}),
            "layers": [[node for node in layer if node in visible] for layer in self.layers() if any(node in visible for node in layer)],
            "future": "unknown_by_design",
        }

    def explain(self, state_id: str) -> list[str]:
        """Return a deterministic ancestry explanation from present to roots."""
        self.validate()
        self._require_state(state_id)
        lines: list[str] = []

        def explain_node(node: str, depth: int) -> None:
            lines.append(("<- " if depth else "") + node)
            for parent in sorted(self._states[node].records):
                explain_node(parent, depth + 1)

        explain_node(state_id, 0)
        return lines
