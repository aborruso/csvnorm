# output-location Specification

## Purpose
TBD - created by archiving change update-default-output-dir. Update Purpose after archive.
## Requirements
### Requirement: Default output directory uses current working directory
The system SHALL write output files to the current working directory when `--output-dir` is not provided.

#### Scenario: No output directory specified
- **WHEN** a user runs `csvnormr` without `--output-dir`
- **THEN** the output CSV is created in the process working directory
- **AND THEN** temporary files (`reject_errors.csv`, `*_utf8.csv`) are created in the same directory

### Requirement: Existing output file blocks without force
The system SHALL stop and warn the user when the output CSV already exists, unless `--force` is provided.

#### Scenario: Output exists without force
- **WHEN** the output CSV path already exists
- **AND WHEN** `--force` is not provided
- **THEN** the command exits without writing any output
- **AND THEN** the user is warned that the output file already exists

#### Scenario: Output exists with force
- **WHEN** the output CSV path already exists
- **AND WHEN** `--force` is provided
- **THEN** the output CSV is overwritten

