## ADDED Requirements
### Requirement: Flag to keep original column names
The system SHALL provide a `--keep-names` flag that preserves input column names and disables snake_case normalization of headers.

#### Scenario: Keep names enabled
- **WHEN** the user runs the tool with `--keep-names`
- **THEN** output headers match the input headers (no snake_case conversion)

#### Scenario: Keep names default
- **WHEN** the user runs the tool without `--keep-names`
- **THEN** output headers are normalized to snake_case

### Requirement: Removal of --no-normalize
The system SHALL NOT accept the `--no-normalize` option.

#### Scenario: Legacy flag is used
- **WHEN** the user runs the tool with `--no-normalize`
- **THEN** the tool fails with an unknown option error
