## 1. Proposal Validation
- [ ] 1.1 Run `openspec validate add-mojibake-repair-ftfy --strict` and fix any errors

## 2. Implementation
- [ ] 2.1 Add CLI flag for mojibake repair and wire through to `process_csv`
- [ ] 2.2 Implement mojibake detection/repair step using ftfy (local files and remote URLs when flag enabled)
- [ ] 2.3 Support optional sample size argument to `--fix-mojibake`
- [ ] 2.4 Add summary output for mojibake repair status
- [ ] 2.5 Add dependency metadata (pyproject/README) and update LOG.md

## 3. Tests
- [ ] 3.1 Add unit test for mojibake detection/repair logic
- [ ] 3.2 Add integration test for `--fix-mojibake` happy path
- [ ] 3.3 Add test for `--fix-mojibake <N>` sample size override
