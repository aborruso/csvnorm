# encoding-detection Specification

## Purpose
TBD - created by archiving change update-encoding-detector. Update Purpose after archive.
## Requirements
### Requirement: Primary encoding detection uses charset_normalizer
The system SHALL detect the input encoding with `charset_normalizer`. For files up to 50 MiB it SHALL run `charset_normalizer` on the whole file. For larger files it SHALL first decode the file as strict UTF-8 in chunks; a file that is valid UTF-8 is `utf-8` (also with a UTF-8 BOM), a pure ASCII file is `ascii`. For a larger file that is not valid UTF-8 the system SHALL build a sample with a window around the first usable occurrence of every byte value `>= 0x80` in the file (and around the first UTF-8 error when possible), SHALL pass it to `charset_normalizer` so that the whole sample is examined, excluding `utf_8` and `ascii`, and SHALL prefer a Western codec (cp1252, latin-1, iso8859-15) among the least chaotic candidates. A UTF-16 or UTF-32 BOM, a UTF-8 BOM followed by invalid UTF-8, a NUL byte, ISO-2022 or HZ escape sequences in an ASCII file, a high byte value without a usable window, or a sample with no candidate SHALL route the file to whole-file detection.

#### Scenario: Primary detector succeeds
- **WHEN** `charset_normalizer` returns a usable encoding label
- **THEN** the system uses that label for subsequent conversion logic

#### Scenario: Primary detector fails
- **WHEN** `charset_normalizer` returns no usable encoding label on the whole file
- **THEN** the system stops with "Cannot detect encoding" and exit code 1
- **AND** no other detector is used (there is no `file -b --mime-encoding` fallback)

#### Scenario: File up to 50 MiB
- **WHEN** the input is 50 MiB or smaller
- **THEN** the encoding is detected by `charset_normalizer` on the whole file, as in version 1.3.0

#### Scenario: Valid UTF-8 file
- **WHEN** the input is valid UTF-8 with non-ASCII characters
- **THEN** the detected encoding is `utf-8`

#### Scenario: Sparse non-ASCII bytes in a large file
- **WHEN** the input is larger than 50 MiB, ASCII except one cp1252 byte `0xE9` near the end
- **THEN** the detected encoding is one of `cp1252`, `latin-1`, `iso8859-15`
- **AND** the converted output contains `é`

#### Scenario: Sample looks like UTF-8
- **WHEN** a file larger than 50 MiB starts with UTF-8 `’` (`E2 80 99`) and later contains a lone byte `0x92`
- **THEN** the detected encoding is not `utf-8`

#### Scenario: Binary file
- **WHEN** the input contains a NUL byte
- **THEN** whole-file detection runs and a binary file raises "Cannot detect encoding"

#### Scenario: Conversion fails after detection
- **WHEN** the strict conversion with the detected encoding fails
- **THEN** the system runs full-file detection once and converts again
- **AND** if the second conversion fails, the system shows "Encoding conversion failed" and exits with code 1

### Requirement: UTF-8 conversion preserves line breaks
The system SHALL convert non-UTF-8 input to UTF-8 in fixed-size chunks and SHALL keep every CR, LF and CRLF byte sequence as in the input, inside and outside quoted fields, with the same result on every operating system.

#### Scenario: CRLF inside a quoted cell
- **WHEN** a latin-1 file has a quoted field containing `\r\n`
- **THEN** the output field contains `\r\n`

