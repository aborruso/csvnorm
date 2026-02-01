## MODIFIED Requirements

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
