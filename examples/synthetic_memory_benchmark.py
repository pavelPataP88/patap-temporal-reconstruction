"""Reproducible dependency-only synthetic memory experiment."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from patap import PATAPMemory


def main() -> None:
    memory = PATAPMemory()
    # Ten independent chains give a 100-state context inside a 1000-state graph.
    for index in range(1_000):
        dependency = [f"state_{index - 10}"] if index >= 10 else []
        memory.record(f"state_{index}", dependency, {"ordinal_metadata": 1_000 - index})
    current = "state_999"
    stats = memory.stats(current)
    print(f"Total states: {stats['total_states']}")
    print(f"Relevant ancestry states: {stats['visible_states']}")
    print(f"Structural context ratio: {stats['context_ratio']:.3f}")


if __name__ == "__main__":
    main()
