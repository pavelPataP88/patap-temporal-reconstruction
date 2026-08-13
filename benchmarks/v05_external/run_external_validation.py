"""Linux strace recorder for frozen PATAP v0.5 external validation.

The public adapter receives only opaque IDs, output hashes and read hashes.
The privileged evaluator separately uses syscall ordering to identify the last
writer of the concrete path read by a later process.  No public record carries
paths, timestamps, syscall positions, build graph data, or evaluator edges.
"""
from __future__ import annotations
import argparse, hashlib, json, os, random, re, shutil, subprocess, sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG = Path(__file__).with_name("projects.json")
OUT = ROOT / "benchmark_results" / "v0.5-external"
OPEN = re.compile(r"^(?:\[pid +(\d+)\]|(\d+)) +(?:open|openat)\([^\"]*\"([^\"]+)\".*?\b(O_[A-Z|]+)")

def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def opaque(project: str, pid: str, seed: int) -> str:
    return "Q" + hashlib.sha256(f"{project}:{pid}:{seed}".encode()).hexdigest()[:24]

def parse_log(log: Path, project_root: Path) -> list[tuple[int, str, str, Path]]:
    """Return (log_position, pid, mode, path), retaining only project files."""
    events: list[tuple[int, str, str, Path]] = []
    for position, line in enumerate(log.read_text(errors="replace").splitlines()):
        match = OPEN.match(line)
        if not match:
            continue
        pid, alt_pid, raw, flags = match.groups()
        candidate = Path(raw) if raw.startswith("/") else project_root / raw
        try:
            path = candidate.resolve()
            path.relative_to(project_root.resolve())
        except ValueError:
            continue
        if ".git" in path.parts or not path.is_file():
            continue
        mode = "write" if any(flag in flags for flag in ("O_WRONLY", "O_RDWR", "O_CREAT", "O_TRUNC")) else "read"
        events.append((position, pid or alt_pid, mode, path))
    return events

def capture(project: dict[str, str], seed: int) -> tuple[list[dict], list[list[str]], dict]:
    """Run a real third-party build; public and evaluator outputs diverge here."""
    workspace = OUT / "work" / project["name"]
    shutil.rmtree(workspace, ignore_errors=True)
    workspace.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "clone", project["url"], str(workspace)], check=True, stdout=subprocess.DEVNULL)
    subprocess.run(["git", "checkout", "--detach", project["commit"]], cwd=workspace, check=True, stdout=subprocess.DEVNULL)
    log = workspace.parent / f"{project['name']}.strace"
    command = ["strace", "-f", "-o", str(log), "-e", "trace=open,openat", "bash", "-lc", project["command"]]
    subprocess.run(command, cwd=workspace, check=True)
    events = parse_log(log, workspace)
    reads: dict[str, list[tuple[int, Path]]] = defaultdict(list)
    writes: dict[str, list[tuple[int, Path]]] = defaultdict(list)
    for position, pid, mode, path in events:
        (writes if mode == "write" else reads)[pid].append((position, path))
    ids = {pid: opaque(project["name"], pid, seed) for pid in set(reads) | set(writes)}
    # Public T(W): fingerprints are byproducts of file access; no path or order survives.
    public = []
    for pid in sorted(ids):
        outputs = sorted({digest(path) for _, path in writes[pid] if path.exists()})
        inputs = sorted({digest(path) for _, path in reads[pid] if path.exists()})
        if outputs or inputs:
            public.append({"id": ids[pid], "traces": {"output_fingerprints": outputs, "immediate_input_fingerprints": inputs}})
    # Privileged evaluator: last actual writer of the exact concrete path before a read.
    writer_history: dict[Path, list[tuple[int, str]]] = defaultdict(list)
    truth: set[tuple[str, str]] = set()
    for position, pid, mode, path in sorted(events):
        if mode == "write":
            writer_history[path].append((position, pid))
        elif mode == "read":
            prior = [entry for entry in writer_history[path] if entry[0] < position]
            if prior and prior[-1][1] != pid:
                truth.add((ids[prior[-1][1]], ids[pid]))
    metadata = {"project": project, "units": len(public), "syscall_file_events": len(events)}
    return public, sorted(map(list, truth)), metadata

def extract(rows: list[dict]) -> tuple[set[tuple[str, str]], set[tuple[str, str]], set[tuple[str, str]]]:
    """Exact fixed v0.4 rule, generalized only to multiple output fingerprints."""
    producers: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        for value in row["traces"].get("output_fingerprints", []):
            producers[value].add(row["id"])
    edges: set[tuple[str, str]] = set(); unknown: set[tuple[str, str]] = set(); ambiguous: set[tuple[str, str]] = set()
    for row in rows:
        for value in row["traces"].get("immediate_input_fingerprints", []):
            owners = producers.get(value, set())
            if len(owners) == 1:
                owner = next(iter(owners))
                if owner != row["id"]:
                    edges.add((owner, row["id"]))
            elif not owners:
                unknown.add((row["id"], value))
            else:
                ambiguous.add((row["id"], value))
    return edges, unknown, ambiguous

def closure(edges: set[tuple[str, str]]) -> set[tuple[str, str]]:
    reach = set(edges); changed = True
    while changed:
        expanded = reach | {(a, d) for a, b in reach for c, d in reach if b == c}
        changed = len(expanded) != len(reach); reach = expanded
    return reach

def score(truth: set[tuple[str, str]], got: set[tuple[str, str]]) -> dict[str, float | int]:
    correct = len(truth & got); fp = len(got - truth); fn = len(truth - got)
    precision = correct / (correct + fp) if correct + fp else 1.0
    recall = correct / (correct + fn) if correct + fn else 1.0
    return {"true": len(truth), "correct": correct, "false_positive": fp, "false_negative": fn, "precision": precision, "recall": recall, "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0}

def mutate(rows: list[dict], control: str, seed: int) -> tuple[list[dict], dict[str, str]]:
    result = json.loads(json.dumps(rows)); rng = random.Random(seed + int(hashlib.sha256(control.encode()).hexdigest()[:8], 16))
    mapping = {row["id"]: row["id"] for row in result}
    if control == "inputs_removed":
        for row in result: row["traces"]["immediate_input_fingerprints"] = []
    elif control in {"loss25", "loss50"}:
        chance = 0.25 if control == "loss25" else 0.50
        for row in result:
            values = row["traces"].get("immediate_input_fingerprints", [])
            row["traces"]["immediate_input_fingerprints"] = [x for x in values if rng.random() >= chance]
    elif control == "opaque_ids":
        mapping = {row["id"]: opaque("replacement", row["id"], seed) for row in result}
        for row in result: row["id"] = mapping[row["id"]]
    elif control == "false_trusted":
        fingerprints = sorted({x for row in result for x in row["traces"].get("output_fingerprints", [])})
        target = next((row for row in result if row["traces"].get("immediate_input_fingerprints")), None)
        if target:
            used = set(target["traces"]["immediate_input_fingerprints"])
            candidate = next((x for x in fingerprints if x not in used), None)
            if candidate: target["traces"]["immediate_input_fingerprints"].append(candidate)
    rng.shuffle(result)
    return result, mapping

def run_project(project: dict[str, str], seed: int) -> dict:
    public, truth_rows, metadata = capture(project, seed)
    truth = {tuple(edge) for edge in truth_rows}
    results = {}
    for control in ("normal", "inputs_removed", "shuffled", "opaque_ids", "loss25", "loss50", "false_trusted"):
        rows, mapping = mutate(public, control, seed)
        control_truth = {(mapping[a], mapping[b]) for a, b in truth}
        edges, unknown, ambiguous = extract(rows)
        results[control] = {"direct": score(control_truth, edges), "order": score(closure(control_truth), closure(edges)), "unknown_count": len(unknown), "ambiguous_count": len(ambiguous)}
    return {"metadata": metadata, "public_observations": public, "evaluator_truth": truth_rows, "results": results}

def main() -> None:
    config = json.loads(CONFIG.read_text()); OUT.mkdir(parents=True, exist_ok=True)
    all_projects = [run_project(project, config["seed"]) for project in config["projects"]]
    (OUT / "raw.json").write_text(json.dumps(all_projects, indent=2) + "\n")
    aggregate_truth = aggregate_correct = aggregate_fp = aggregate_fn = 0
    for project in all_projects:
        direct = project["results"]["normal"]["direct"]; aggregate_truth += direct["true"]; aggregate_correct += direct["correct"]; aggregate_fp += direct["false_positive"]; aggregate_fn += direct["false_negative"]
    precision = aggregate_correct / (aggregate_correct + aggregate_fp) if aggregate_correct + aggregate_fp else 1.0
    recall = aggregate_correct / (aggregate_correct + aggregate_fn) if aggregate_correct + aggregate_fn else 1.0
    aggregate = {"true": aggregate_truth, "correct": aggregate_correct, "false_positive": aggregate_fp, "false_negative": aggregate_fn, "precision": precision, "recall": recall, "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0}
    (OUT / "results.json").write_text(json.dumps({"config": config, "projects": all_projects, "aggregate_direct": aggregate}, indent=2) + "\n")

if __name__ == "__main__":
    main()
