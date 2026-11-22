## 1. Implementation

- [x] 1.1 `utils.py`: add `has_crlf_line_endings(file_path: Path) -> bool` (utils.py:298)
- [x] 1.2 `validation.py`: add `convert_row_endings_to_crlf(file_path: Path) -> None` (byte-level state machine) (validation.py:645)
- [x] 1.3 `core.py`: detect CRLF on original input before processing (core.py:725)
- [x] 1.4 `core.py`: apply CRLF post-processing after normalization (file mode only) (core.py:812)

## 2. Tests

- [x] 2.1 Create fixture `test/crlf_with_embedded_lf.csv`
- [x] 2.2 Test: file output preserves CRLF row terminators and LF in-cell newlines (tests/test_integration.py::TestCrlfPreservation::test_crlf_input_preserves_crlf_in_file_output)
- [x] 2.3 Test: LF-only input produces LF-only output (no regression) (test_lf_input_stays_lf_in_file_output)
- [x] 2.4 Test: stdout mode always outputs LF even when input is CRLF (test_crlf_input_stdout_always_lf)

## 3. Documentation

- [x] 3.1 Update `LOG.md` (LOG.md, voce 2026-05-16)
