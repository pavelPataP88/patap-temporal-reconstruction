"""Small pre-freeze smoke tests for the v0.4 final-validation runner."""
import unittest
from benchmarks import run_v04_final_validation as validation


class TraceFinalValidationSmokeTests(unittest.TestCase):
    def test_small_run_is_shuffle_invariant_and_trace_removed_has_no_edges(self):
        result = validation.run(12, 404001)
        self.assertEqual(result["shuffle_invariance_rate"], 1.0)
        self.assertEqual(result["conditions"]["removed"]["direct"]["correct"], 0)

    def test_ambiguity_and_corruption_are_scored_as_labels(self):
        result = validation.run(15, 404001)
        self.assertGreater(result["conditions"]["normal"]["ambiguous_correctness"]["expected"], 0)
        self.assertEqual(result["conditions"]["normal"]["ambiguous_correctness"]["rate"], 1.0)
        self.assertGreater(result["conditions"]["corrupt10"]["unknown_correctness"]["expected"], 0)
        self.assertEqual(result["conditions"]["corrupt10"]["unknown_correctness"]["rate"], 1.0)

    def test_false_trusted_control_has_real_unconsumed_artifact_event(self):
        result = validation.run(12, 404001)
        control = result["conditions"]["false_trusted"]
        self.assertEqual(control["false_trusted_events"], 12)
        self.assertGreater(control["direct"]["false_positive"], 0)


if __name__ == "__main__":
    unittest.main()

