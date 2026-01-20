## 1. Implementation
- [ ] 1.1 Add `--in-place` flag to CLI and enforce mutual exclusion with `-o/--output-file`
- [ ] 1.2 Validate `--in-place` only for local files (reject HTTP/HTTPS)
- [ ] 1.3 Write normalized output to a temp file and atomically replace the input on success
- [ ] 1.4 Ensure reject file path is `{input_dir}/{input_stem}_reject_errors.csv` for in-place mode
- [ ] 1.5 Update summary messaging to indicate in-place output target
- [ ] 1.6 Add tests for in-place happy path, URL rejection, and overwrite behavior
- [ ] 1.7 Update `LOG.md` with the change
