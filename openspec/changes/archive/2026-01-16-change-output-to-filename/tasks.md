# Tasks: change-output-to-filename

## Ordered Implementation Tasks

1. Update `src/csvnorm/cli.py` to change `-o/--output-dir` to `-o/--output-file` argument accepting full file path
2. Update `src/csvnorm/core.py::process_csv()` to handle `output_file` parameter instead of `output_dir`
3. Modify path resolution logic: reject files in output directory, temp utf8 files in system temp directory using `tempfile.mkdtemp()`
4. Update help text and examples in CLI to reflect new behavior
5. Update `openspec/specs/output-location/spec.md` with new requirements
6. Update `tests/test_cli.py` tests for `-o` flag behavior
7. Update `tests/test_integration.py` fixture methods using `output_dir` parameter
8. Update LOG.md with breaking change notice
9. Run `make test` to verify all tests pass
10. Run `shellcheck script/prepare.sh` to verify script compliance

## Validation
- All existing tests pass after updates
- New tests cover absolute and relative paths
- Reject/temp files correctly placed in output file's directory
- Force flag works with new output specification
