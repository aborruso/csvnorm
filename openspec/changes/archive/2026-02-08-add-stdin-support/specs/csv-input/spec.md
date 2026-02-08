## ADDED Requirements

### Requirement: Accept stdin as input via dash argument

The system SHALL accept `-` as the `input_file` argument to read CSV data from standard input.

#### Scenario: Pipe data via stdin

- **WHEN** user runs `cat data.csv | csvnorm -`
- **THEN** the system reads binary data from stdin
- **AND** saves it to a temporary file
- **AND** processes it as a local CSV file
- **AND** cleans up the temporary file after completion

#### Scenario: Stdin with file output

- **WHEN** user runs `cat data.csv | csvnorm - -o output.csv`
- **THEN** the system reads stdin and writes normalized output to the specified file

#### Scenario: Stdin with check mode

- **WHEN** user runs `cat data.csv | csvnorm - --check`
- **THEN** the system validates the piped CSV and exits with appropriate code

#### Scenario: Stdin with non-UTF-8 encoding

- **WHEN** user pipes a non-UTF-8 CSV via `csvnorm -`
- **THEN** the system detects the encoding and converts to UTF-8 as for local files

#### Scenario: No piped data (terminal stdin)

- **WHEN** user runs `csvnorm -` without piping data (stdin is a terminal)
- **THEN** the system shows an error message
- **AND** exits with code 1
