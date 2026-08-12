import itertools
import tempfile
import unittest
from pathlib import Path

from patap import CycleError, PATAP, PATAPMemory, ValidationError


class PATAPTests(unittest.TestCase):
    def test_shuffled_input_reconstructs_dependencies(self):
        graph = PATAP()
        for state_id, records in [("C", ["B"]), ("A", []), ("B", ["A"])]:
            graph.add_state(state_id, records)
        self.assertEqual(graph.reconstruct_order(), [["A"], ["B"], ["C"]])

    def test_independent_branches_are_incomparable(self):
        graph = PATAP().add_state("A").add_state("B", ["A"]).add_state("C", ["A"])
        self.assertIn(("B", "C"), graph.incomparable_pairs())
        self.assertEqual(graph.layers(), [["A"], ["B", "C"]])

    def test_cycle_fails_validation(self):
        graph = PATAP().add_state("A", ["C"]).add_state("B", ["A"]).add_state("C", ["B"])
        with self.assertRaises(CycleError):
            graph.validate()

    def test_forward_references_resolve_later(self):
        graph = PATAP().add_state("tests", ["auth"])
        with self.assertRaises(ValidationError):
            graph.validate()
        graph.add_state("auth")
        graph.validate()
        self.assertEqual(graph.direct_past_of("tests"), {"auth"})

    def test_observer_isolation(self):
        graph = PATAP().add_state("A").add_state("B", ["A"]).add_state("C", ["B"]).add_state("D", ["C"])
        view = graph.observer_view("C")
        self.assertEqual(view["present"], "C")
        self.assertEqual(view["past"], ["A", "B"])
        self.assertEqual(view["future"], "unknown_by_design")
        self.assertNotIn("D", [node for layer in view["layers"] for node in layer])

    def test_input_order_independence(self):
        states = [("A", []), ("B", ["A"]), ("C", ["A"]), ("D", ["B", "C"])]
        expected = [["A"], ["B", "C"], ["D"]]
        for ordering in itertools.permutations(states):
            graph = PATAP()
            for state_id, records in ordering:
                graph.add_state(state_id, records)
            self.assertEqual(graph.reconstruct_order(), expected)

    def test_data_timestamps_are_not_used(self):
        graph = PATAP()
        graph.add_state("C", ["B"], {"created_at": "1900-01-01T00:00:00Z"})
        graph.add_state("A", [], {"created_at": "9999-12-31T23:59:59Z"})
        graph.add_state("B", ["A"], {"modified_at": "1800-01-01T00:00:00Z"})
        self.assertEqual(graph.reconstruct_order(), [["A"], ["B"], ["C"]])

    def test_explain_shows_ancestry(self):
        graph = PATAP().add_state("schema").add_state("requirement").add_state("login", ["schema", "requirement"])
        self.assertEqual(graph.explain("login"), ["login", "<- requirement", "<- schema"])

    def test_memory_records_context_and_excludes_descendants(self):
        memory = PATAPMemory()
        memory.record("D", ["C"])
        memory.record("C", ["B"], evidence=["test"])
        memory.record("A", data={"kind": "root"})
        memory.record("B", ["A"])
        context = memory.context_for("C")
        self.assertEqual(context["past"], ["A", "B"])
        self.assertEqual(context["future"], "unknown_by_design")
        self.assertNotIn("D", context["states"])
        self.assertEqual(context["states"]["C"]["evidence"], ["test"])

    def test_memory_excludes_independent_branch(self):
        memory = PATAPMemory()
        for state, dependencies in [("C", ["B"]), ("Y", ["X"]), ("A", []), ("B", ["A"]), ("X", [])]:
            memory.record(state, dependencies)
        self.assertEqual(set(memory.context_for("C")["states"]), {"A", "B", "C"})

    def test_memory_forward_references_and_cycles(self):
        memory = PATAPMemory().record("tests", ["login"]).record("login", ["schema"]).record("schema")
        memory.validate()
        self.assertEqual(memory.context_for("tests")["layers"], [["schema"], ["login"], ["tests"]])
        with self.assertRaises(CycleError):
            PATAPMemory().record("A", ["B"]).record("B", ["A"]).validate()

    def test_memory_save_load_preserves_data_evidence_and_order(self):
        memory = PATAPMemory().record("C", ["B"], {"created_at": "1900"}, ["proof"]).record("A").record("B", ["A"], {"created_at": "9999"})
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "memory.json"
            memory.save(path)
            restored = PATAPMemory.load(path)
        self.assertEqual(restored.context_for("C"), memory.context_for("C"))
        self.assertEqual(restored._engine.layers(), [["A"], ["B"], ["C"]])

    def test_memory_input_order_metadata_and_context_ratio(self):
        memory = PATAPMemory()
        for state, dependencies in [("D", ["C"]), ("X", []), ("B", ["A"]), ("C", ["B"]), ("A", [])]:
            memory.record(state, dependencies, {"timestamp": state})
        self.assertEqual(memory.context_for("D")["layers"], [["A"], ["B"], ["C"], ["D"]])
        self.assertEqual(memory.stats("D"), {"total_states": 5, "visible_states": 4, "context_ratio": 0.8})


if __name__ == "__main__":
    unittest.main()
