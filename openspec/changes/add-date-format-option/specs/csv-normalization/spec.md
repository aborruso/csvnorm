## ADDED Requirements

### Requirement: Date format hint for normalization
The system SHALL accept `--date-format` and pass its value as DuckDB `read_csv` `dateformat` during normalization only.

#### Scenario: Normalize local file with date format hint
- **WHEN** a user runs `csvnorm data.csv --date-format "%d/%m/%Y" -o out.csv`
- **THEN** normalization uses DuckDB `read_csv(..., dateformat='%d/%m/%Y')`
- **AND THEN** validation does not use the date format hint

#### Scenario: Normalize remote URL with date format hint
- **WHEN** a user runs `csvnorm https://example.com/data.csv --date-format "%m/%d/%Y" -o out.csv`
- **THEN** normalization uses DuckDB `read_csv(..., dateformat='%m/%d/%Y')`
