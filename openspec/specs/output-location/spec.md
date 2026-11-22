## Purpose
Define how csvnorm chooses output locations, handles default output, and manages reject and temp files.
## Requirements
### Requirement: Output file path specification
The system SHALL write output to the exact path specified by `-o/--output-file`, supporting both absolute and relative paths. When no output path is provided, the system SHALL write output to stdout.

#### Scenario: Absolute path output
- **WHEN** a user runs `csvnorm data.csv -o /tmp/output.csv`
- **THEN** the output CSV is created at `/tmp/output.csv`
- **AND THEN** reject/temp files are placed in `/tmp/`

#### Scenario: Relative path output
- **WHEN** a user runs `csvnorm data.csv -o ../processed/data.csv`
- **THEN** the output CSV is created at `../processed/data.csv`
- **AND THEN** reject/temp files are placed in `../processed/`

#### Scenario: Default output location
- **WHEN** a user runs `csvnorm data.csv` without `-o`
- **THEN** the output CSV is written to stdout
- **AND THEN** no output file is created on disk

#### Scenario: Custom output filename and extension
- **WHEN** a user runs `csvnorm data.csv -o processed/output.txt`
- **THEN** the output file is created at `processed/output.txt`
- **AND THEN** no validation is performed on the file extension

### Requirement: Existing output file blocks without force
The system SHALL stop and warn the user when the output file path already exists, unless `--force` is provided.

#### Scenario: Output exists without force
- **WHEN** the output file path specified by `-o` already exists
- **AND WHEN** `--force` is not provided
- **THEN** the command exits without writing any output
- **AND THEN** the user is warned that the output file already exists

#### Scenario: Output exists with force
- **WHEN** the output file path specified by `-o` already exists
- **AND WHEN** `--force` is provided
- **THEN** the output file is overwritten

### Requirement: Temp and reject file locations

The system SHALL create UTF-8 conversion temporary files in a system temp directory with auto-cleanup. Reject files SHALL be placed in the output directory for file mode, or in the system temp directory with a unique name for stdout mode.

#### Scenario: Temp UTF8 file in system temp

- **WHEN** encoding conversion is required
- **THEN** a temp UTF-8 file is created in system temp directory (e.g., `/tmp/csvnorm_xxxxx/`)
- **AND THEN** the temp directory is automatically cleaned up after processing

#### Scenario: Reject file in output directory (file mode)

- **WHEN** validation errors occur during processing with `-o` specified
- **THEN** a reject file is created as `{output_dir}/{output_stem}_reject_errors.csv`
- **AND THEN** if an existing reject file exists, it is overwritten without warning
- **AND THEN** if empty (only header), the reject file is removed after processing

#### Scenario: Reject file in system temp directory (stdout mode)

- **WHEN** validation errors occur during processing without `-o` (stdout mode)
- **THEN** a reject file is created in the system temp directory as `csvnorm_reject_errors_<id>.csv`, with a name unique to the run
- **AND THEN** its full path is printed on stderr
- **AND THEN** no file is created in the current working directory
- **AND THEN** if empty (only header), the reject file is removed after processing
- **AND THEN** otherwise the reject file persists after processing

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

