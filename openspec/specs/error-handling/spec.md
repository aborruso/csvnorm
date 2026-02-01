# error-handling Specification

## Purpose
TBD - created by archiving change improve-stdout-error-visibility. Update Purpose after archive.
## Requirements
### Requirement: Strict mode validation

The system SHALL provide a `--strict` flag that causes the command to fail (exit code 1) if any validation errors occur, preventing invalid data from being processed.

#### Scenario: Strict mode with validation errors

- **WHEN** user runs `csvnorm input.csv --strict`
- **AND** validation detects rejected rows
- **THEN** error panel is displayed to stderr showing validation failures
- **AND** no normalization occurs
- **AND** no output is written (neither to stdout nor to file)
- **AND** reject file is still created with error details
- **AND** system exits with code 1

#### Scenario: Strict mode with clean data

- **WHEN** user runs `csvnorm input.csv --strict`
- **AND** validation passes with zero rejected rows
- **THEN** normalization proceeds normally
- **AND** output is written (to stdout or file)
- **AND** system exits with code 0

#### Scenario: Strict mode with file output

- **WHEN** user runs `csvnorm input.csv -o output.csv --strict`
- **AND** validation detects rejected rows
- **THEN** error panel is displayed
- **AND** output file is NOT created
- **AND** reject file IS created in output directory
- **AND** system exits with code 1

#### Scenario: Non-strict mode with validation errors (default)

- **WHEN** user runs `csvnorm input.csv` (without `--strict`)
- **AND** validation detects rejected rows
- **THEN** error panel is displayed to stderr
- **AND** normalization proceeds with valid rows
- **AND** output is written (excluding rejected rows)
- **AND** reject file is created
- **AND** system exits with code 0

