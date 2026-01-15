## 1. Implementation
- [x] 1.1 Confirm the exact CLI invocation and output format for `charset_normalizer` to extract a single encoding label.
- [x] 1.2 Update `script/prepare.sh` to use `charset_normalizer` as the primary detector while preserving SIGPIPE and fallback behavior.
- [x] 1.3 Update dependency lists (Makefile, README.md, openspec/project.md, PRD.md, CLAUDE.md) to replace `chardet` with `charset_normalizer`.
- [x] 1.4 Update or add tests/fixtures if needed to validate encoding detection behavior.
- [x] 1.5 Run `shellcheck script/prepare.sh` and `make test`.
- [x] 1.6 Update LOG.md with the change.
