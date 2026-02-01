# Implementation Tasks

## 1. CLI and Error Handling
- [x] 1.1 Add `--strict` flag to argparse in `cli.py`
- [x] 1.2 Create `error-handling` capability spec in `openspec/specs/`
- [x] 1.3 Update help text to document strict mode behavior

## 2. Reject File Location
- [x] 2.1 Update `output-location` spec with new reject file behavior
- [x] 2.2 Modify `core.py` to place reject files in current directory for stdout mode
- [x] 2.3 Update temp directory cleanup logic to not delete current directory reject files
- [x] 2.4 Update tests for new reject file location

## 3. Early Validation Warning
- [x] 3.1 Update `processing-summary` spec with early warning requirement
- [x] 3.2 Modify validation flow to complete before normalization starts
- [x] 3.3 Show validation error panel to stderr BEFORE writing output
- [x] 3.4 Ensure progress indicators don't interfere with error visibility

## 4. Strict Mode Implementation
- [x] 4.1 Add strict mode check after validation in `core.py`
- [x] 4.2 Exit with code 1 if reject_count > 0 and strict mode enabled
- [x] 4.3 Show appropriate error message when strict mode triggers
- [x] 4.4 Update exit code documentation

## 5. Testing
- [x] 5.1 Add tests for `--strict` flag with validation errors
- [x] 5.2 Add tests for `--strict` flag with clean data
- [x] 5.3 Update stdout mode tests for new reject file location
- [x] 5.4 Add integration test for early warning visibility
- [x] 5.5 Test piped scenarios (`| head`, `| grep`, etc.)

## 6. Documentation
- [x] 6.1 Update README.md with strict mode usage
- [x] 6.2 Update CLAUDE.md with new behavior
- [x] 6.3 Add example commands showing strict mode
- [x] 6.4 Document reject file location change in changelog/migration notes
