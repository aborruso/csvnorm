## ADDED Requirements
### Requirement: Download remote input when range requests are unsupported

The system SHALL provide an explicit CLI flag to download remote CSVs locally when the remote server does not support HTTP range requests.

#### Scenario: Remote server lacks range support and flag is provided
- **WHEN** user runs `csvnorm https://example.com/data.csv --download-remote`
- **AND** the remote server does not support HTTP range requests
- **THEN** the system downloads the file to a temporary local path
- **AND** continues processing using the local file
- **AND** cleans up the temporary download after completion

#### Scenario: Remote server lacks range support and flag is not provided
- **WHEN** user runs `csvnorm https://example.com/data.csv`
- **AND** the remote server does not support HTTP range requests
- **THEN** the system shows the existing error panel explaining the limitation
- **AND** exits with code 1

#### Scenario: Remote server supports range requests
- **WHEN** user runs `csvnorm https://example.com/data.csv --download-remote`
- **AND** the remote server supports HTTP range requests
- **THEN** the system processes the remote URL without downloading it
