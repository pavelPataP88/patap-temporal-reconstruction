# Observer Quotient Order

## Status

This document is a finite mathematical formalization of the historical PATAP
idea that observer-accessible distinctions may support a local ordering. It
does not claim to derive physical time, duration, causality, a physical
trajectory, or any new physical law.

The operator `D_O` below is a model element. The audit implementation uses an
evaluator-only latent order to check a theorem; it is not an algorithm that an
internal observer B runs, and it is not the raw-trace extractor.

## Definitions

Let `(S, <)` be a strict partial order: it is irreflexive and transitive. Let
an observer distinction map be:

```text
D_O : S -> X
```

where `X` is the set of observations that are distinguishable to the observer.
It induces an equivalence relation:

```text
x ~_O y  iff  D_O(x) = D_O(y).
```

The intended observer-local quotient has elements `[x]_O`. We would like to
write:

```text
[x]_O <_O [y]_O  iff  x < y.
```

This expression is valid only when it does not depend on the arbitrary choice
of representatives.

## The observer-order congruence theorem

**Theorem.** The quotient relation above is well-defined precisely if, for all
`x ~_O x'` and `y ~_O y'`,

```text
x < y  iff  x' < y'.
```

Under this condition, `<_O` is a strict partial order on the observer's
distinguishable classes.

**Proof.** The stated biconditional is exactly representative independence, so
the truth of `[x]_O <_O [y]_O` is well-defined. If a class preceded itself,
choose the same representative on both sides; irreflexivity of `<` gives a
contradiction. If `[x]_O <_O [y]_O` and `[y]_O <_O [z]_O`, choose
representatives. Transitivity of `<` yields `x < z`, hence
`[x]_O <_O [z]_O`. Therefore the quotient relation is irreflexive and
transitive. □

The condition is called **observer-order congruence** in this project. It is
a descriptive name for a standard quotient-order requirement, not a claim that
PATAP has discovered new mathematics.

## Why non-congruence matters

Suppose `D_O(a1) = D_O(a2) = source`, but only `a1 < b` and `a2` is
incomparable with `b`. Then an observer who can only distinguish `source`
cannot honestly infer either:

```text
source < result
```

or its negation. The two representative choices disagree. The correct
external result is an explicit violation/unknown, not a forced total order.

Likewise, if `a < b` but `D_O(a) = D_O(b)`, collapsing them into one class
would make that class precede itself. A valid observer-local strict order
therefore cannot identify comparable states in this way.

## Relation to trace extraction

The two layers are different and both are necessary:

```text
public traces X -> extractor E -> recovered graph G-hat
latent order + D_O -> evaluator audit of whether a quotient order is defined
```

`TraceExtractor` works on public structural records and returns direct,
ancestral, unknown, ambiguous, or conflicting evidence. It must not receive
the latent graph. `audit_observer_order()` instead receives evaluator truth
to verify whether a proposed distinction map satisfies the theorem above.

This separation prevents circularity. It also says exactly what an eventual
physical theory would still have to provide: a justified physical account of
the state space `S`, the access channel `D_O`, and an independently testable
reason that an observer-order congruence holds in real systems.

## Executable finite audit

`patap.observer_order.audit_observer_order()` takes a finite latent graph and a
complete map from state IDs to opaque observation classes. It returns either:

- a strict quotient-order relation; or
- representative-pair witnesses showing why the quotient is not defined.

The supplied tests cover a valid quotient, mixed representative relations,
an invalid collapse of comparable states, input-order invariance, and malformed
distinction maps.
