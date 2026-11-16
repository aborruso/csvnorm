## MODIFIED Requirements

### Requirement: Temp files in system directory

The system SHALL create UTF-8 conversion temporary files in a system temp directory with auto-cleanup. Reject files SHALL be placed in the output directory for file mode, or in the system temp directory with a unique name for stdout mode.

#### Scenario: Temp UTF8 file in system temp

- **WHEN** encoding conversion is required
- **THEN** a temp UTF-8 file is created in system temp directory (e.g., `/tmp/csvnorm_xxxxx/`)
- **AND THEN** the temp directory is automatically cleaned up after processing

#### Scenario: Reject file in output directory (file mode)

- **WHEN** validation errors occur during processing with `-o` specified
- **THEN** a reject file is created as `{output_dir}/{output_stem}_reject_errors.csv`
- **AND THEN** if an existing reject file exists, it is overwritten without warning
- **AND THEN** if empty (only header), the reject file is removed after processing

#### Scenario: Reject file in system temp directory (stdout mode)

- **WHEN** validation errors occur during processing without `-o` (stdout mode)
- **THEN** a reject file is created in the system temp directory as `csvnorm_reject_errors_<id>.csv`, with a name unique to the run
- **AND THEN** its full path is printed on stderr
- **AND THEN** no file is created in the current working directory
- **AND THEN** if empty (only header), the reject file is removed after processing
- **AND THEN** otherwise the reject file persists after processing
