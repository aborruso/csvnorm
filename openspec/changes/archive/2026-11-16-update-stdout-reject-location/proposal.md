# Change: Stdout-mode reject file goes to the system temp directory

## Why

In stdout mode (`csvnorm data.csv > out.csv`, or in a pipe) the reject file is written as `./reject_errors.csv` in the current working directory. It clutters the directory the command is run from, overwrites a previous `reject_errors.csv` there without warning, and fails when that directory is not writable.

## What Changes

- In stdout mode the reject file is created in the system temp directory with a unique name (`csvnorm_reject_errors_<id>.csv`).
- Its full path is printed on stderr in the validation error panel (`Details: <path>`), as today.
- If there are no rejected rows, no reject file is left behind, as today.
- File mode (`-o`) is unchanged: `{output_dir}/{output_stem}_reject_errors.csv`.

## Impact

- Affected specs: `output-location`
- Affected code: `src/csvnorm/core.py` (`_setup_output_paths`), README
- Behavior change for scripts that read `./reject_errors.csv` after a stdout run: they must read the path from stderr or use `-o`
