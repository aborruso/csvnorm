## ADDED Requirements

### Requirement: Declared input encoding
The system SHALL accept an optional `-e/--encoding NAME` option. When it is given, the system SHALL decode the input with that encoding and SHALL NOT run automatic encoding detection.

#### Scenario: Declared encoding decodes the input
- **WHEN** the user runs `csvnorm test/windows1252_quotes.csv -e cp1252`
- **THEN** the output is UTF-8 and contains `“Libro”` and `10€`
- **AND** automatic detection is not run

#### Scenario: Unknown encoding name
- **WHEN** the user passes an encoding name that is not a Python codec
- **THEN** the system prints an error on stderr and exits with code 1 before reading the input

#### Scenario: Input not decodable with the declared encoding
- **WHEN** the input contains bytes that the declared encoding cannot decode
- **THEN** the system exits with code 1
- **AND** the error message reports the declared encoding, the byte offset and the offending byte
- **AND** the system does not fall back to automatic detection

#### Scenario: No option given
- **WHEN** `--encoding` is not given
- **THEN** the system detects the encoding automatically as before

### Requirement: Summary reports a declared encoding
The processing summary SHALL label the encoding as declared when it comes from `--encoding`.

#### Scenario: Summary label
- **WHEN** the user runs csvnorm with `-e cp1252` on a non-UTF-8 file
- **THEN** the summary shows `cp1252 → UTF-8 (declared)`
