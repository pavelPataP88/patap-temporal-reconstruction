"""Finite audits for observer-relative quotients of a latent partial order.

This is an evaluator-side mathematical tool. It checks whether a proposed
distinction map can induce a well-defined strict partial order on what an
observer can distinguish. It is not an extractor and must never be given to
an internal observer as a global graph oracle.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable, Mapping

from .engine import PATAP


class ObserverOrderError(ValueError):
    """Raised when a finite latent order or distinction map is malformed."""


@dataclass(frozen=True)
class CongruenceViolation:
    """A witness that one observational class cannot carry a single order role."""

    left_class: str
    right_class: str
    left_pair: tuple[str, str]
    right_pair: tuple[str, str]


@dataclass(frozen=True)
class ObserverOrderAudit:
    """Result of checking whether a distinction quotient is order-compatible."""

    classes: Mapping[str, tuple[str, ...]]
    quotient_order: frozenset[tuple[str, str]]
    violations: tuple[CongruenceViolation, ...]

    @property
    def is_order_congruence(self) -> bool:
        """Whether the observer's equivalence classes admit a strict quotient order."""
        return not self.violations


def audit_observer_order(
    state_ids: Iterable[str],
    latent_edges: Iterable[tuple[str, str]],
    distinctions: Mapping[str, str],
) -> ObserverOrderAudit:
    """Audit the quotient induced by an observer distinction map.

    Let ``x ~ y`` mean ``D(x) == D(y)``. The quotient relation is well-defined
    exactly when the truth of ``x < y`` is constant for every pair of
    equivalence classes. When that condition holds, this function returns the
    induced strict partial order on observation classes. Otherwise it returns
    explicit witnesses instead of selecting a representative arbitrarily.

    ``latent_edges`` are evaluator-only input used to verify the mathematical
    statement. This function is deliberately separate from the public-trace
    extractor, which never receives them.
    """
    identifiers = tuple(state_ids)
    if len(identifiers) != len(set(identifiers)) or not all(isinstance(item, str) and item for item in identifiers):
        raise ObserverOrderError("state_ids must be unique non-empty strings")
    if set(distinctions) != set(identifiers):
        raise ObserverOrderError("distinctions must define exactly one observation for every state")
    if not all(isinstance(value, str) and value for value in distinctions.values()):
        raise ObserverOrderError("distinction values must be non-empty strings")

    graph = PATAP()
    for state_id in identifiers:
        graph.add_state(state_id)
    for predecessor, successor in latent_edges:
        if predecessor not in graph.state_ids() or successor not in graph.state_ids():
            raise ObserverOrderError("latent edge refers to an unknown state")
        graph.add_dependency(predecessor, successor)
    graph.validate()

    classes_by_name: dict[str, list[str]] = defaultdict(list)
    for state_id in identifiers:
        classes_by_name[distinctions[state_id]].append(state_id)
    classes = {name: tuple(sorted(members)) for name, members in sorted(classes_by_name.items())}
    past = {state_id: graph.past_of(state_id) for state_id in identifiers}

    def precedes(left: str, right: str) -> bool:
        return left in past[right]

    violations: list[CongruenceViolation] = []
    quotient_order: set[tuple[str, str]] = set()
    names = tuple(classes)
    for left_name in names:
        for right_name in names:
            pairs = [(left, right) for left in classes[left_name] for right in classes[right_name]]
            truth_values = [precedes(left, right) for left, right in pairs]
            if any(truth_values) and not all(truth_values):
                first_true = next(pair for pair in pairs if precedes(*pair))
                first_false = next(pair for pair in pairs if not precedes(*pair))
                violations.append(CongruenceViolation(left_name, right_name, first_true, first_false))
            elif left_name != right_name and all(truth_values):
                quotient_order.add((left_name, right_name))
            elif left_name == right_name and any(truth_values):
                pair = next(pair for pair in pairs if precedes(*pair))
                self_pair = (pair[0], pair[0])
                violations.append(CongruenceViolation(left_name, right_name, pair, self_pair))

    return ObserverOrderAudit(
        classes=classes,
        quotient_order=frozenset(quotient_order) if not violations else frozenset(),
        violations=tuple(violations),
    )
