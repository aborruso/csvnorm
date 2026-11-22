## ADDED Requirements

### Requirement: Preserve CRLF row terminators in file output

When the input CSV uses CRLF (`\r\n`) as row terminators and output is written to a file (`-o`), the system SHALL preserve CRLF in the output. In-cell LF newlines (inside quoted fields) SHALL remain as LF. Stdout output SHALL always use LF regardless of input line endings.

Detection is automatic: no user configuration is required.

#### Scenario: CRLF input written to file preserves CRLF

- **WHEN** input CSV has CRLF row terminators and in-cell LF newlines inside quoted fields
- **AND** user runs `csvnorm input.csv -o output.csv`
- **THEN** output file row terminators are CRLF
- **AND** in-cell newlines inside quoted fields remain LF

#### Scenario: LF-only input written to file stays LF

- **WHEN** input CSV uses LF-only line endings
- **AND** user runs `csvnorm input.csv -o output.csv`
- **THEN** output file uses LF-only line endings (no change to current behavior)

#### Scenario: CRLF input to stdout uses LF

- **WHEN** input CSV has CRLF row terminators
- **AND** user runs `csvnorm input.csv` (stdout mode, no `-o`)
- **THEN** stdout output uses LF line endings (Unix pipeline compatibility)
