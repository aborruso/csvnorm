# mojibake-repair Specification

## Purpose
TBD - created by archiving change add-mojibake-repair-ftfy. Update Purpose after archive.
## Requirements
### Requirement: Optional mojibake repair using ftfy
The system SHALL offer an opt-in mojibake repair step using `ftfy`.

#### Scenario: Repair applied when mojibake detected
- **WHEN** the user enables mojibake repair
- **AND** the input is a local file (or a remote URL downloaded to a local temp file)
- **AND** `ftfy.badness.is_bad()` returns true on a sample of the decoded text
- **THEN** the system applies `ftfy` repair to the file contents
- **AND** processing continues using the repaired content

#### Scenario: Repair skipped when text is clean
- **WHEN** the user enables mojibake repair
- **AND** the input is a local file (or a remote URL downloaded to a local temp file)
- **AND** `ftfy.badness.is_bad()` returns false on the sample
- **THEN** the system does not alter the content

#### Scenario: Repair disabled by default
- **WHEN** the user does not enable mojibake repair
- **THEN** the system does not run mojibake detection or repair

#### Scenario: Remote URLs download before repair
- **WHEN** the user enables mojibake repair
- **AND** the input is a remote URL
- **THEN** the system downloads the remote file to a system temp location
- **AND** the system runs mojibake detection and repair on the local copy

#### Scenario: Sample size override
- **WHEN** the user passes a numeric argument to `--fix-mojibake`
- **THEN** the system uses that value as the sample size for mojibake detection

