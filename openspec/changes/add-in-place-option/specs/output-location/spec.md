## ADDED Requirements

### Requirement: In-place output mode
The system SHALL support `--in-place` to overwrite the input file after successful processing, using a temporary file for atomic replacement.

#### Scenario: In-place processing for local file
- **WHEN** a user runs `csvnorm data.csv --in-place`
- **THEN** the output is written to a temporary file in the system temp directory
- **AND THEN** the input file `data.csv` is replaced by the normalized output
- **AND THEN** the temporary file is removed after completion

#### Scenario: Reject file location for in-place
- **WHEN** a user runs `csvnorm data.csv --in-place`
- **AND WHEN** validation errors occur
- **THEN** a reject file is created as `{input_dir}/{input_stem}_reject_errors.csv`

#### Scenario: In-place disallows output path
- **WHEN** a user runs `csvnorm data.csv --in-place -o out.csv`
- **THEN** the command fails with a message indicating the options are mutually exclusive

#### Scenario: In-place disallows remote URLs
- **WHEN** a user runs `csvnorm https://example.com/data.csv --in-place`
- **THEN** the command fails with a message indicating in-place requires a local file

## MODIFIED Requirements

### Requirement: Existing output file blocks without force
The system SHALL stop and warn the user when the output file path already exists, unless `--force` is provided, except when using `--in-place` which always overwrites the input file on success.

#### Scenario: Output exists without force
- **WHEN** the output file path specified by `-o` already exists
- **AND WHEN** `--force` is not provided
- **THEN** the command exits without writing any output
- **AND THEN** the user is warned that the output file already exists

#### Scenario: Output exists with force
- **WHEN** the output file path specified by `-o` already exists
- **AND WHEN** `--force` is provided
- **THEN** the output file is overwritten

#### Scenario: In-place overwrites input without force
- **WHEN** a user runs `csvnorm data.csv --in-place`
- **THEN** the input file is overwritten after successful processing
- **AND THEN** no `--force` flag is required
