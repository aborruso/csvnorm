# csv-input Specification

## Purpose
TBD - created by archiving change add-remote-url-support. Update Purpose after archive.
## Requirements
### Requirement: Accept HTTP/HTTPS URLs as input

The system SHALL accept HTTP and HTTPS URLs in addition to local file paths as the `input_file` argument.

#### Scenario: User provides HTTP URL

- **WHEN** user runs `csvnorm https://example.com/data.csv`
- **THEN** the system detects it as a remote URL and processes it

#### Scenario: User provides HTTPS URL

- **WHEN** user runs `csvnorm https://example.com/data.csv`
- **THEN** the system detects it as a remote URL and processes it

#### Scenario: User provides local file path

- **WHEN** user runs `csvnorm ./data.csv`
- **THEN** the system detects it as a local file and processes it with existing logic

### Requirement: Validate URL format

The system SHALL validate that URLs use HTTP or HTTPS protocols and reject other protocols.

#### Scenario: Valid HTTP URL

- **WHEN** user provides `http://example.com/data.csv`
- **THEN** validation passes and processing continues

#### Scenario: Invalid protocol

- **WHEN** user provides `ftp://example.com/data.csv` or `file:///path/to/file`
- **THEN** system shows error message and exits with code 1

### Requirement: Skip encoding operations for remote URLs

The system SHALL skip encoding detection and conversion when processing remote URLs, delegating character handling to DuckDB.

#### Scenario: Remote URL skips encoding detection

- **WHEN** processing a remote URL
- **THEN** encoding detection step is skipped
- **AND** no temporary UTF-8 conversion file is created
- **AND** progress indicator shows "Remote URL (encoding handled by DuckDB)"

### Requirement: Generate output filename from URL

The system SHALL derive the output filename from the URL path's last segment, applying snake_case normalization.

#### Scenario: URL with filename

- **WHEN** input is `https://example.com/path/My_Data_File.csv`
- **THEN** output filename is `my_data_file.csv`

#### Scenario: URL without extension

- **WHEN** input is `https://example.com/data`
- **THEN** output filename is `data.csv` (append .csv extension)

#### Scenario: URL with query parameters

- **WHEN** input is `https://example.com/data.csv?format=csv&version=2`
- **THEN** query parameters are stripped and output filename is `data.csv`

### Requirement: Apply fixed timeout for remote requests

The system SHALL configure DuckDB with a 30-second HTTP timeout for remote CSV requests.

#### Scenario: Remote file loads within timeout

- **WHEN** remote CSV responds within 30 seconds
- **THEN** processing succeeds normally

#### Scenario: Remote file exceeds timeout

- **WHEN** remote CSV doesn't respond within 30 seconds
- **THEN** DuckDB raises timeout error
- **AND** system shows error panel with timeout message
- **AND** exits with code 1

### Requirement: Public URLs only

The system SHALL support only publicly accessible URLs without authentication.

#### Scenario: Public URL works

- **WHEN** user provides public URL without auth requirements
- **THEN** DuckDB reads the file successfully

#### Scenario: Auth-protected URL fails gracefully

- **WHEN** URL requires authentication (returns 401/403)
- **THEN** DuckDB fails with HTTP error
- **AND** system shows error panel explaining authentication not supported

