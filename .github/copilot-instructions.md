## CSV Normalizer — Quick instructions for AI coding agents

Purpose: Help an AI contributor be productive quickly by documenting the runtime entrypoints,
important patterns, and project-specific behaviours discovered in this repo.

1) Big picture
- This repo implements a single-command CSV normalizer driven by the Bash wrapper `script/prepare.sh`.
- Core behaviours are: encoding detection (chardet / fallback to `file`), optional `iconv` conversion to UTF-8,
  validation and normalization using DuckDB's `read_csv`, and an output write path in `script/tmp` by default.

2) Where to look
- Primary script: `script/prepare.sh` (source of truth for CLI flags and implementation details).
- Requirements & goals: `PRD.md` and `README.md` — useful for expected behaviour and acceptance criteria.
- Changelog for behavioural fixes: `LOG.md` (e.g. SIGPIPE handling for `chardetect`).
- Example input: `test/*.csv` (use these for quick smoke tests).

3) Key workflows and commands (examples taken from `script/prepare.sh`)
- Run the tool: `script/prepare.sh input.csv [options]`.
- Common options: `-f|--force` (overwrite), `-n|--no-normalize` (keep original headers),
  `-d|--delimiter <char>`, `-o|--output-dir <dir>`, `-v|--verbose`.
- Output: `<output_dir>/<clean_name>.csv` (default `script/tmp/<snake_cased_input>.csv`).
- Rejects file: `${output_dir}/reject_errors.csv` — if it has > 1 line the script exits with code 1.

4) Important implementation details to preserve when editing
- Encoding detection: `chardet --minimal` is used with SIGPIPE handling; fallback uses `file -b --mime-encoding`.
- Conversion: if detected encoding isn’t `utf-8|ascii|utf-8-sig` the script runs `iconv -f <enc> -t UTF-8` to a temp file
  (`${output_dir}/${base_name}_utf8.csv`) and then uses that for DuckDB input.
- DuckDB usage: validation via `read_csv(..., store_rejects=true, sample_size=-1)` and final write using `copy (...) to '<file>' (header true, format csv[, delimiter 'X'])`.
- Header normalisation: implemented via DuckDB `normalize_names=true` or via a shell-derived `base_name` transformation.
- Temp files: script cleans `reject_errors.csv` and the `_utf8.csv` temp; preserve that cleanup behaviour unless intentionally changing lifecycle.

5) Project-specific conventions & checks
- The Bash script sets `set -euo pipefail` — follow this pattern in new shell tooling.
- The PRD expects `shellcheck` compliance and references `CONVENTIONS.md` — run `shellcheck script/prepare.sh` when modifying shell code.
- CI / packaging: README suggests `pip install .` but packaging files (pyproject/setup) are not present; verify before adding Python packaging changes.

6) Integration points / external deps
- Requires installed: `chardet` (CLI), `iconv`, `file`, and DuckDB (CLI). The README lists Python packages too, but current scripts are Bash + DuckDB CLI.

7) Small contract for edits
- Inputs: arbitrary CSV file path (may be large). Outputs: normalized CSV in output dir, and `reject_errors.csv` when invalid rows exist.
- Error modes: non-UTF-8 encodings, invalid CSV rows (DuckDB rejects), pre-existing output file (overwritten only with `--force`).

8) Quick tests and smoke checks
- Run `script/prepare.sh test/<example.csv>` and confirm a new file under `script/tmp/` and no `reject_errors.csv` for valid samples.
- Run `shellcheck script/prepare.sh` after edits.

9) When content is missing or ambiguous
- If you need to change Python packaging, note there is no `pyproject.toml`/`setup.py` — propose adding one and mention compatibility with README.
- No unit tests found. Add small smoke tests using files in `test/` and document them in README if you introduce behavior changes.

If anything above is unclear or you want the instructions expanded (e.g., include exact shellcheck rules or CI commands), tell me which section to expand.
