## ADDED Requirements

### Requirement: Check-only validation mode

The system SHALL provide a `--check` flag that validates the CSV file without processing or normalizing it.

#### Scenario: Valid CSV with check mode

- **WHEN** user runs `csvnorm data.csv --check` on a valid CSV file
- **THEN** system validates the file structure
- **AND** outputs "✓ Valid CSV" to stderr
- **AND** exits with code 0
- **AND** no output file is created
- **AND** no encoding conversion is performed

#### Scenario: Invalid CSV with check mode

- **WHEN** user runs `csvnorm data.csv --check` on a CSV with validation errors
- **THEN** system validates the file structure
- **AND** outputs "✗ Invalid CSV: N rows rejected" to stderr
- **AND** outputs brief error summary to stderr
- **AND** exits with code 1
- **AND** no output file is created

#### Scenario: Check mode with remote URL

- **WHEN** user runs `csvnorm https://example.com/data.csv --check`
- **THEN** system validates the remote CSV
- **AND** outputs validation status to stderr
- **AND** exits with appropriate code (0=valid, 1=invalid)

#### Scenario: Check mode skips normalization

- **WHEN** user runs `csvnorm data.csv --check`
- **THEN** system performs only validation step
- **AND** skips encoding conversion (unless needed for validation)
- **AND** skips mojibake repair
- **AND** skips normalization
- **AND** skips output writing

#### Scenario: Check mode incompatible with output options

- **WHEN** user runs `csvnorm data.csv --check -o output.csv`
- **THEN** system shows error message: "--check cannot be used with -o (output file)"
- **AND** exits with code 1

#### Scenario: Check mode incompatible with strict mode

- **WHEN** user runs `csvnorm data.csv --check --strict`
- **THEN** system shows warning: "--strict is redundant with --check (both exit on errors)"
- **AND** proceeds with check mode
- **AND** exits with code 1 if errors found
