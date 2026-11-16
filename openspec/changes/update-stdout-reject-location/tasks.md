# Tasks: update-stdout-reject-location

- [x] 1.1 Test (subprocess): stdout run with invalid CSV leaves no `reject_errors.csv` in the working directory; the path in `Details:` on stderr exists and holds the rejected rows
- [x] 1.2 Test: stdout run with valid CSV leaves no reject file in the temp directory
- [x] 1.3 `_setup_output_paths`: stdout reject file in `tempfile.gettempdir()` with a unique name
- [x] 1.4 README: stdout mode section
- [x] 1.5 Full test suite
