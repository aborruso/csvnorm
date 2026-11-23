## MODIFIED Requirements

### Requirement: Validate URL format

The system SHALL validate that URLs use HTTP or HTTPS protocols and reject other protocols.

#### Scenario: Valid HTTP URL

- **WHEN** user provides `http://example.com/data.csv`
- **THEN** validation passes and processing continues

#### Scenario: Invalid protocol

- **WHEN** user provides `ftp://example.com/data.csv` or `file:///path/to/file`
- **THEN** system shows error message and exits with code 2

### Requirement: Apply fixed timeout for remote requests

The system SHALL configure DuckDB with a 30-second HTTP timeout for remote CSV requests.

#### Scenario: Remote file loads within timeout

- **WHEN** remote CSV responds within 30 seconds
- **THEN** processing succeeds normally

#### Scenario: Remote file exceeds timeout

- **WHEN** remote CSV doesn't respond within 30 seconds
- **THEN** DuckDB raises timeout error
- **AND** system shows error panel with timeout message
- **AND** exits with code 2

### Requirement: Accept zip-compressed CSV inputs with a single CSV entry
The system SHALL accept zip archives that contain exactly one CSV entry and process that entry without manual extraction.

#### Scenario: Zip file with one CSV
- **WHEN** user runs `csvnorm ./data.zip` and the zip contains exactly one `.csv`
- **THEN** the system reads the CSV via a `zip://` path
- **AND** produces normalized output as for uncompressed inputs

#### Scenario: Zip file with multiple CSVs
- **WHEN** user runs `csvnorm ./data.zip` and the zip contains more than one `.csv`
- **THEN** the system fails with a clear error listing the CSV entries
- **AND** exits with code 2

#### Scenario: Zip file with no CSVs
- **WHEN** user runs `csvnorm ./data.zip` and the zip contains no `.csv`
- **THEN** the system fails with a clear error
- **AND** exits with code 2

### Requirement: Check-only validation mode

The system SHALL provide a `--check` flag that validates the CSV file without processing or normalizing it.

#### Scenario: Valid CSV with check mode

- **WHEN** user runs `csvnorm data.csv --check` on a valid CSV file
- **THEN** system validates the file structure
- **AND** outputs "✓ Valid CSV" to stderr
- **AND** exits with code 0
- **AND** no output file is created
- **AND** no encoding conversion is performed

#### Scenario: Invalid CSV with check mode

- **WHEN** user runs `csvnorm data.csv --check` on a CSV with validation errors
- **THEN** system validates the file structure
- **AND** outputs "✗ Invalid CSV: N rows rejected" to stderr
- **AND** outputs brief error summary to stderr
- **AND** exits with code 1
- **AND** no output file is created

#### Scenario: Check mode with remote URL

- **WHEN** user runs `csvnorm https://example.com/data.csv --check`
- **THEN** system validates the remote CSV
- **AND** outputs validation status to stderr
- **AND** exits with code 0 if valid, 1 if rows are rejected, 2 if the check could not run

#### Scenario: Check mode skips normalization

- **WHEN** user runs `csvnorm data.csv --check`
- **THEN** system performs only validation step
- **AND** skips encoding conversion (unless needed for validation)
- **AND** skips mojibake repair
- **AND** skips normalization
- **AND** skips output writing

#### Scenario: Check mode incompatible with output options

- **WHEN** user runs `csvnorm data.csv --check -o output.csv`
- **THEN** system shows error message: "--check writes nothing, so it cannot be used with -o; drop one of them"
- **AND** exits with code 2

#### Scenario: Check mode incompatible with strict mode

- **WHEN** user runs `csvnorm data.csv --check --strict`
- **THEN** system shows warning: "--strict is redundant with --check (both exit on errors)"
- **AND** proceeds with check mode
- **AND** exits with code 1 if errors found

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
- **AND** exits with code 2
