"""Command-line interface for PATAP JSON graphs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from .engine import PATAP, ValidationError
from .memory import PATAPMemory


def load_graph(path: str) -> PATAP:
    """Load a graph from a JSON object containing a ``states`` list."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("states"), list):
        raise ValidationError("JSON must contain a 'states' array")
    engine = PATAP()
    for item in payload["states"]:
        if not isinstance(item, dict) or "id" not in item:
            raise ValidationError("each state must be an object with an 'id'")
        engine.add_state(item["id"], item.get("records"), item.get("data"))
    return engine


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="patap", description="Dependency-based temporal reconstruction")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("analyze", "view", "explain"):
        command = subparsers.add_parser(name)
        command.add_argument("file")
        if name != "analyze":
            command.add_argument("state_id")
    memory_parser = subparsers.add_parser("memory", help="manage persistent structural memory")
    memory_commands = memory_parser.add_subparsers(dest="memory_command", required=True)
    add = memory_commands.add_parser("add", help="record a state")
    add.add_argument("file")
    add.add_argument("state_id")
    add.add_argument("--depends-on", nargs="*", default=[])
    add.add_argument("--data", help="JSON object metadata")
    add.add_argument("--evidence", nargs="*", default=None)
    for name in ("context", "explain", "stats"):
        command = memory_commands.add_parser(name)
        command.add_argument("file")
        if name != "stats":
            command.add_argument("state_id")
        else:
            command.add_argument("state_id", nargs="?")
    args = parser.parse_args(argv)
    try:
        if args.command == "memory":
            file_path = Path(args.file)
            memory = PATAPMemory.load(file_path) if file_path.exists() else PATAPMemory()
            if args.memory_command == "add":
                data = json.loads(args.data) if args.data else None
                if data is not None and not isinstance(data, dict):
                    raise ValidationError("--data must decode to a JSON object")
                memory.record(args.state_id, args.depends_on, data, args.evidence)
                memory.save(file_path)
                print(f"Recorded {args.state_id} in {file_path}")
            elif args.memory_command == "context":
                print(json.dumps(memory.context_for(args.state_id), indent=2, ensure_ascii=False))
            elif args.memory_command == "explain":
                print("\n".join(memory.explain_context(args.state_id)))
            else:
                print(json.dumps(memory.stats(args.state_id), indent=2))
            return 0
        engine = load_graph(args.file)
        engine.validate()
        if args.command == "analyze":
            print("Reconstructed dependency layers:")
            for layer in engine.layers():
                print("  " + " || ".join(layer))
            pairs = sorted(engine.incomparable_pairs())
            if pairs:
                print("Incomparable pairs: " + ", ".join(f"{a} || {b}" for a, b in pairs))
        elif args.command == "view":
            print(json.dumps(engine.observer_view(args.state_id), indent=2))
        else:
            print("\n".join(engine.explain(args.state_id)))
        return 0
    except (OSError, json.JSONDecodeError, ValidationError, KeyError, ValueError) as error:
        print(f"patap: error: {error}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
