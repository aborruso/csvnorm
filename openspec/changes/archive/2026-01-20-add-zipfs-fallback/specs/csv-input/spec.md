## ADDED Requirements
### Requirement: Fallback when zipfs extension is unavailable
The system SHALL fallback to local ZIP extraction when the input is a local ZIP file and DuckDB cannot load the zipfs extension.

#### Scenario: Zipfs extension missing for downloaded ZIP
- **WHEN** the input is a local ZIP file (including a remote ZIP downloaded with `--download-remote`)
- **AND** DuckDB cannot load the zipfs extension
- **THEN** the system extracts the ZIP locally and processes the single CSV inside

#### Scenario: ZIP contains multiple CSV files
- **WHEN** the ZIP contains more than one CSV file
- **THEN** the system stops and reports that the user must extract the desired file and run csvnorm on it
