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

### Requirement: Temp files in system directory

The system SHALL create UTF-8 conversion temporary files in a system temp directory with auto-cleanup. Reject files SHALL be placed in the output directory for file mode, or in the current working directory for stdout mode.

#### Scenario: Temp UTF8 file in system temp

- **WHEN** encoding conversion is required
- **THEN** a temp UTF-8 file is created in system temp directory (e.g., `/tmp/csvnorm_xxxxx/`)
- **AND THEN** the temp directory is automatically cleaned up after processing

#### Scenario: Reject file in output directory (file mode)

- **WHEN** validation errors occur during processing with `-o` specified
- **THEN** a reject file is created as `{output_dir}/{output_stem}_reject_errors.csv`
- **AND THEN** if an existing reject file exists, it is overwritten without warning
- **AND THEN** if empty (only header), the reject file is removed after processing

#### Scenario: Reject file in current directory (stdout mode)

- **WHEN** validation errors occur during processing without `-o` (stdout mode)
- **THEN** a reject file is created as `./reject_errors.csv` in the current working directory
- **AND THEN** if an existing reject file exists, it is overwritten without warning
- **AND THEN** if empty (only header), the reject file is removed after processing
- **AND THEN** the reject file persists after processing (not in temp directory)

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

