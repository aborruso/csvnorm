## MODIFIED Requirements
### Requirement: Skip encoding operations for remote URLs

The system SHALL download remote URLs to a local temporary file and process them through the standard local-file pipeline, including encoding detection and conversion.

#### Scenario: Remote URL triggers download and encoding detection
- **WHEN** processing a remote HTTP/HTTPS URL
- **THEN** the system downloads the file to a temporary local path
- **AND** encoding detection is performed on the local file
- **AND** conversion to UTF-8 occurs when needed
- **AND** DuckDB reads the local file path (not the URL)

## MODIFIED Requirements
### Requirement: Download remote input when download flag is provided

The system SHALL download remote HTTP/HTTPS inputs to a local temporary file before processing, regardless of whether `--download-remote` is provided.

#### Scenario: Flag is provided
- **WHEN** user runs `csvnorm https://example.com/data.csv --download-remote`
- **THEN** the system downloads the file to a temporary local path
- **AND** continues processing using the local file
- **AND** cleans up the temporary download after completion

#### Scenario: Flag is not provided
- **WHEN** user runs `csvnorm https://example.com/data.csv`
- **THEN** the system downloads the file to a temporary local path
- **AND** continues processing using the local file
- **AND** cleans up the temporary download after completion
