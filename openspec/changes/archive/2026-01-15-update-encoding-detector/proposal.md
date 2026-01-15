# Change: Update encoding detection to charset_normalizer

## Why
`chardet` is the current primary encoding detector, but the request is to adopt `charset_normalizer` for improved detection accuracy and maintenance.

## What Changes
- Replace the primary encoding detection tool from `chardet` to `charset_normalizer` using `normalizer --minimal` directly on the input file.
- Keep `file -b --mime-encoding` as the fallback detector.
- Update dependency lists and documentation to reflect the new tool.

## Impact
- Affected specs: encoding-detection (new capability)
- Affected code: script/prepare.sh, Makefile, README.md, PRD.md, CLAUDE.md, openspec/project.md
