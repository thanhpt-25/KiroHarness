# How to run the evals and quality gates

- `python3 -I evals/run.py` replays the scenarios in `evals/scenarios/` through every Adapter; add a JSON file there to add one.
- `python3 -I evals/run.py --corpus` replays the Bypass_Corpus. A `must-block` item that is allowed fails the run; a `known-gap` item that becomes blocked also fails, so promote it to `must-block` in the same commit.
- `scripts/coverage.sh` enforces 90 percent line and 80 percent branch coverage; `scripts/mutation.sh` scores the guard modules (weekly in CI).
- `scripts/test-properties.sh` runs the property suite; `HYPOTHESIS_PROFILE=ci` uses 300 examples.

See the [command reference](../reference/cli.md) for every script.
