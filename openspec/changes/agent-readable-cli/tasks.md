# Tasks: agent-readable-cli

## 1. Help and version

- [x] 1.1 Tests: help sections, no escape codes, under 100 lines, Start here commands run; `--version` one line off-terminal
- [x] 1.2 New description and epilog in `cli.py`; shorter option texts; metavars `N`, `FILE`, `CHAR`; encoding names in the epilog
- [x] 1.3 `VersionAction`: one plain line when stdout is not a terminal

## 2. Errors and exit codes

- [x] 2.1 `EXIT_OK`, `EXIT_INVALID`, `EXIT_ERROR` in `core.py`; fatal paths in `core.py` and `cli.main` return 2; unexpected exceptions caught in `main`
- [x] 2.2 `ui._print_boxed`: panels on a terminal, plain lines otherwise
- [x] 2.3 Remedy in the error messages that lacked one; existing output reported as an error
- [x] 2.4 Existing tests that expected 1 for fatal errors updated to 2, each checked

## 3. Docs and validation

- [x] 3.1 README: install and version check, exit codes, remote URLs, `--download-remote`
- [x] 3.2 `openspec validate agent-readable-cli --strict`; full suite; mypy
- [ ] 3.3 After release: clean install from PyPI, fresh agent session with no skill, small real task from `--help`; also without network
