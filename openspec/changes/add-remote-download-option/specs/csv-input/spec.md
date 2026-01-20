## ADDED Requirements
### Requirement: Download remote input when download flag is provided

The system SHALL provide an explicit CLI flag to download remote CSVs locally before processing.

#### Scenario: Flag is provided
- **WHEN** user runs `csvnorm https://example.com/data.csv --download-remote`
- **THEN** the system downloads the file to a temporary local path
- **AND** continues processing using the local file
- **AND** cleans up the temporary download after completion

#### Scenario: Download encounters TLS/SSL handshake failure with flag provided
- **WHEN** user runs `csvnorm https://example.com/data.csv --download-remote`
- **AND** the initial download attempt fails with a TLS/SSL handshake error
- **THEN** the system retries the download using a compatibility fallback
- **AND** continues processing using the downloaded local file
- **AND** cleans up the temporary download after completion

#### Scenario: Remote server lacks range support and flag is not provided
- **WHEN** user runs `csvnorm https://example.com/data.csv`
- **AND** the remote server does not support HTTP range requests
- **THEN** the system shows the existing error panel explaining the limitation
- **AND** exits with code 1

#### Scenario: Flag is not provided and range is supported
- **WHEN** user runs `csvnorm https://example.com/data.csv`
- **AND** the remote server supports HTTP range requests
- **THEN** the system processes the remote URL without downloading it
