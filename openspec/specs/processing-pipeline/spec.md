# processing-pipeline Specification

## Purpose
TBD - created by archiving change refactor-core-process-csv. Update Purpose after archive.
## Requirements
### Requirement: Core processing pipeline is decomposed into helper steps

The system SHALL implement the CSV processing pipeline using internal helper functions for each major step to improve testability and maintainability.

#### Scenario: Orchestration remains centralized
- **WHEN** `process_csv` runs
- **THEN** it delegates encoding detection/conversion, optional mojibake repair, validation, normalization, and cleanup to helper functions
- **AND** its external behavior and return codes remain unchanged

### Requirement: Keyword prefix removal works with any output delimiter
When header normalization is enabled, the system SHALL remove the `_` prefix that DuckDB adds to column names that are SQL keywords, for every output delimiter, and SHALL keep user columns that start with `_` unchanged.

#### Scenario: Semicolon delimiter
- **WHEN** the input header is `select,_id` and the user runs `csvnorm input.csv -d ';' -o out.csv`
- **THEN** the output header is `select;_id`

