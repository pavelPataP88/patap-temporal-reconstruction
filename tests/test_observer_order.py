"""Tests for the finite observer-quotient theorem checker."""

from __future__ import annotations

import unittest

from patap.observer_order import ObserverOrderError, audit_observer_order


class ObserverOrderTests(unittest.TestCase):
    def test_congruent_distinctions_induce_a_strict_quotient_order(self) -> None:
        audit = audit_observer_order(
            ["a1", "a2", "b"],
            [("a1", "b"), ("a2", "b")],
            {"a1": "source", "a2": "source", "b": "result"},
        )
        self.assertTrue(audit.is_order_congruence)
        self.assertEqual(audit.quotient_order, frozenset({("source", "result")}))

    def test_mixed_representatives_make_the_quotient_undefined(self) -> None:
        audit = audit_observer_order(
            ["a1", "a2", "b"],
            [("a1", "b")],
            {"a1": "source", "a2": "source", "b": "result"},
        )
        self.assertFalse(audit.is_order_congruence)
        self.assertFalse(audit.quotient_order)
        self.assertEqual(audit.violations[0].left_pair, ("a1", "b"))
        self.assertEqual(audit.violations[0].right_pair, ("a2", "b"))

    def test_comparable_states_cannot_be_collapsed_into_one_observation(self) -> None:
        audit = audit_observer_order(
            ["a", "b"],
            [("a", "b")],
            {"a": "same", "b": "same"},
        )
        self.assertFalse(audit.is_order_congruence)

    def test_input_order_is_not_used(self) -> None:
        distinctions = {"a1": "source", "a2": "source", "b": "result"}
        forward = audit_observer_order(["a1", "a2", "b"], [("a1", "b"), ("a2", "b")], distinctions)
        reverse = audit_observer_order(["b", "a2", "a1"], [("a2", "b"), ("a1", "b")], distinctions)
        self.assertEqual(forward, reverse)

    def test_missing_or_extra_distinction_is_rejected(self) -> None:
        with self.assertRaises(ObserverOrderError):
            audit_observer_order(["a"], [], {"a": "x", "b": "x"})


if __name__ == "__main__":
    unittest.main()
