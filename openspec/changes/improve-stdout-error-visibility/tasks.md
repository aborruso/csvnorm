# Implementation Tasks

## 1. CLI and Error Handling
- [ ] 1.1 Add `--strict` flag to argparse in `cli.py`
- [ ] 1.2 Create `error-handling` capability spec in `openspec/specs/`
- [ ] 1.3 Update help text to document strict mode behavior

## 2. Reject File Location
- [ ] 2.1 Update `output-location` spec with new reject file behavior
- [ ] 2.2 Modify `core.py` to place reject files in current directory for stdout mode
- [ ] 2.3 Update temp directory cleanup logic to not delete current directory reject files
- [ ] 2.4 Update tests for new reject file location

## 3. Early Validation Warning
- [ ] 3.1 Update `processing-summary` spec with early warning requirement
- [ ] 3.2 Modify validation flow to complete before normalization starts
- [ ] 3.3 Show validation error panel to stderr BEFORE writing output
- [ ] 3.4 Ensure progress indicators don't interfere with error visibility

## 4. Strict Mode Implementation
- [ ] 4.1 Add strict mode check after validation in `core.py`
- [ ] 4.2 Exit with code 1 if reject_count > 0 and strict mode enabled
- [ ] 4.3 Show appropriate error message when strict mode triggers
- [ ] 4.4 Update exit code documentation

## 5. Testing
- [ ] 5.1 Add tests for `--strict` flag with validation errors
- [ ] 5.2 Add tests for `--strict` flag with clean data
- [ ] 5.3 Update stdout mode tests for new reject file location
- [ ] 5.4 Add integration test for early warning visibility
- [ ] 5.5 Test piped scenarios (`| head`, `| grep`, etc.)

## 6. Documentation
- [ ] 6.1 Update README.md with strict mode usage
- [ ] 6.2 Update CLAUDE.md with new behavior
- [ ] 6.3 Add example commands showing strict mode
- [ ] 6.4 Document reject file location change in changelog/migration notes
