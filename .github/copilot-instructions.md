## CSV Normalizer — Quick instructions for AI coding agents

Purpose: Get an AI contributor productive quickly. This file highlights the runtime entrypoint, important implementation details to preserve, and the minimal commands and files you will need.

1) Big picture
- Single-command CSV normalizer implemented as a Bash wrapper: `script/prepare.sh` is the runtime entrypoint.
- Flow: encoding detection (chardet -> fallback to `file`) -> optional `iconv` to UTF‑8 -> validate with DuckDB `read_csv(store_rejects=true)` -> write normalized CSV via DuckDB `copy` into `script/tmp` (or `--output-dir`).

2) Where to look (source of truth)
- `script/prepare.sh` — full CLI parsing, encoding logic, DuckDB commands, temp-file lifecycle, and header normalisation.
- `PRD.md` / `README.md` — product goals, usage examples and Make targets.
- `LOG.md` — changelog with behavioral fixes (e.g., SIGPIPE handling for `chardetect`).
- `test/` — example CSVs for fast smoke tests.

3) Key commands & examples
- Run locally: `script/prepare.sh test/<example.csv>` (creates `script/tmp/<snake_cased_name>.csv`).
- Common flags: `-f|--force`, `-n|--no-normalize`, `-d|--delimiter $'\\t'`, `-o|--output-dir /path`.
- DuckDB validation (as used in the script):
  - `read_csv('<file>', store_rejects=true, sample_size=-1)` to collect rejects.
  - final write: `copy (...) to '<out>.csv' (header true, format csv[, delimiter \'\\t\'])`.

4) Implementation details to preserve (explicit)
- Encoding: `chardet --minimal` with SIGPIPE handling; fallback `file -b --mime-encoding`.
- Conversion: only run `iconv -f <detected> -t UTF-8` when encoding is not `utf-8|ascii|utf-8-sig`. The script writes a temp `${output_dir}/${base_name}_utf8.csv` and uses it as DuckDB input.
- Header normalization: `normalize_names=true` is used in DuckDB; `base_name` is created with `tr`/`sed` to snake_case for output filename.
- Temp files: remove `${output_dir}/reject_errors.csv` and `${output_dir}/${base_name}_utf8.csv` when empty/unused — keep this cleanup behaviour.

5) Project conventions & checks
- Shell policy: scripts use `set -euo pipefail`. Maintain this style in any new shell tooling.
- Run `shellcheck script/prepare.sh` after edits; PRD mentions ShellCheck compliance.
- README lists `make` targets (install, test, check, clean). Packaging files (`pyproject.toml`/`setup.py`) are not present — validate before adding Python packaging changes.

6) External deps & integration points
- Required at runtime: `chardet` (CLI), `iconv`, `file`, DuckDB CLI (or Python `duckdb` package if invoked differently).
- `Makefile` automates installing DuckDB and Python deps; check it before adding install steps.

7) Quick contract for edits
- Input: arbitrary CSV path (may be large). Output: UTF-8, comma-delimited CSV in `<output_dir>/<clean_name>.csv` and `reject_errors.csv` for invalid rows.
- Error modes to treat carefully: non-UTF-8 encodings, DuckDB rejects, and pre-existing outputs (respect `--force`).

8) Fast smoke tests
- `script/prepare.sh test/<example.csv>`, then verify `script/tmp/<snake_name>.csv` exists and `reject_errors.csv` is absent.
- After editing shell code, run `shellcheck script/prepare.sh` and re-run the smoke test.

9) When adding features
- If you introduce Python packaging or CLI entrypoints, add `pyproject.toml` and update `README.md` and `Makefile` accordingly — README currently suggests `pip install .` but packaging files are missing.

If anything in these notes is unclear or you want more detail (exact shellcheck rules, CI hooks, or example `make` output), tell me which section to expand.
