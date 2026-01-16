# Change Proposal: change-output-to-filename

## Summary
Modify `-o` flag to accept a full output filename instead of an output directory, supporting both absolute and relative paths.

## Why
Current behavior uses `-o` for output directory, automatically generating output filename. This prevents explicit output filename control. Users need to specify exact output paths for better integration with pipelines and existing workflows.

## What Changes
**Breaking Change**: `-o` behavior changes from directory path to full file path.
- Before: `csvnorm data.csv -o output_folder/` → `output_folder/data.csv`
- After: `csvnorm data.csv -o output_folder/data.csv` → `output_folder/data.csv`

Changes to `output-location` spec:
- MODIFIED: Output file path specification - now accepts full file path instead of directory
- REMOVED: Default output directory requirement - replaced by file path specification
- MODIFIED: Existing output file blocks without force - updated to reference file path

## Decisions
1. **No backward compatibility** - clean break to directory-based `-o`
2. **No extension validation** - user chooses any output filename/extension
3. **Temp files** in system temp directory (auto-cleanup), `reject_errors.csv` in output directory with overwriting
