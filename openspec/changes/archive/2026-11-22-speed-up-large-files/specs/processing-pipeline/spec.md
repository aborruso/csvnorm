## ADDED Requirements

### Requirement: Keyword prefix removal works with any output delimiter
When header normalization is enabled, the system SHALL remove the `_` prefix that DuckDB adds to column names that are SQL keywords, for every output delimiter, and SHALL keep user columns that start with `_` unchanged.

#### Scenario: Semicolon delimiter
- **WHEN** the input header is `select,_id` and the user runs `csvnorm input.csv -d ';' -o out.csv`
- **THEN** the output header is `select;_id`
