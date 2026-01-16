## 1. Implementation

- [x] 1.1 Add URL validation utility to `src/csvnorm/utils.py`
  - Function `is_url(input_str: str) -> bool` to detect HTTP/HTTPS URLs
  - Function `validate_url(url: str) -> None` to ensure protocol is http/https
  - Function `extract_filename_from_url(url: str) -> str` to derive output name

- [x] 1.2 Update CLI argument parsing in `src/csvnorm/cli.py`
  - Change `input_file` type from `Path` to `str` to accept URLs
  - Update help text to mention URL support
  - Add example with URL in epilog

- [x] 1.3 Update core pipeline in `src/csvnorm/core.py`
  - Add URL detection at start of `process_csv()`
  - Skip file existence check for URLs
  - Skip encoding detection/conversion for URLs
  - Generate output filename from URL using utility function
  - Add progress message indicating remote URL processing

- [x] 1.4 Ensure DuckDB queries support URLs in `src/csvnorm/validation.py`
  - Verify `read_csv()` queries work with URL strings (no changes likely needed)
  - Add DuckDB httpfs timeout configuration (SET http_timeout=30000)

- [x] 1.5 Update error handling
  - Add specific error messages for HTTP errors (401, 403, 404, timeout)
  - Detect DuckDB HTTP errors and show user-friendly messages

## 2. Testing

- [x] 2.1 Add test with public CSV URL
  - Test with https://raw.githubusercontent.com or similar public source
  - Verify output file created with correct snake_case name
  - Verify validation and normalization work correctly

- [x] 2.2 Add test with invalid URL
  - Test with ftp:// protocol
  - Test with file:// protocol
  - Verify error message shown

- [x] 2.3 Add test for URL filename extraction
  - URL with .csv extension
  - URL without extension
  - URL with query parameters

- [x] 2.4 Manual test with real open data URL
  - Test with a typical open data portal CSV
  - Verify --force, --keep-names, --delimiter flags work with URLs

## 3. Documentation

- [x] 3.1 Update README.md
  - Add URL support to Features section
  - Add example with URL in Usage section
  - Mention 30s timeout limitation
  - Note that authentication is not supported

- [x] 3.2 Update LOG.md
  - Add entry with date
  - Describe new remote URL capability

## Dependencies

- Tasks 1.3 depends on 1.1 (needs utility functions)
- Tasks 1.3 depends on 1.2 (needs CLI changes)
- Task 2.1-2.4 depend on all implementation tasks
