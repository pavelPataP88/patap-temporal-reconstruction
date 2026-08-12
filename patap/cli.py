"""Command-line interface for PATAP JSON graphs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from .engine import PATAP, ValidationError


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
    args = parser.parse_args(argv)
    try:
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
