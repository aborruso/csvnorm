## ADDED Requirements

### Requirement: Disk full is reported and never leaves a partial output
The system SHALL report a full disk during UTF-8 conversion, normalization or reject export with the panel "No space left on device" and exit code 1, SHALL remove its temporary files, and SHALL leave the input and any existing output file unchanged. Before processing, the system SHALL warn without stopping when free space looks insufficient.

#### Scenario: Disk fills during normalization with an existing output
- **WHEN** the user runs `csvnorm input.csv -o output.csv --force` and the disk fills during normalization
- **THEN** a low-disk-space warning was shown before processing
- **AND** the panel "No space left on device" is shown and the exit code is 1
- **AND** the existing `output.csv` is unchanged and no partial file remains
