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

### Requirement: Fallback when zipfs extension is unavailable
The system SHALL fallback to local ZIP extraction when the input is a local ZIP file and DuckDB cannot load the zipfs extension.

#### Scenario: Zipfs extension missing for downloaded ZIP
- **WHEN** the input is a local ZIP file (including a remote ZIP downloaded with `--download-remote`)
- **AND** DuckDB cannot load the zipfs extension
- **THEN** the system extracts the ZIP locally and processes the single CSV inside

#### Scenario: ZIP contains multiple CSV files
- **WHEN** the ZIP contains more than one CSV file
- **THEN** the system stops and reports that the user must extract the desired file and run csvnorm on it

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

### Requirement: Accept gzip-compressed CSV inputs
The system SHALL accept gzip-compressed CSV inputs (e.g., `.csv.gz`) and process them without requiring manual decompression.

#### Scenario: Gzip file input
- **WHEN** user runs `csvnorm ./data.csv.gz`
- **THEN** the system reads the file with DuckDB's CSV compression autodetect
- **AND** produces normalized output as for uncompressed inputs

### Requirement: Accept zip-compressed CSV inputs with a single CSV entry
The system SHALL accept zip archives that contain exactly one CSV entry and process that entry without manual extraction.

#### Scenario: Zip file with one CSV
- **WHEN** user runs `csvnorm ./data.zip` and the zip contains exactly one `.csv`
- **THEN** the system reads the CSV via a `zip://` path
- **AND** produces normalized output as for uncompressed inputs

#### Scenario: Zip file with multiple CSVs
- **WHEN** user runs `csvnorm ./data.zip` and the zip contains more than one `.csv`
- **THEN** the system fails with a clear error listing the CSV entries
- **AND** exits with code 1

#### Scenario: Zip file with no CSVs
- **WHEN** user runs `csvnorm ./data.zip` and the zip contains no `.csv`
- **THEN** the system fails with a clear error
- **AND** exits with code 1

### Requirement: Auto-install and load DuckDB zipfs extension for zip inputs
The system SHALL automatically install and load DuckDB's `zipfs` extension when a zip input is detected.

#### Scenario: Zip input loads zipfs extension
- **WHEN** user runs `csvnorm ./data.zip`
- **THEN** the system installs and loads `zipfs` if not already available
- **AND** proceeds to read the CSV entry

