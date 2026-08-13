"""Executable checks for PATAP's conservative public-trace boundary."""

from __future__ import annotations

import unittest

from patap import PATAP
from patap.traces import EvidenceStatus, TraceExtractor, TraceObservation, TraceValidationError


class TraceIdentifiabilityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.extractor = TraceExtractor()

    def test_unique_direct_trace_reconstructs_a_dependency(self) -> None:
        result = self.extractor.extract(
            [
                TraceObservation("qX", produced=frozenset({"sha256:source"})),
                TraceObservation("m9", direct_inputs=frozenset({"sha256:source"})),
            ]
        )
        self.assertEqual(result.direct_edges, frozenset({("qX", "m9")}))
        self.assertEqual(result.to_patap().past_of("m9"), {"qX"})

    def test_ancestral_trace_is_not_promoted_to_a_direct_edge(self) -> None:
        result = self.extractor.extract(
            [
                TraceObservation("a", produced=frozenset({"root"})),
                TraceObservation("b", ancestral_records=frozenset({"root"})),
            ]
        )
        self.assertFalse(result.direct_edges)
        self.assertEqual(result.evidence_with(EvidenceStatus.ANCESTRAL)[0].candidates, ("a",))

    def test_duplicate_content_is_ambiguous_not_an_arbitrary_edge(self) -> None:
        result = self.extractor.extract(
            [
                TraceObservation("opaque-9", produced=frozenset({"same"})),
                TraceObservation("opaque-4", produced=frozenset({"same"})),
                TraceObservation("opaque-f", direct_inputs=frozenset({"same"})),
            ]
        )
        self.assertFalse(result.direct_edges)
        self.assertEqual(result.ambiguous[0].candidates, ("opaque-4", "opaque-9"))

    def test_missing_public_producer_is_unknown(self) -> None:
        result = self.extractor.extract([TraceObservation("x", direct_inputs=frozenset({"missing"}))])
        self.assertEqual(result.unknown[0].fingerprint, "missing")
        self.assertFalse(result.direct_edges)

    def test_permuting_observations_does_not_change_result(self) -> None:
        observations = [
            TraceObservation("id-k", produced=frozenset({"a"})),
            TraceObservation("id-p", produced=frozenset({"b"})),
            TraceObservation("id-z", direct_inputs=frozenset({"a", "b"})),
        ]
        forward = self.extractor.extract(observations)
        backward = self.extractor.extract(list(reversed(observations)))
        self.assertEqual(forward, backward)

    def test_conflicting_cycle_is_reported_and_not_materialized(self) -> None:
        result = self.extractor.extract(
            [
                TraceObservation("u", produced=frozenset({"from-u"}), direct_inputs=frozenset({"from-v"})),
                TraceObservation("v", produced=frozenset({"from-v"}), direct_inputs=frozenset({"from-u"})),
            ]
        )
        self.assertFalse(result.direct_edges)
        self.assertEqual(len(result.conflicts), 2)
        self.assertIsInstance(result.to_patap(), PATAP)

    def test_direct_dependency_aliases_are_rejected_at_public_boundary(self) -> None:
        with self.assertRaises(TraceValidationError):
            TraceObservation.from_mapping({"state_id": "x", "depends_on": ["y"]})


if __name__ == "__main__":
    unittest.main()
