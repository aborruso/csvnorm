# CSV Normalizer Utility – Product Requirements Document (PRD)

## 1. Purpose
Provide a robust command-line tool that validates, cleans, and normalizes CSV files so that downstream analytics, ETL, and data-science workflows can reliably consume them.

## 2. Background
Many open data portals and legacy systems publish CSV files with inconsistent encodings, delimiters, and header naming conventions. These issues break automated pipelines and require manual intervention. This utility removes that friction.

## 3. Goals & Objectives
* Accept a raw CSV file and output a fully normalized UTF-8 comma-delimited file.
* Detect and report structural or encoding errors early.
* Integrate easily into shell scripts and CI pipelines.
* Support datasets up to 1 GB on commodity machines.

## 4. In-Scope
* Encoding detection & conversion to UTF-8.
* Delimiter standardisation (auto-detect or user-supplied).
* Optional snake_case header normalisation.
* Detailed error report including row numbers and reasons.
* Configurable output directory and overwrite behaviour.

### Out-of-Scope
* Interactive GUI.
* Automatic schema inference beyond DuckDB default behaviour.
* Cloud storage integration.

## 5. Personas
| Persona | Needs |
|---------|-------|
| Data Engineer | Batch-process hundreds of CSVs in CI pipelines. |
| Data Analyst  | Quickly clean a single file before importing into BI tools. |
| Open-Data Maintainer | Validate files before publishing. |

## 6. User Stories
1. *As a Data Engineer* I want to run `csv_normalizer large.csv --force` so that existing outputs are overwritten without a prompt.  
2. *As a Data Analyst* I want to keep original column names by adding `--no-normalize` so that my downstream scripts referencing camelCase headers keep working.  
3. *As an Open-Data Maintainer* I want the tool to fail fast and generate `reject_errors.csv` so that I can fix invalid rows.

## 7. Functional Requirements
FR-1 The tool SHALL accept an input CSV path as the first positional argument.  
FR-2 The tool SHALL detect file encoding using `charset_normalizer` and fallback to `file` when necessary.  
FR-3 If encoding ≠ UTF-8/ASCII, the tool SHALL convert the file to UTF-8 using `iconv`.  
FR-4 The tool SHALL validate the CSV with DuckDB’s `read_csv` and store rejects to `reject_errors.csv`.  
FR-5 If rejects are present (>1 data line), the tool SHALL exit with code 1.  
FR-6 The tool SHALL support `--delimiter <char>` to override delimiter detection.  
FR-7 The tool SHALL output the cleaned file to `<output_dir>/<clean_name>.csv`.  
FR-8 The tool SHALL normalise headers to snake_case unless `--no-normalize` is set.  
FR-9 The tool SHALL support `--force` to overwrite existing output without a prompt.  
FR-10 The tool SHALL support `--verbose` to print debug information.

## 8. Non-Functional Requirements
NFR-1 Execution time for a 100 MB file SHOULD be < 60 s on a 4-core machine.  
NFR-2 Memory footprint SHOULD not exceed 2× input file size.  
NFR-3 The script SHALL target Bash 4+ and run on Linux and macOS.  
NFR-4 The code SHALL follow the conventions in `CONVENTIONS.md` and pass `shellcheck`.

## 9. Constraints & Assumptions
* Relies on DuckDB, charset_normalizer, and iconv being installed.
* Users have write permission to the output directory.
* Large files may require increased system resources.

## 10. KPIs / Success Metrics
* ≥ 95 % of processed files produce zero rejects on first run.
* Average runtime < 1 s per 10 MB on reference hardware.
* < 1 % bug-report rate per 1000 executions after v1.1.

## 11. Future Work
* Parallel processing for large datasets.
* Native Windows PowerShell wrapper.
* Optional JSON/YAML schema validation.
* Publishing as a PyPI package with CLI entry point.
