# Change: Add optional mojibake repair using ftfy

## Why
Some CSVs are already decoded incorrectly (mojibake), so encoding detection/conversion alone cannot fix them. Issue #21 shows ftfy can reliably repair these cases, albeit with extra CPU cost.

## What Changes
- Add optional mojibake repair step using `ftfy`.
- Detect mojibake with `ftfy.badness` on a text sample; only apply fixes when the text is deemed bad.
- Allow `--fix-mojibake` to accept an optional sample size argument (default hardcoded).
- When `--fix-mojibake` is used with a remote URL, download the file to system temp first, then run repair on the local copy.
- Report whether mojibake repair was applied in the success summary.
- Add dependency on `ftfy` (and its transitive dependency `wcwidth`).

## Impact
- Affected specs: `mojibake-repair` (new), `processing-summary` (modified)
- Affected code: `src/csvnorm/core.py`, `src/csvnorm/cli.py`, `src/csvnorm/ui.py`, `src/csvnorm/encoding.py` (or new module), `pyproject.toml`, `README.md`, `LOG.md`
