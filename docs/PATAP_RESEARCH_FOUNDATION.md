# PATAP Research Foundation

## Purpose

PATAP investigates a narrow, falsifiable question:

> Can an external analysis reconstruct an observer-local partial order from
> non-temporal structural traces, without being given a global clock, input
> sequence, timestamp, or declared dependency edge?

This is not a claim that physical time has been derived. It is a programme for
separating what can be proved about structural ordering from what remains a
physical hypothesis.

The historical visual notation `-0` is retained only as background: it denoted
a structural description before an internal observer has separated accessible
experience into past, present, and future. It is not arithmetic negative zero,
and it is not the current name of the project.

## Historical model and its careful status

The early model wrote

\[
M=(S,A,B,\rho,\{D_O\}),
\]

and defined a phenomenal-time candidate for an internal observer \(O\) as

\[
\operatorname{Time}_{\mathrm{phen}}(O)=
\left(\operatorname{Im}(D_O\circ\rho)\setminus\{\bot\},\prec_O\right).
\]

Here \(S\) is a structural state space, \(A\) is an external modelling
perspective, \(B\) is a class of internal observers, \(D_O\) is an
observer-relative distinction/accessibility operator, and \(\bot\) represents
what is not distinguishable to that observer. The historical statement
\(\operatorname{Time}_{\mathrm{phen}}(A)=\varnothing\) is a **model
postulate**, not an empirical theorem.

The early notation exposed its own foundational risk: if \(\rho\) is an
already temporally indexed trajectory, it has smuggled the order to be derived
into the input. Likewise, a rate such as \(dx/dt\) presupposes a temporal
parameter. PATAP therefore does not treat either as a primitive input to its
reconstruction experiments.

## What earlier work already established

PATAP does not claim to have invented partial orders, concurrency, provenance,
or non-clock ordering.

| Area | What it contributes | What it does not by itself answer for PATAP |
| --- | --- | --- |
| [Lamport's happened-before relation](https://doi.org/10.1145/359545.359563) | A partial order of distributed events and a logical-clock construction. | It begins from process/message semantics, not from a deliberately restricted observer-local trace channel; logical clocks are an added ordering mechanism. |
| [Event structures](https://www.cl.cam.ac.uk/~gw104/Winskel1987_Chapter_EventStructures.pdf) | Formal causality, conflict, concurrency, and configurations. | The enabling/causality structure is part of the model; the problem of recovering it from incomplete traces is separate. |
| [W3C PROV-DM](https://www.w3.org/TR/2012/WD-prov-dm-20120503/) | Explicit entity/activity/use/generation provenance, including the fact that equal values may be distinct entities. | Its relations are declared provenance assertions; it is not an identifiability theory for an observer receiving only lossy traces. |
| [Causal-set theory](https://arxiv.org/abs/1903.11544) | A physics programme in which a locally finite partial order is fundamental. | It postulates a physical order; it does not demonstrate recovery of that order from observer-accessible records, and PATAP makes no causal-set or quantum-gravity claim. |

The proximity is useful rather than embarrassing. It sets a high standard:
PATAP can matter only by stating exactly what information is available, what is
hidden, and what follows from the distinction.

## The missing link in early PATAP

The original model had a compelling direction but lacked an operational bridge:

\[
\text{accessible structure}\quad\not\Rightarrow\quad
\text{specified recovery rule or a measurable error condition}.
\]

Seven requirements were missing or incomplete.

1. **Trace schema.** `D_O` needed a concrete non-temporal representation rather
   than an informal notion of a record.
2. **Information boundary.** The evaluator's world, public observation, and
   extractor input had to be separated. A field equivalent to
   `depends_on=[X]` cannot test reconstruction.
3. **Identifiability.** A theory needed to say when a trace determines a direct
   predecessor, when it determines only ancestry, and when it determines
   nothing.
4. **Ambiguity semantics.** Indistinguishable producers cannot honestly be
   resolved by choosing one. `AMBIGUOUS` and `UNKNOWN` are required results.
5. **Controls.** Input shuffle, opaque-ID replacement, trace removal, loss,
   corruption, and false-trace controls are needed to rule out hidden time.
6. **Relation discipline.** Actual-use/provenance \(\to_{use}\) is distinct
   from counterfactual necessity \(\to_{nec}\). Neither is automatically
   physical causality.
7. **Claim discipline.** A partial-order result does not derive duration,
   clocks, dynamics, probability, relativity, entropy, or physical time.

## Modern PATAP experiment boundary

The current research architecture is:

\[
W \xrightarrow{\ T\ } X \xrightarrow{\ E\ } \widehat G
\xrightarrow{\ \mathrm{TC}\ } \widehat\prec.
\]

- \(W\): a latent world/process. Evaluator-only actual-use truth is
  \(x\to_{use}y\) when operation \(y\) consumed the concrete artifact instance
  produced by operation \(x\).
- \(T\): an observation function that retains, removes, corrupts, or exposes
  structural records such as immutable artifact fingerprints and composition
  manifests.
- \(X=T(W)\): public observations. They have opaque state IDs and no timestamp,
  sequence number, input ordering semantics, path-derived edge semantics,
  `depends_on`, or evaluator truth.
- \(E\): deterministic external extractor. It is not executed by the internal
  observer \(B\).
- \(\widehat G\), \(\widehat\prec\): recovered direct graph and its transitive
  partial order.

The observer constraint remains central: \(B\) does not know that \(A\),
PATAP, \(W\), \(T\), or \(E\) exists. B has only its present local state and
whatever traces it contains. Descendants are not supplied as B's future;
future is `unknown_by_design`.

## Formal propositions that PATAP can actually support

Let each public row \(y\) expose a finite set of immediate trace keys
\(C(y)\), and let each row \(x\) expose a finite set of produced keys
\(P(x)\). For a key \(k\), define

\[
\mathrm{Prod}_X(k)=\{x\mid k\in P(x)\}.
\]

The basic extractor reports:

\[
E(X,k,y)=
\begin{cases}
x\to y & \text{if } \mathrm{Prod}_X(k)=\{x\}\text{ and }x\ne y,\\
\mathrm{UNKNOWN} & \text{if } \mathrm{Prod}_X(k)=\varnothing,\\
\mathrm{AMBIGUOUS} & \text{if } |\mathrm{Prod}_X(k)|>1.
\end{cases}
\]

### Proposition 1 — permutation invariance

If \(E\) uses only the sets \(P(x)\), \(C(y)\), and opaque row identities,
then any permutation of the public-record array produces the same recovered
edge set.

**Reason.** The producer map and every lookup above are functions of membership,
not of array position. This is a mathematical property of the extractor and a
testable software invariant.

### Proposition 2 — unique-trace soundness

Suppose a public immediate key \(k\in C(y)\) was soundly emitted by \(T\) for
an actual direct use of an artifact from \(x\), no other public row produces
\(k\), and \(x\ne y\). Then the basic extractor returns \(x\to y\).

**Status.** This is a conditional correctness theorem about the specified
observation contract. It is not a theorem that arbitrary real-world traces are
sound or unique.

### Proposition 3 — observational non-identifiability

If two latent worlds \(W_1\) and \(W_2\) yield the identical public observation
\(T(W_1)=T(W_2)\), but disagree about whether a direct actual-use edge
\(x\to_{use}y\) occurred, then no deterministic extractor receiving only
\(T(W)\) can be correct on both worlds for that edge.

**Proof.** A deterministic extractor receives identical input in both worlds,
so it must emit identical output. That output cannot equal two contradictory
ground-truth answers. \(\square\)

This is the crucial anti-fabrication result: insufficient accessible structure
must lead to `UNKNOWN` or `AMBIGUOUS`, not manufactured temporal order.

### Proposition 4 — incomparability preservation

The transitive closure of recovered direct edges may establish comparability
only along recovered paths. In the absence of either direction of a path, the
extractor must retain incomparability instead of creating a total order.

## What PATAP is stronger on — conditionally

PATAP is not stronger than Lamport, PROV, event structures, or causal-set work
at their established goals. Its potentially distinctive contribution is a
single conjunction that can be tested:

1. the internal observer is modelled as local and non-omniscient;
2. external reconstruction receives only an explicitly restricted trace
   channel;
3. direct dependency is inferred rather than declared;
4. non-identifiability is a first-class output;
5. reconstructed order stays partial and does not expose future descendants to
   the observer API.

This is a research position, not a priority claim. It becomes scientifically
strong only if results on independent, non-PATAP-created trace corpora survive
the stated controls.

## Existing evidence and its limits

- **v0.1–v0.2 software fact:** declared dependencies can be validated and
  converted into a dependency partial order. This does not establish raw-trace
  extraction.
- **v0.3 software fact:** the frozen context-selection benchmark found no
  advantage for PATAP ancestry over its lexical baseline. The negative result
  is retained and must not be rewritten.
- **v0.4 software fact:** a controlled trace-reconstruction validation tested
  a deterministic mechanism with shuffled inputs, trace-removed controls, and
  ambiguity handling. It supports only the controlled claim associated with its
  frozen synthetic world and protocol.
- **Open problem:** external validity on independently created traces has not
  yet been established. The incomplete v0.5 recorder work is not evidence and
  must not be presented as a successful external experiment.

## Research sequence that preserves the original idea

1. Publish a formal note proving the propositions above and defining a trace
   language independent of any one software platform.
2. Extend the implementation so every inferred edge carries a minimal witness
   and every non-edge can be explained as no witness, ambiguous witness, or
   excluded non-immediate evidence.
3. Test identifiability on independently authored, static provenance datasets
   where exact public/evaluator separation can be audited. Do not start by
   claiming universal operating-system capture.
4. Seek independent replication and critical review before extending any claim
   toward physics.
5. Only a distinct, falsifiable physical prediction could elevate PATAP from a
   structural reconstruction framework to a physical theory candidate.

## Safe conclusion

PATAP has a coherent and testable core: observer-accessible non-temporal
structure can, under explicit trace conditions, support reconstruction of a
local partial order. This does not prove that physical time, causality, or
spacetime emerges from PATAP. Whether suitable structural traces occur in
natural physical systems, and whether they yield new physical predictions,
remains open.

## Sources

1. Leslie Lamport, *Time, Clocks, and the Ordering of Events in a Distributed
   System* (1978), [DOI](https://doi.org/10.1145/359545.359563).
2. Glynn Winskel, *Event Structures* (chapter/PDF),
   [University of Cambridge](https://www.cl.cam.ac.uk/~gw104/Winskel1987_Chapter_EventStructures.pdf).
3. W3C, *PROV-DM: The PROV Data Model*,
   [W3C Recommendation draft](https://www.w3.org/TR/2012/WD-prov-dm-20120503/).
4. Fay Dowker and Sumati Surya, *The causal set approach to quantum gravity*,
   [arXiv:1903.11544](https://arxiv.org/abs/1903.11544).
