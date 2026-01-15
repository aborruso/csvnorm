## ADDED Requirements
### Requirement: CSV columns default to VARCHAR
The system SHALL read input CSV files with all columns typed as VARCHAR during DuckDB validation and normalization to avoid inference-driven type errors.

#### Scenario: Validation reads CSV
- **WHEN** the validation step reads the input CSV with DuckDB
- **THEN** all columns are treated as VARCHAR

#### Scenario: Normalization reads CSV
- **WHEN** the normalization step reads the input CSV with DuckDB
- **THEN** all columns are treated as VARCHAR and field values are not coerced
