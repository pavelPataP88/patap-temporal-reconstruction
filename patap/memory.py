"""A small structural-memory layer built on the PATAP dependency engine."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from .engine import PATAP, UnknownStateError


class PATAPMemory:
    """Record agent states and retrieve only a present state's structural context.

    Metadata and evidence are provenance attached to a state. They never affect
    dependency reconstruction, which is delegated entirely to :class:`PATAP`.
    """

    def __init__(self, engine: PATAP | None = None) -> None:
        self._engine = engine or PATAP()

    def record(
        self,
        state_id: str,
        depends_on: Iterable[str] | None = None,
        data: dict[str, Any] | None = None,
        evidence: Iterable[str] | None = None,
    ) -> "PATAPMemory":
        """Store one state and its explicit structural dependencies.

        Dependencies may name states recorded later; :meth:`validate` resolves
        that contract before a context can be analysed.
        """
        self._engine.add_state(state_id, records=depends_on, data=data, evidence=evidence)
        return self

    def validate(self) -> None:
        """Validate all references and reject cyclic dependency structures."""
        self._engine.validate()

    def context_for(self, state_id: str) -> dict[str, Any]:
        """Return the present state and its ancestry, never global descendants."""
        self.validate()
        if state_id not in self._engine._states:
            raise UnknownStateError(f"unknown state: {state_id}")
        past = self._engine.past_of(state_id)
        visible = past | {state_id}
        layers = [
            [node for node in layer if node in visible]
            for layer in self._engine.layers()
            if any(node in visible for node in layer)
        ]
        states = {
            node: {
                "dependencies": sorted(self._engine._states[node].records),
                "data": self._engine._states[node].data,
                "evidence": self._engine._states[node].evidence,
            }
            for node in sorted(visible)
        }
        return {
            "present": state_id,
            "past": sorted(past),
            "layers": layers,
            "states": states,
            "future": "unknown_by_design",
        }

    def explain_context(self, state_id: str) -> list[str]:
        """Explain the current state using its transitive structural ancestry."""
        return self._engine.explain(state_id)

    def stats(self, state_id: str | None = None) -> dict[str, int | float]:
        """Report graph size and, optionally, the visible structural-context ratio."""
        self.validate()
        total = len(self._engine._states)
        if state_id is None:
            return {"total_states": total}
        visible = len(self._engine.past_of(state_id)) + 1
        return {
            "total_states": total,
            "visible_states": visible,
            "context_ratio": visible / total if total else 0.0,
        }

    def save(self, path: str | Path) -> None:
        """Persist states, dependencies, data, and evidence as portable JSON."""
        payload = {
            "states": [
                {
                    "id": state.id,
                    "records": sorted(state.records),
                    "data": state.data,
                    "evidence": state.evidence,
                }
                for state in sorted(self._engine._states.values(), key=lambda item: item.id)
            ]
        }
        Path(path).write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "PATAPMemory":
        """Load memory JSON without treating its array order as temporal order."""
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(payload, dict) or not isinstance(payload.get("states"), list):
            raise ValueError("memory JSON must contain a 'states' array")
        memory = cls()
        for item in payload["states"]:
            if not isinstance(item, dict) or not isinstance(item.get("id"), str):
                raise ValueError("each memory state must have a string 'id'")
            memory.record(item["id"], item.get("records"), item.get("data"), item.get("evidence"))
        return memory
