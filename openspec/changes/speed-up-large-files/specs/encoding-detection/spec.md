## MODIFIED Requirements

### Requirement: Primary encoding detection uses charset_normalizer
The system SHALL detect the input encoding without decoding the whole file once per candidate codec. It SHALL first decode the file as strict UTF-8 in chunks; a file that is valid UTF-8 is `utf-8` (also with a UTF-8 BOM), a pure ASCII file is `ascii`, an empty file is `utf-8`. For a file that is not valid UTF-8 the system SHALL build a sample with a window around the first UTF-8 error and around the first usable occurrence of every byte value `>= 0x80` in the file, and SHALL pass it to `charset_normalizer` so that the whole sample is examined, excluding `utf_8` and `ascii`. A UTF-16 or UTF-32 BOM, a UTF-8 BOM followed by invalid UTF-8, a NUL byte, or a high byte value without a usable window SHALL route the file to full-file detection with `charset_normalizer`.

#### Scenario: Valid UTF-8 file
- **WHEN** the input is valid UTF-8 with non-ASCII characters
- **THEN** the detected encoding is `utf-8`

#### Scenario: Sparse non-ASCII bytes in a large file
- **WHEN** the input is 200,000 ASCII rows with one cp1252 byte `0xE9` near the end
- **THEN** the detected encoding is one of `cp1252`, `latin-1`, `iso8859-15`
- **AND** the converted output contains `é`

#### Scenario: Sample looks like UTF-8
- **WHEN** the input starts with UTF-8 `’` (`E2 80 99`) and later contains a lone byte `0x92`
- **THEN** the detected encoding is not `utf-8`

#### Scenario: Binary file
- **WHEN** the input contains a NUL byte
- **THEN** full-file detection runs and a binary file raises "Cannot detect encoding"

#### Scenario: Conversion fails after detection
- **WHEN** the strict conversion with the detected encoding fails
- **THEN** the system runs full-file detection once and converts again
- **AND** if the second conversion fails, the system shows "Encoding conversion failed" and exits with code 1

## ADDED Requirements

### Requirement: UTF-8 conversion preserves line breaks
The system SHALL convert non-UTF-8 input to UTF-8 in fixed-size chunks and SHALL keep every CR, LF and CRLF byte sequence as in the input, inside and outside quoted fields, with the same result on every operating system.

#### Scenario: CRLF inside a quoted cell
- **WHEN** a latin-1 file has a quoted field containing `\r\n`
- **THEN** the output field contains `\r\n`
