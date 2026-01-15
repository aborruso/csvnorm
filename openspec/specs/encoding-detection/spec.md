# encoding-detection Specification

## Purpose
TBD - created by archiving change update-encoding-detector. Update Purpose after archive.
## Requirements
### Requirement: Primary encoding detection uses charset_normalizer
The system SHALL detect input CSV encoding using `charset_normalizer` as the primary detector and use `file -b --mime-encoding` as a fallback when the primary detector fails or yields no usable encoding.

#### Scenario: Primary detector succeeds
- **WHEN** `charset_normalizer` returns a usable encoding label
- **THEN** the system uses that label for subsequent conversion logic

#### Scenario: Primary detector fails
- **WHEN** `charset_normalizer` exits non-zero or returns no usable encoding label
- **THEN** the system falls back to `file -b --mime-encoding`

