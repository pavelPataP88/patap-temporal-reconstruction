# External Trace Corpus Admissibility for PATAP

## Decision

No existing source examined in this first audit is admitted as evidence for the
central PATAP claim. This is a positive methodological decision: a source
that already publishes a dependency edge, or one that cannot distinguish a
concrete artifact version from a pathname, cannot test whether the edge is
recoverable from a restricted non-temporal trace channel.

An admissible external corpus must contain computations not designed for PATAP.
It must allow a privileged evaluator to establish realized artifact use while a
separate public channel exposes only non-temporal structural evidence. It is
not enough for a corpus to be called "provenance."

## The information boundary

For each corpus, PATAP requires two separately generated views of one observed
execution:

```text
raw execution capture
  ├─ evaluator channel: concrete producer artifact instance -> consumer use
  └─ public channel: opaque computation ID + consumed/produced fingerprints
```

The public channel must contain no declared dependency edge, path-derived
dependency rule, event position, timestamp, PID chronology, run order, or
evaluator artifact-instance identifier. Its rows must be permutable without
changing extraction.

The actual-use target is deliberately narrow:

```text
x ->use y
```

means that computation `y` actually consumed a concrete regular-file artifact
version produced by `x` in the observed execution. It is not a claim of
counterfactual necessity or physical causality.

## First audit of existing sources

| Source | What it genuinely provides | Why it is not admitted unchanged |
| --- | --- | --- |
| [W3C PROV](https://www.w3.org/TR/prov-primer/) | A formal vocabulary for entities, activities, `used`, and `wasGeneratedBy`; entities can represent distinct versions. | `used` and generation relations are provenance assertions. Handing those relations to an extractor would serialize the target edge under standard names rather than test recovery. It is a comparison language, not an external test corpus for this question. |
| [OpenLineage](https://github.com/OpenLineage/OpenLineage/blob/main/spec/OpenLineage.md) | Runtime input/output dataset facets and a public event schema. | Input/output lineage is the instrument's declared lineage data. Its run/event structure also includes information that must be explicitly stripped before a PATAP public view. It cannot be accepted as evidence without an independent evaluator/public separation. |
| [ReproZip](https://docs.reprozip.org/en/latest/) | A Linux `ptrace` capture of system calls and a trace SQLite database; it can visualize file/process provenance. | Its post-capture configuration aggregates filesystem access to classify input/output paths. Documentation explicitly distinguishes raw trace data from information obtained from the filesystem after execution. That does not, by itself, establish which byte-version was read at a particular use. It is an engineering reference, not a valid artifact-instance corpus as-is. |

The rejection is not a criticism of these systems. Each solves a different,
valuable problem. PATAP's experiment asks a narrower question: what can be
recovered when evaluator-level provenance is withheld rather than published.

## Admission gate

A candidate corpus is admitted only if every condition below is documented and
checked before running a PATAP score.

1. **Independent origin.** The computations and their artifacts were not
   created or selected after observing PATAP extraction scores.
2. **Concrete-version truth.** The evaluator can distinguish a producer's
   artifact instance from a later replacement at the same pathname and from an
   independently produced byte-identical artifact.
3. **Separate derivations.** Evaluator truth and public observations are
   produced by different transforms of raw capture; the public transform never
   reads evaluator edges.
4. **Non-temporal public view.** Public records omit timestamps, counters,
   process launch order, positions, semantic paths, build-system edges, and
   dependency declarations. State IDs are opaque and are randomly replaced in
   a control.
5. **Artifact evidence.** Public consumed and produced fingerprints are
   generated from the observed concrete artifacts, not constructed from a list
   of true parents.
6. **Coverage accounting.** Every candidate same-execution producer/consumer
   read is counted as resolved or unresolved. An experiment may not delete
   unresolved reads to improve its score; coverage is reported separately.
7. **Auditable controls.** The corpus supports record shuffle, opaque-ID
   replacement, removal of public input fingerprints, controlled trace loss,
   and insertion of a genuine-looking false trace.
8. **Holdout discipline.** Extractor rules are frozen before the admitted
   corpus is scored. Calibration material is not reported as external
   validation.

## Minimum evidence package

An admitted corpus must publish, with checksums where practical:

- source repository and exact revision, or another immutable source reference;
- build/execution command and environment;
- public observations, shuffled before extraction;
- evaluator truth kept in a separate directory and code path;
- resolved and unresolved artifact-instance coverage records;
- manual audit of sampled producer-to-consumer uses;
- frozen extractor revision, controls, raw scores, and reproduction command.

## Falsification criteria

The external claim is **not** supported when any of the following occurs:

- an edge is available to the public extractor as a declared provenance field;
- public record order or identifier spelling changes the graph;
- a path replacement or duplicate-content producer can silently be treated as
  the same evaluator artifact instance;
- `UNKNOWN` or `AMBIGUOUS` cases are forced into definite edges;
- the public trace removal control still recovers the original order;
- project-specific semantics are needed for the common extractor.

This gate makes a negative result useful: it can show either that the traces
are insufficient, or that the measurement instrument was insufficient. Those
are different conclusions and must not be conflated.

## Next research action

The next step is not to alter the extractor. It is to find or capture a
corpus meeting this gate, publish the admissibility audit before extraction,
and accept the measured result. Until that happens, PATAP has a controlled
trace-identifiability result, not an external generalization claim.
