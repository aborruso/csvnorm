## MODIFIED Requirements
### Requirement: Display encoding conversion status

The system SHALL display whether encoding conversion occurred during processing and, when enabled, whether mojibake repair was applied.

#### Scenario: Encoding was converted

- **WHEN** input file required UTF-8 conversion (e.g., WINDOWS-1252 → UTF-8)
- **THEN** success summary shows "Encoding: WINDOWS-1252 → UTF-8 (converted)"

#### Scenario: No encoding conversion needed

- **WHEN** input file is already UTF-8 or ASCII
- **THEN** success summary shows "Encoding: UTF-8 (no conversion needed)"

#### Scenario: Mojibake repair applied

- **WHEN** the user enables mojibake repair
- **AND** the system applies a repair
- **THEN** success summary includes a note such as "Mojibake: repaired (ftfy)"

#### Scenario: Remote URL processing

- **WHEN** processing a remote URL
- **THEN** success summary does not show encoding info (not available for remote files)
- **AND** no mojibake repair status is shown
