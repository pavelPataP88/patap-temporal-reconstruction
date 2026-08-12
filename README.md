# PATAP Temporal Reconstruction

PATAP is a dependency-based partial-order reconstruction and structural-memory library for Python. It reconstructs partial event order and relevant history from structural dependencies without relying on timestamps.

It is a small, deterministic Python core for situations where a state carries records of the states that made it possible. A record `X` inside `Y` means `X -> Y`; PATAP reconstructs only the order implied by those edges. It never uses timestamps, sequence numbers, JSON array position, names, or Git history.

## Why it is useful

Dependency structure preserves the provenance relevant to a decision without forcing unrelated events into an invented total order. This is useful for build provenance, workflows, audit trails, branching histories, and AI-agent memory.

The software demonstrates dependency-based partial-order reconstruction without timestamp ordering. Physical interpretation is a separate research question.

## PATAP Core

The core maps explicit dependencies to a partial order:

```text
dependencies -> partial order
```

It preserves independent events as incomparable rather than inventing a total order. Array position, timestamps, state names, and metadata never determine order.

## PATAP Memory

`PATAPMemory` is a small layer for an AI agent or another stateful program:

```text
agent state -> structural records -> relevant ancestry -> local context
```

```python
from patap import PATAPMemory

memory = PATAPMemory()
memory.record("database_schema", data={"kind": "artifact"})
memory.record("auth_requirement", data={"kind": "requirement"})
memory.record(
    "login_api",
    depends_on=["database_schema", "auth_requirement"],
    evidence=["code_diff", "tests", "decision_record"],
)

context = memory.context_for("login_api")
print(context["past"])
# ['auth_requirement', 'database_schema']
print(memory.stats("login_api"))
# {'total_states': 3, 'visible_states': 3, 'context_ratio': 1.0}
```

Memory JSON is portable and dependency-only:

```python
memory.save("memory.json")
restored = PATAPMemory.load("memory.json")
```

The structural context ratio is `visible_states / total_states`. It measures the graph share required for a present state's ancestry; it is not a claim about LLM token savings or intelligence.

## Installation

Requires Python 3.10 or later.

```bash
python -m pip install "git+https://github.com/pavelPataP88/patap-temporal-reconstruction.git"
```

For development from a checkout:

```bash
git clone https://github.com/pavelPataP88/patap-temporal-reconstruction.git
cd patap-temporal-reconstruction
python -m pip install -e .
python -m unittest discover -s tests -v
```

## Quick start

```python
from patap import PATAPMemory

memory = PATAPMemory()
memory.record("requirement")
memory.record("implementation", depends_on=["requirement"])

print(memory.context_for("implementation"))
```

The returned context includes only the present state and its structural ancestry.

## CLI

```bash
patap analyze examples/simple_history.json
patap view examples/ai_agent_memory.json login_api
patap explain examples/ai_agent_memory.json auth_tests
patap memory add memory.json database_schema --data '{"kind":"artifact"}'
patap memory add memory.json login_api --depends-on database_schema --evidence code_diff tests
patap memory context memory.json login_api
patap memory stats memory.json login_api
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

PATAP supplies the ancestry graph; it makes no claims about token savings. Run `python examples/agent_memory_demo.py` for a deliberately shuffled agent-memory example, or `python examples/synthetic_memory_benchmark.py` for a reproducible 1000-state experiment.

## Observer B

The engine may have the whole graph, but an observer at state `C` does not automatically receive its descendants. For `A -> B -> C -> D`, `observer_view("C")` reports `C`, its structural past (`A`, `B`), and `"future": "unknown_by_design"`. This models a local observer whose available context is limited to the present state and its records.

## Independent events

For `A -> B` and `A -> C`, PATAP infers `A < B` and `A < C`, but `B || C`: the latter pair is incomparable. It deliberately does not create an arbitrary `B < C` or `C < B` ordering.

## Limitations

- Input dependencies must be declared accurately; PATAP does not infer missing edges.
- Cycles are contradictory and rejected.
- This package reconstructs a partial order, not wall-clock time, causality in the physical sense, or a complete global history.
