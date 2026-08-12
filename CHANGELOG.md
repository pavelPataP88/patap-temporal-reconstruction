# Changelog

## 0.2.1 - 2026-08-12

- Added distribution build and clean-install validation to CI.
- Corrected installation instructions for the pre-PyPI package.
- Made repeated state recording merge dependencies and preserve omitted metadata.
- Added public read-only state accessors used by `PATAPMemory`; reconstruction semantics are unchanged.

## 0.2.0 - 2026-08-12

- Added `PATAPMemory` for recording agent states and retrieving local structural context.
- Added JSON persistence, memory CLI commands, and deterministic demo/benchmark scripts.
- Added memory-layer tests for provenance, isolation, persistence, and context ratios.

## 0.1.0 - 2026-08-12

- Initial public release of the deterministic dependency-based reconstruction engine.
- Added Python API, CLI, examples, tests, and GitHub Actions coverage.
