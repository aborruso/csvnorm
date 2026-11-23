# Change: Help, errors and exit codes readable by an agent

## Why

An AI agent that discovers csvnorm from a non-interactive shell, with no skill and no knowledge of the repository, must reach a first useful result from the installed `--help` alone. Today the help is a list of options: it does not say what the pipeline does or does not do, where the output and the reject file go, what the exit codes mean, or the limits (URL download, temporary space, sampled detection above 50 MiB). Exit code 1 means both "rows rejected, output written" and "could not run, no output", so a caller has to parse stderr to know whether it has a file to use. Errors are drawn in boxes also in pipes, and some do not say how to fix them.

## What Changes

- `--help`: short description of the pipeline and of what csvnorm does not do; sections Start here (three real commands), Output, Exit codes, Limits and side effects, Encoding names (online list and an offline command), Examples. No banner.
- `--version`: one line `csvnorm X.Y.Z` when stdout is not a terminal; the banner stays on a terminal.
- **BREAKING** Exit codes, grep style: 0 clean, 1 rows rejected (output still written unless `--strict`), 2 could not complete (invalid command line, missing file, download failure, undecodable or undetectable encoding, disk full, unexpected error). Fatal errors exited with 1 before.
- Unexpected exceptions are caught: one `Error:` line, exit 2, full traceback with `-V`.
- When stderr is not a terminal, errors, warnings and the validation report are plain lines, without boxes.
- Error messages that lacked one get the remedy (missing file, not a file, download failure, existing output, incompatible options).
- The existing output file error is an error, no longer a warning.
- The requirement on the validation summary said exit code 0 with rejected rows; the code exits with 1 since 1.3.0. The requirement is aligned.

## Impact

- Affected specs: `csv-input`, `encoding-detection`, `error-handling`, `processing-summary`
- Affected code: `src/csvnorm/cli.py`, `src/csvnorm/core.py`, `src/csvnorm/ui.py`, README
- Scripts that test `$? -eq 1` to catch any failure miss fatal errors, which now exit with 2. Scripts that test zero against non-zero are unaffected
