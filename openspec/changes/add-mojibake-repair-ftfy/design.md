## Context
CSV files can be syntactically valid but still contain mojibake from prior mis-decoding (e.g., UTF-8 interpreted as ISO-8859-1). The current pipeline detects and converts encodings but does not repair mojibake. Issue #21 includes a working script that uses ftfy's badness heuristic and `fix_and_explain` to repair such text.

## Goals / Non-Goals
- Goals:
  - Provide an optional, safe mojibake repair step for local files.
  - Limit overhead by sampling for detection and only repairing when needed.
  - Keep the pipeline minimal and avoid affecting remote URL handling.
- Non-Goals:
  - Automatic detection/repair without user opt-in.
  - Replacing encoding detection/conversion logic.
  - Full audit trails of per-line transformations (only a summary status).

## Decisions
- Decision: Add a CLI flag `--fix-mojibake` that enables detection and repair, with an optional integer argument to set sample size.
  - Rationale: ftfy adds CPU cost; opt-in keeps default performance and avoids unexpected text changes.
- Decision: Use `ftfy.badness.is_bad()` on a sample (default hardcoded; user can override via `--fix-mojibake <N>`) to decide whether to repair.
  - Rationale: aligns with the script in issue #21 and keeps detection fast on large files.
- Decision: Apply `ftfy.fix_text()` (or `fix_and_explain()` in debug) to the full text only when flagged and badness indicates mojibake.
  - Rationale: minimize unnecessary transformations while leveraging ftfy's broader repair capabilities.
- Decision: Insert the repair step after UTF-8 conversion and before DuckDB validation/normalization.
  - Rationale: ensures we operate on Unicode text and avoid conflicting with conversion.
- Decision: When `--fix-mojibake` is used on a remote URL, download the file to system temp and treat it as local for repair.
  - Rationale: ftfy operates on decoded text; DuckDB remote streaming would bypass repair.

## Risks / Trade-offs
- Additional CPU and memory use when repair runs. Mitigation: opt-in flag + sampling gate.
- Potential text changes beyond encoding fixes (ftfy also normalizes quotes/line breaks). Mitigation: opt-in flag and summary note indicating repair applied.
 - Remote URL downloads may increase I/O and disk usage. Mitigation: only when flag is enabled.

## Migration Plan
- Add dependency and CLI flag; no behavior change unless flag used.
- Document usage and caveats in README.

## Open Questions
- None.
