import unittest

from benchmarks.v05_external.run_external_validation import extract, mutate, score


class ExternalValidationToyTests(unittest.TestCase):
    def setUp(self):
        self.rows = [
            {"id": "Qa", "traces": {"output_fingerprints": ["A"], "immediate_input_fingerprints": []}},
            {"id": "Qb", "traces": {"output_fingerprints": ["B"], "immediate_input_fingerprints": ["A"]}},
        ]

    def test_public_fingerprint_join_and_input_removal(self):
        self.assertEqual(extract(self.rows)[0], {("Qa", "Qb")})
        removed, _ = mutate(self.rows, "inputs_removed", 505001)
        self.assertEqual(extract(removed)[0], set())

    def test_shuffle_and_opaque_ids_do_not_change_metrics(self):
        shuffled, _ = mutate(self.rows, "shuffled", 505001)
        opaque, mapping = mutate(self.rows, "opaque_ids", 505001)
        truth = {("Qa", "Qb")}
        self.assertEqual(score(truth, extract(shuffled)[0])["f1"], 1.0)
        self.assertEqual(score({(mapping["Qa"], mapping["Qb"])}, extract(opaque)[0])["f1"], 1.0)

    def test_unknown_and_ambiguous_are_public_properties(self):
        missing = [{"id": "Qx", "traces": {"output_fingerprints": [], "immediate_input_fingerprints": ["missing"]}}]
        self.assertEqual(len(extract(missing)[1]), 1)
        duplicate = [
            {"id": "Qa", "traces": {"output_fingerprints": ["same"], "immediate_input_fingerprints": []}},
            {"id": "Qb", "traces": {"output_fingerprints": ["same"], "immediate_input_fingerprints": []}},
            {"id": "Qc", "traces": {"output_fingerprints": [], "immediate_input_fingerprints": ["same"]}},
        ]
        self.assertEqual(len(extract(duplicate)[2]), 1)
