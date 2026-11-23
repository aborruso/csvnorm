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
The system SHALL report a full disk during UTF-8 conversion, normalization or reject export with the message "No space left on device" and exit code 2, SHALL remove its temporary files, and SHALL leave the input and any existing output file unchanged. Before processing, the system SHALL warn without stopping when free space looks insufficient.

#### Scenario: Disk fills during normalization with an existing output
- **WHEN** the user runs `csvnorm input.csv -o output.csv --force` and the disk fills during normalization
- **THEN** a low-disk-space warning was shown before processing
- **AND** the message "No space left on device" is shown and the exit code is 2
- **AND** the existing `output.csv` is unchanged and no partial file remains

### Requirement: Exit codes distinguish rejected rows from runs that could not complete
The system SHALL exit with 0 when every row is accepted, with 1 when rows are rejected (the accepted rows are still written unless `--strict`), and with 2 when it could not complete: invalid command line, missing input, download failure, undetectable or undecodable encoding, disk full, or an unexpected error. With exit code 2 no output is written. An unexpected exception SHALL be reported as one `Error:` line with exit code 2, with the full traceback only with `-V`.

#### Scenario: Missing input file
- **WHEN** the user runs `csvnorm missing.csv`
- **THEN** stderr starts with `Error: Input file not found` and suggests checking the path or using `-`
- **AND** the exit code is 2 and stdout is empty

#### Scenario: Rejected rows
- **WHEN** the user runs `csvnorm malformed.csv -o out.csv` and some rows are rejected
- **THEN** `out.csv` holds the accepted rows
- **AND** the exit code is 1

#### Scenario: Unexpected exception
- **WHEN** processing raises an exception that csvnorm does not handle
- **THEN** stderr shows `Error: unexpected failure: <type>: <message>` and suggests `-V`
- **AND** the exit code is 2, not Python's 1

### Requirement: Messages are plain text when stderr is not a terminal
The system SHALL print errors, warnings and the validation report inside panels only when the target stream is a terminal. Otherwise it SHALL print them as plain lines, starting with `Error:`, `Warning:` or `! Validation Failed`, with no box-drawing characters and no escape codes.

#### Scenario: Error in a pipe
- **WHEN** the user runs `csvnorm missing.csv 2> err.txt`
- **THEN** `err.txt` contains no box-drawing characters and no escape codes
- **AND** its first non-empty line starts with `Error:`

### Requirement: Help and version are usable without a terminal
The system SHALL provide a `--help` that works offline and without prompts, and that states what csvnorm does and does not do, a first path of three real commands, where the output, the summary and the reject file go, the exit codes, the limits and side effects (URL download, temporary space, sampled detection above 50 MiB, `-O`), and where to find valid encoding names online and offline. Redirected to a file it SHALL contain no escape codes and no truncated lists. `--version` SHALL print one line `csvnorm X.Y.Z` when stdout is not a terminal.

#### Scenario: Help redirected to a file
- **WHEN** the user runs `csvnorm --help > help.txt`
- **THEN** `help.txt` contains the sections Start here, Output, Exit codes, Limits and side effects
- **AND** it contains no escape codes

#### Scenario: Version in a pipe
- **WHEN** the user runs `csvnorm --version | cat`
- **THEN** the output is the single line `csvnorm X.Y.Z`

