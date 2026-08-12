# PATAP Temporal Reconstruction

PATAP is a dependency-based temporal reconstruction engine that reconstructs partial event order and relevant history from structural dependencies without relying on timestamps.

It is a small, deterministic Python core for situations where a state carries records of the states that made it possible. A record `X` inside `Y` means `X -> Y`; PATAP reconstructs only the order implied by those edges. It never uses timestamps, sequence numbers, JSON array position, names, or Git history.

## Why it is useful

Dependency structure preserves the provenance relevant to a decision without forcing unrelated events into an invented total order. This is useful for build provenance, workflows, audit trails, branching histories, and AI-agent memory.

The software demonstrates dependency-based partial-order reconstruction without timestamp ordering. Physical interpretation is a separate research question.

## Installation

Requires Python 3.10 or later.

```bash
pip install patap-temporal-reconstruction
```

For development from a checkout:

```bash
pip install -e .
python -m unittest discover -s tests -v
```

## Quick start

```python
from patap import PATAP

graph = PATAP()
graph.add_state("tests", records=["auth"])
graph.add_state("database")
graph.add_state("auth", records=["database"])

print(graph.reconstruct_order())
# [['database'], ['auth'], ['tests']]
```

The list above displays dependency layers. It does not make states in the same layer sequential.

## CLI

```bash
patap analyze examples/simple_history.json
patap view examples/ai_agent_memory.json login_api
patap explain examples/ai_agent_memory.json auth_tests
```

Invalid references and cycles result in a readable error and a non-zero exit code.

## AI-agent structural memory

Instead of retaining only a long stream of messages:

```text
message1
message2
...
message50000
```

an agent can retain a state with explicit provenance:

```text
STATE:
login_api

DEPENDS_ON:
database_schema
auth_requirement

EVIDENCE:
code_diff
tests
decision_record
```

It can then request ancestry for the current decision:

```text
current state
    -> relevant structural ancestry
    -> compact reconstructed context
    -> LLM
```

PATAP supplies the ancestry graph; it makes no claims about token savings.

## Observer B

The engine may have the whole graph, but an observer at state `C` does not automatically receive its descendants. For `A -> B -> C -> D`, `observer_view("C")` reports `C`, its structural past (`A`, `B`), and `"future": "unknown_by_design"`. This models a local observer whose available context is limited to the present state and its records.

## Independent events

For `A -> B` and `A -> C`, PATAP infers `A < B` and `A < C`, but `B || C`: the latter pair is incomparable. It deliberately does not create an arbitrary `B < C` or `C < B` ordering.

## Limitations

- Input dependencies must be declared accurately; PATAP does not infer missing edges.
- Cycles are contradictory and rejected.
- This package reconstructs a partial order, not wall-clock time, causality in the physical sense, or a complete global history.
