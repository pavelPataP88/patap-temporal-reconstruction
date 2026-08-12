# Context Selection Benchmark

Run `python benchmarks/run_context_benchmark.py`. The command reads the checked-in static JSON dataset, compares FULL, structural PATAP context, a size-matched recency baseline, and a size-matched lexical baseline, then writes raw JSON and a report.

Required facts are static annotations in the dataset; the runner does not derive them from PATAP ancestry. Dependency records are declared input, not automatically inferred.
