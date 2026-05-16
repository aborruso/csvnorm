## 1. Implementation

- [ ] 1.1 `utils.py`: add `has_crlf_line_endings(file_path: Path) -> bool`
- [ ] 1.2 `validation.py`: add `convert_row_endings_to_crlf(file_path: Path) -> None` (byte-level state machine)
- [ ] 1.3 `core.py`: detect CRLF on original input before processing
- [ ] 1.4 `core.py`: apply CRLF post-processing after normalization (file mode only)

## 2. Tests

- [ ] 2.1 Create fixture `test/crlf_with_embedded_lf.csv`
- [ ] 2.2 Test: file output preserves CRLF row terminators and LF in-cell newlines
- [ ] 2.3 Test: LF-only input produces LF-only output (no regression)
- [ ] 2.4 Test: stdout mode always outputs LF even when input is CRLF

## 3. Documentation

- [ ] 3.1 Update `LOG.md`
