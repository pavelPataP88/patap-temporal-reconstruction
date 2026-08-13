# PATAP Trace-Identifiability Core

## Purpose

This is an executable research boundary for the central PATAP question:
which observer-accessible, non-temporal structural traces justify recovering a
dependency relation, and which do not? It is not a claim about physical time,
physical causality, automatic semantic understanding, or the historical
priority of partial orders.

The boundary is deliberately stricter than the earlier software API. The
existing core accepts declared records and reconstructs their partial order.
This module instead accepts public artifact traces and produces only a
conservative *candidate* direct-edge graph. The recovered graph can then be
passed into the existing core to calculate the partial order.

## Public observation schema

Each input is a `TraceObservation`:

```python
TraceObservation(
    state_id="opaque-7f",
    produced={"sha256:3a..."},
    direct_inputs={"sha256:81..."},
    ancestral_records={"sha256:4c..."},
)
```

`state_id` is opaque. The extractor never parses, ranks, or sorts it to infer
an edge. The state collection is an unordered set conceptually; sorting is
used only inside diagnostics to make output reproducible.

The public schema has no `depends_on`, predecessor, timestamp, sequence,
position, process identifier, ground-truth edge, or evaluator artifact ID.
The parser rejects unexpected fields rather than accepting a disguised edge
declaration.

`produced` is a set of public fingerprints emitted by a state-local operation.
`direct_inputs` is a set of fingerprints present in an immediate-input
manifest. `ancestral_records` is a set of fingerprints retained by a derived
object, a provenance fragment, or another non-immediate historical record.
The latter can be evidence of ancestry but is insufficient evidence of a direct
edge.

## Extraction rule

For every direct-input fingerprint `k` in a consumer state `y`, form the set
of public producers:

```text
Prod_X(k) = { x | k is in x.produced }
```

The deterministic rule is:

| Public producer set | Result |
| --- | --- |
| `Prod_X(k) = ∅` | `UNKNOWN`; infer no edge. |
| `Prod_X(k) = {x}`, `x != y` | infer direct candidate `x -> y`. |
| `|Prod_X(k)| > 1` | `AMBIGUOUS`; infer no edge. |
| `Prod_X(k) = {y}` | `CONFLICT`; infer no self-edge. |

If independently supported candidates form a directed cycle, every candidate
edge in that cycle is removed and reported as `CONFLICT`. The extractor does
not choose an edge by array position, identifier spelling, or a traversal
tie-break.

For an `ancestral_records` fingerprint, a unique producer produces
`ANCESTRAL` evidence only. It does **not** yield `x -> y`, because it may be a
multi-hop trace. Zero producers yields `UNKNOWN`, and multiple producers
yields `AMBIGUOUS`.

Malformed public records are rejected at the boundary with
`TraceValidationError`. They yield neither an edge nor a guessed status.

## Identifiability claim and limit

Under the explicit model condition that a unique public output fingerprint
identifies the concrete producer of an immediate consumed input, each direct
edge inferred by this rule is sound with respect to that condition. This is a
conditional property of the trace model, not a theorem about arbitrary logs.

The inverse limit is equally important. If two latent worlds produce the same
public observations `X` but realize different producer identities for the same
fingerprint, no deterministic extractor `E(X)` can return both distinct true
graphs. In this situation the correct outcome is `AMBIGUOUS`, not a fabricated
order. A stale or false trusted trace with exactly the same observable form as
a genuine immediate input is likewise not generally detectable without an
extra public invariant; the extractor must expose the resulting false candidate
rather than consult evaluator truth.

## Relation to PATAP and observer B

The experiment's modern analogue is:

```text
latent process W -> observation T(W) -> public traces X -> external E(X)
    -> recovered direct graph -> PATAP partial order
```

`E` is an external analytical instrument. Internal observer B does not run
the extractor, does not know PATAP or a global graph, and receives no
descendants as a known future. The software model evaluates whether local
traces are sufficient for an external reconstruction; it does not state that B
knows the reconstruction or that physical time has been derived.
