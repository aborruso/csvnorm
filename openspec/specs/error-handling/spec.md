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

### Requirement: Disk full is reported and never leaves a partial output
The system SHALL report a full disk during UTF-8 conversion, normalization or reject export with the panel "No space left on device" and exit code 1, SHALL remove its temporary files, and SHALL leave the input and any existing output file unchanged. Before processing, the system SHALL warn without stopping when free space looks insufficient.

#### Scenario: Disk fills during normalization with an existing output
- **WHEN** the user runs `csvnorm input.csv -o output.csv --force` and the disk fills during normalization
- **THEN** a low-disk-space warning was shown before processing
- **AND** the panel "No space left on device" is shown and the exit code is 1
- **AND** the existing `output.csv` is unchanged and no partial file remains

