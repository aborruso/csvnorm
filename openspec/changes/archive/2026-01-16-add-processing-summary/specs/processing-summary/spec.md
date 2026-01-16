## ADDED Requirements

### Requirement: Display encoding conversion status

The system SHALL display whether encoding conversion occurred during processing.

#### Scenario: Encoding was converted

- **WHEN** input file required UTF-8 conversion (e.g., WINDOWS-1252 → UTF-8)
- **THEN** success summary shows "Encoding: WINDOWS-1252 → UTF-8 (converted)"

#### Scenario: No encoding conversion needed

- **WHEN** input file is already UTF-8 or ASCII
- **THEN** success summary shows "Encoding: UTF-8 (no conversion needed)"

#### Scenario: Remote URL processing

- **WHEN** processing a remote URL
- **THEN** success summary shows "Encoding: remote (handled by DuckDB)"

### Requirement: Display processing statistics

The system SHALL display statistics about the processed file in the success summary.

#### Scenario: Success with statistics

- **WHEN** processing completes successfully
- **THEN** success summary shows:
  - Number of rows processed
  - Number of columns
  - Input file size (formatted as KB/MB/GB)
  - Output file size (formatted as KB/MB/GB)

### Requirement: Display error summary when validation fails

The system SHALL display a summary panel showing validation error details when rejected rows exist, alongside the success summary.

#### Scenario: Validation errors with reject file

- **WHEN** DuckDB encounters invalid rows
- **THEN** success summary table is displayed with output file info
- **AND** error panel is displayed with:
  - Number of rejected rows
  - Up to 3 sample error types/reasons from reject file
  - Path to reject_errors.csv file
  - Yellow border for visibility
- **AND** system exits with code 1

#### Scenario: No validation errors

- **WHEN** validation passes with zero rejected rows
- **THEN** no error panel is displayed
- **AND** only success summary table is shown

### Requirement: Show output file location in summary

The system SHALL always display the output file path in the processing summary.

#### Scenario: Successful processing

- **WHEN** processing completes successfully
- **THEN** success summary shows "Output: <full_path_to_output_file>"

#### Scenario: Remote URL processing

- **WHEN** processing a remote URL
- **THEN** success summary shows the local output file path (not the URL)
