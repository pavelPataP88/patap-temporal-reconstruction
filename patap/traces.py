"""Deterministic extraction of structural dependencies from public traces.

This module is deliberately narrower than a provenance system. It accepts only
public, non-temporal observations: opaque state identifiers and artifact
fingerprints that a state produced, directly consumed, or retained as an
ancestral record. It never accepts dependency edges, timestamps, positions, or
evaluator labels.

The result distinguishes justified direct edges from evidence that is missing,
ambiguous, ancestral-only, malformed, or inconsistent. In particular, an
ancestral fingerprint is not silently promoted to a direct dependency.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterable, Mapping

from .engine import PATAP


class TraceValidationError(ValueError):
    """Raised when a public trace record is not structurally well-formed."""


class EvidenceStatus(str, Enum):
    """What an extractor can honestly conclude from one public trace key."""

    DIRECT = "direct"
    ANCESTRAL = "ancestral"
    UNKNOWN = "unknown"
    AMBIGUOUS = "ambiguous"
    CONFLICT = "conflict"
    MALFORMED = "malformed"


def _fingerprint_set(values: Iterable[str], field_name: str) -> frozenset[str]:
    """Validate a fingerprint collection without assigning it temporal meaning."""
    result = frozenset(values)
    if not all(isinstance(value, str) and value for value in result):
        raise TraceValidationError(f"{field_name} must contain non-empty strings")
    return result


@dataclass(frozen=True)
class TraceObservation:
    """One public, state-local structural observation.

    ``direct_inputs`` records fingerprints that the observed operation claims
    to have used immediately. ``ancestral_records`` records fingerprints
    retained in a derived object or manifest; it supports ancestry evidence but
    never, by itself, proves a direct edge.

    ``state_id`` is treated as an opaque label. Callers must not encode
    chronology in it; the extractor never parses or orders identifiers.
    """

    state_id: str
    produced: frozenset[str] = field(default_factory=frozenset)
    direct_inputs: frozenset[str] = field(default_factory=frozenset)
    ancestral_records: frozenset[str] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        if not isinstance(self.state_id, str) or not self.state_id:
            raise TraceValidationError("state_id must be a non-empty string")
        object.__setattr__(self, "produced", _fingerprint_set(self.produced, "produced"))
        object.__setattr__(self, "direct_inputs", _fingerprint_set(self.direct_inputs, "direct_inputs"))
        object.__setattr__(self, "ancestral_records", _fingerprint_set(self.ancestral_records, "ancestral_records"))

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "TraceObservation":
        """Parse the intentionally small public JSON-compatible schema.

        No aliases such as ``depends_on`` or ``parent_state`` are accepted;
        accepting them would make the experimental boundary circular.
        """
        allowed = {"state_id", "produced", "direct_inputs", "ancestral_records"}
        unexpected = sorted(set(raw) - allowed)
        if unexpected:
            raise TraceValidationError("unsupported public fields: " + ", ".join(unexpected))
        for name in allowed - {"state_id"}:
            if name in raw and (isinstance(raw[name], (str, bytes)) or not isinstance(raw[name], Iterable)):
                raise TraceValidationError(f"{name} must be an iterable of fingerprints")
        return cls(
            state_id=raw.get("state_id"),
            produced=frozenset(raw.get("produced", ())),
            direct_inputs=frozenset(raw.get("direct_inputs", ())),
            ancestral_records=frozenset(raw.get("ancestral_records", ())),
        )


@dataclass(frozen=True)
class TraceEvidence:
    """A single auditable conclusion about one observed fingerprint."""

    consumer: str
    fingerprint: str
    channel: str
    status: EvidenceStatus
    candidates: tuple[str, ...] = ()


@dataclass(frozen=True)
class TraceExtraction:
    """Direct edges plus all non-edge evidence retained by the extractor."""

    state_ids: frozenset[str]
    direct_edges: frozenset[tuple[str, str]]
    evidence: tuple[TraceEvidence, ...]

    def evidence_with(self, status: EvidenceStatus) -> tuple[TraceEvidence, ...]:
        """Return deterministic diagnostics for one evidence status."""
        return tuple(item for item in self.evidence if item.status is status)

    @property
    def unknown(self) -> tuple[TraceEvidence, ...]:
        """Direct trace keys for which no public producer exists."""
        return self.evidence_with(EvidenceStatus.UNKNOWN)

    @property
    def ambiguous(self) -> tuple[TraceEvidence, ...]:
        """Trace keys whose public producer identity is not unique."""
        return self.evidence_with(EvidenceStatus.AMBIGUOUS)

    @property
    def conflicts(self) -> tuple[TraceEvidence, ...]:
        """Candidate edges rejected because public traces imply a cycle/self-loop."""
        return self.evidence_with(EvidenceStatus.CONFLICT)

    def to_patap(self) -> PATAP:
        """Materialize only recovered direct edges in the existing PATAP core.

        This bridge is intentionally one-way: the core receives the extractor's
        defensible result, not raw public traces and not an evaluator graph.
        """
        graph = PATAP()
        for state_id in sorted(self.state_ids):
            graph.add_state(state_id)
        for predecessor, successor in sorted(self.direct_edges):
            graph.add_dependency(predecessor, successor)
        graph.validate()
        return graph


class TraceExtractor:
    """Recover uniquely supported direct dependencies from public traces only."""

    def extract(self, observations: Iterable[TraceObservation]) -> TraceExtraction:
        """Extract a permutation-invariant, conservative direct-edge graph.

        The algorithm indexes public output fingerprints, then joins only
        ``direct_inputs`` against that index. It does not inspect observation
        order or identifier spelling. A collision creates ``AMBIGUOUS``
        evidence; an absent producer creates ``UNKNOWN`` evidence. Cyclic
        direct candidates are all removed and reported as ``CONFLICT``.
        """
        states = tuple(observations)
        state_ids = [state.state_id for state in states]
        if len(state_ids) != len(set(state_ids)):
            raise TraceValidationError("public state_id values must be unique")

        producers: dict[str, set[str]] = {}
        for state in states:
            for fingerprint in state.produced:
                producers.setdefault(fingerprint, set()).add(state.state_id)

        direct_candidates: dict[tuple[str, str], list[TraceEvidence]] = {}
        evidence: list[TraceEvidence] = []
        for state in states:
            for fingerprint in state.direct_inputs:
                candidates = tuple(sorted(producers.get(fingerprint, set())))
                if not candidates:
                    evidence.append(TraceEvidence(state.state_id, fingerprint, "direct_input", EvidenceStatus.UNKNOWN))
                elif len(candidates) != 1:
                    evidence.append(TraceEvidence(state.state_id, fingerprint, "direct_input", EvidenceStatus.AMBIGUOUS, candidates))
                elif candidates[0] == state.state_id:
                    evidence.append(TraceEvidence(state.state_id, fingerprint, "direct_input", EvidenceStatus.CONFLICT, candidates))
                else:
                    item = TraceEvidence(state.state_id, fingerprint, "direct_input", EvidenceStatus.DIRECT, candidates)
                    direct_candidates.setdefault((candidates[0], state.state_id), []).append(item)

            for fingerprint in state.ancestral_records:
                candidates = tuple(sorted(producers.get(fingerprint, set())))
                if not candidates:
                    status = EvidenceStatus.UNKNOWN
                elif len(candidates) == 1:
                    status = EvidenceStatus.ANCESTRAL
                else:
                    status = EvidenceStatus.AMBIGUOUS
                evidence.append(TraceEvidence(state.state_id, fingerprint, "ancestral_record", status, candidates))

        cyclic_edges = self._cyclic_edges(set(direct_candidates))
        for edge in sorted(cyclic_edges):
            for item in direct_candidates[edge]:
                evidence.append(TraceEvidence(item.consumer, item.fingerprint, item.channel, EvidenceStatus.CONFLICT, item.candidates))

        direct_edges = frozenset(set(direct_candidates) - cyclic_edges)
        evidence.sort(key=lambda item: (item.consumer, item.fingerprint, item.channel, item.status.value, item.candidates))
        return TraceExtraction(frozenset(state_ids), direct_edges, tuple(evidence))

    @staticmethod
    def _cyclic_edges(edges: set[tuple[str, str]]) -> set[tuple[str, str]]:
        """Return every candidate edge in a directed cycle, without tie-breaking."""
        adjacency: dict[str, set[str]] = {}
        for source, target in edges:
            adjacency.setdefault(source, set()).add(target)
            adjacency.setdefault(target, set())

        index = 0
        indices: dict[str, int] = {}
        lowlinks: dict[str, int] = {}
        stack: list[str] = []
        on_stack: set[str] = set()
        components: list[set[str]] = []

        def visit(node: str) -> None:
            nonlocal index
            indices[node] = index
            lowlinks[node] = index
            index += 1
            stack.append(node)
            on_stack.add(node)
            for successor in sorted(adjacency[node]):
                if successor not in indices:
                    visit(successor)
                    lowlinks[node] = min(lowlinks[node], lowlinks[successor])
                elif successor in on_stack:
                    lowlinks[node] = min(lowlinks[node], indices[successor])
            if lowlinks[node] == indices[node]:
                component: set[str] = set()
                while True:
                    member = stack.pop()
                    on_stack.remove(member)
                    component.add(member)
                    if member == node:
                        break
                components.append(component)

        for node in sorted(adjacency):
            if node not in indices:
                visit(node)
        cyclic_components = [component for component in components if len(component) > 1]
        return {
            edge
            for edge in edges
            if edge[0] == edge[1] or any(edge[0] in component and edge[1] in component for component in cyclic_components)
        }
