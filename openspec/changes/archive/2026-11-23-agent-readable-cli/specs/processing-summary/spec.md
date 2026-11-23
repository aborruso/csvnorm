## MODIFIED Requirements

### Requirement: Display error summary when validation fails

The system SHALL display a validation error summary to stderr BEFORE writing output data, ensuring visibility even in piped scenarios. On a terminal it is a panel with a yellow border; otherwise it is plain lines.

#### Scenario: Validation errors in file mode

- **WHEN** DuckDB encounters invalid rows in file mode (`-o` specified)
- **THEN** validation completes first
- **AND** error panel is displayed to stderr with:
  - Number of rejected rows
  - Up to 3 sample error types/reasons from reject file
  - Path to reject_errors.csv file
  - Yellow border on a terminal, plain lines otherwise
- **AND** normalization proceeds and writes to output file
- **AND** success summary table is displayed afterward
- **AND** system exits with code 1

#### Scenario: Validation errors in stdout mode

- **WHEN** DuckDB encounters invalid rows in stdout mode (no `-o`)
- **THEN** validation completes first
- **AND** error panel is displayed to stderr BEFORE any output data
- **AND** normalization proceeds and writes to stdout
- **AND** brief success summary is shown to stderr afterward
- **AND** system exits with code 1 (with `--strict` nothing is written, still exit code 1)

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
