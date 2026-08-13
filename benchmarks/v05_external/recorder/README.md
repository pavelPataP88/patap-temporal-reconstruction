# Descriptor-level recorder (engineering preflight)

`ptrace_recorder.c` is an evaluator-side Linux/x86-64 process-tree supervisor.
It snapshots a regular read-only descriptor while the traced task is stopped at
the successful open boundary, and fingerprints a dirty output descriptor at its
close boundary. It retains privileged PID, epoch, descriptor, device and inode
information only in its JSONL output.

It deliberately emits `*_unresolved` events for access modes or mechanisms it
cannot yet prove safe. In particular, its current `mmap` handling is explicit
UNRESOLVED; therefore this code is an engineering instrument under test, not a
scientific v0.5 capture protocol or evidence of external validation.

The public adapter must be a separate stage and may expose only opaque unit IDs
and content fingerprints. It must not reuse privileged identities or event
order in this recorder log.

`fanotify_recorder.c` is retained only as a rejected exploratory attempt. It
does not establish open-file-description identity across close events and must
not be used for provenance scoring.
