## ADDED Requirements
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
