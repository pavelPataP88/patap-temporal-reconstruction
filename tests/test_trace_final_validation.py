"""Small pre-freeze smoke tests for the v0.4 final-validation runner."""
import unittest
from benchmarks import run_v04_final_validation as validation


class TraceFinalValidationSmokeTests(unittest.TestCase):
    def test_small_run_is_shuffle_invariant_and_trace_removed_has_no_edges(self):
        result = validation.run(22, 404001)
        self.assertEqual(result["shuffle_invariance_rate"], 1.0)
        self.assertEqual(result["conditions"]["removed"]["direct"]["correct"], 0)

    def test_public_observation_drives_ambiguity_and_unknown_expectations(self):
        result = validation.run(22, 404001)
        self.assertGreater(result["conditions"]["normal"]["ambiguous_correctness"]["expected"], 0)
        self.assertEqual(result["conditions"]["normal"]["ambiguous_correctness"]["rate"], 1.0)
        self.assertGreater(result["conditions"]["corrupt10"]["unknown_correctness"]["expected"], 0)
        self.assertEqual(result["conditions"]["corrupt10"]["unknown_correctness"]["rate"], 1.0)
        self.assertLessEqual(result["conditions"]["loss75"]["ambiguous_correctness"]["expected"], result["conditions"]["normal"]["ambiguous_correctness"]["expected"])

    def test_every_frozen_control_has_direct_and_order_metrics(self):
        result = validation.run(12, 404001)
        expected = {"normal", "removed", "loss10", "loss25", "loss50", "loss75", "corrupt5", "corrupt10", "corrupt25", "renamed", "false_trusted"}
        self.assertEqual(set(result["conditions"]), expected)
        for control in result["conditions"].values():
            self.assertIn("f1", control["direct"])
            self.assertIn("f1", control["order"])

    def test_false_trusted_control_has_real_unconsumed_artifact_event(self):
        result = validation.run(12, 404001)
        control = result["conditions"]["false_trusted"]
        self.assertEqual(control["false_trusted_events"], 12)
        self.assertGreater(control["direct"]["false_positive"], 0)

    def test_secondary_generator_runs_the_same_public_controls(self):
        result = validation.run(12, 404002, secondary=True)
        self.assertEqual(result["shuffle_invariance_rate"], 1.0)
        self.assertEqual(result["conditions"]["renamed"]["direct"], result["conditions"]["normal"]["direct"])


if __name__ == "__main__":
    unittest.main()

