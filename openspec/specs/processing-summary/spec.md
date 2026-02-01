# processing-summary Specification

## Purpose
TBD - created by archiving change add-processing-summary. Update Purpose after archive.
## Requirements
### Requirement: Display encoding conversion status

The system SHALL display whether encoding conversion occurred during processing and, when enabled, whether mojibake repair was applied.

#### Scenario: Encoding was converted

- **WHEN** input file required UTF-8 conversion (e.g., WINDOWS-1252 → UTF-8)
- **THEN** success summary shows "Encoding: WINDOWS-1252 → UTF-8 (converted)"

#### Scenario: No encoding conversion needed

- **WHEN** input file is already UTF-8 or ASCII
- **THEN** success summary shows "Encoding: UTF-8 (no conversion needed)"

#### Scenario: Mojibake repair applied

- **WHEN** the user enables mojibake repair
- **AND** the system applies a repair
- **THEN** success summary includes a note such as "Mojibake: repaired (ftfy)"

#### Scenario: Remote URL processing

- **WHEN** processing a remote URL
- **THEN** success summary does not show encoding info (not available for remote files)
- **AND** no mojibake repair status is shown

### Requirement: Display processing statistics

The system SHALL display statistics about the processed file in the success summary.

#### Scenario: Success with statistics

- **WHEN** processing completes successfully
- **THEN** success summary shows:
  - Number of rows processed
  - Number of columns
  - Input file size (formatted as KB/MB/GB) - only for local files
  - Output file size (formatted as KB/MB/GB)

### Requirement: Display error summary when validation fails

The system SHALL display a validation error summary panel to stderr BEFORE writing output data, ensuring visibility even in piped scenarios.

#### Scenario: Validation errors in file mode

- **WHEN** DuckDB encounters invalid rows in file mode (`-o` specified)
- **THEN** validation completes first
- **AND** error panel is displayed to stderr with:
  - Number of rejected rows
  - Up to 3 sample error types/reasons from reject file
  - Path to reject_errors.csv file
  - Yellow border for visibility
- **AND** normalization proceeds and writes to output file
- **AND** success summary table is displayed afterward
- **AND** system exits with code 0

#### Scenario: Validation errors in stdout mode

- **WHEN** DuckDB encounters invalid rows in stdout mode (no `-o`)
- **THEN** validation completes first
- **AND** error panel is displayed to stderr BEFORE any output data
- **AND** normalization proceeds and writes to stdout
- **AND** brief success summary is shown to stderr afterward
- **AND** system exits with code 0 (unless `--strict` enabled)

#### Scenario: Validation errors with strict mode

- **WHEN** DuckDB encounters invalid rows
- **AND** `--strict` flag is enabled
- **THEN** error panel is displayed to stderr
- **AND** no normalization occurs
- **AND** no output is written
- **AND** system exits with code 1

#### Scenario: No validation errors

- **WHEN** validation passes with zero rejected rows
- **THEN** no error panel is displayed
- **AND** normalization proceeds immediately
- **AND** success summary is shown (format depends on stdout vs file mode)

### Requirement: Show output file location in summary

The system SHALL always display the output file path in the processing summary.

#### Scenario: Successful processing

- **WHEN** processing completes successfully
- **THEN** success summary shows "Output: <full_path_to_output_file>"

#### Scenario: Remote URL processing

- **WHEN** processing a remote URL
- **THEN** success summary shows the local output file path (not the URL)

