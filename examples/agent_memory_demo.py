"""Run with: python examples/agent_memory_demo.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from patap import PATAPMemory


def main() -> None:
    memory = PATAPMemory()
    # Deliberately shuffled: these calls are not a temporal signal.
    memory.record("auth_tests", ["auth_requirement"], evidence=["unit_tests"])
    memory.record("unrelated_report", ["unrelated_source"])
    memory.record("final_feature", ["login_api", "auth_tests"])
    memory.record("database_schema", ["user_requirement"], {"kind": "artifact"})
    memory.record("user_requirement", data={"kind": "requirement"})
    memory.record("login_api", ["database_schema", "auth_requirement"], evidence=["code_diff", "decision_record"])
    memory.record("unrelated_source")
    memory.record("auth_requirement", ["database_schema"], {"kind": "requirement"})

    context = memory.context_for("final_feature")
    statistics = memory.stats("final_feature")
    print(f"Total states: {statistics['total_states']}")
    print(f"Relevant ancestry states: {statistics['visible_states']}")
    print(f"Structural context ratio: {statistics['context_ratio']:.3f}")
    print("Local layers:", context["layers"])
    print("Unrelated branch visible:", "unrelated_report" in context["states"])


if __name__ == "__main__":
    main()
