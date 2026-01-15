#!/bin/bash

# set -x
set -e
set -u
set -o pipefail

print_help() {
    echo "Usage: $(basename "$0") <input_csv_file> [options]"
    echo "Options:"
    echo "  -f, --force         Force overwrite of existing output files"
    echo "  -n, --keep-names    Keep original column names (disable snake_case normalization)"
    echo "                      By default, column names are converted to snake_case format"
    echo "                      (e.g., 'Column Name' becomes 'column_name'). Use this option"
    echo "                      to preserve the original column names as they appear in the"
    echo "                      input file."
    echo "  -d, --delimiter     Set custom field delimiter (default: comma)"
    echo "                      Example: -d ';' for semicolon-delimited files"
    printf "%s\n" "                      Example: -d $\'\t\' for tab-delimited files"
    echo "                      Example: -d '|' for pipe-delimited files"
    echo "  -o, --output-dir    Set custom output directory (default: 'tmp')"
    echo "                      Example: -o my_output_directory"
    echo "  -v, --verbose       Enable verbose output for debugging"
    echo "  -h, --help          Show this help message and exit"
    echo "Examples:"
    echo "  $(basename "$0") data.csv -d ';' -o output_folder --force"
    printf "%s\n" "  $(basename "$0") data.csv --keep-names --delimiter $\'\t\'"
    echo ""
}

# Check if input file is provided
if [ $# -eq 0 ]; then
    print_help
    exit 1
fi

folder="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
input_file=""
force_overwrite=false

# Parse options
force_overwrite=false
normalize_names=true
delimiter=","
output_dir="${folder}/tmp"
verbose=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -f|--force)
            force_overwrite=true
            shift
            ;;
        -n|--keep-names)
            normalize_names=false
            shift
            ;;
        -d|--delimiter)
            if [[ -z "$2" ]]; then
                echo "Error: --delimiter requires a value"
                print_help
                exit 1
            fi
            delimiter="$2"
            shift 2
            ;;
        -v|--verbose)
            verbose=true
            shift
            ;;
        -h|--help)
            print_help
            exit 0
            ;;
        -o|--output-dir)
            if [[ -z "$2" ]]; then
                echo "Error: --output-dir requires a value"
                print_help
                exit 1
            fi
            output_dir="$2"
            shift 2
            ;;
        --)
            shift
            if [ -z "$input_file" ] && [ $# -gt 0 ]; then
                input_file="$1"
                shift
            fi
            ;;
        -*)
            echo "Error: Unknown option: $1"
            print_help
            exit 1
            ;;
        *)
            if [[ -z "$input_file" ]]; then
                input_file="$1"
            else
                echo "Error: Unexpected argument: $1"
                print_help
                exit 1
            fi
            shift
            ;;
    esac
done

if [ -z "$input_file" ]; then
    echo "Error: input CSV file is required."
    print_help
    exit 1
fi
# Convert filename to clean snake_case
base_name=$(basename "$input_file" .csv |
    tr '[:upper:]' '[:lower:]' |
    sed -E 's/[^a-z0-9]+/_/g' |
    sed -E 's/_+/_/g' |
    sed -E 's/^_|_$//g')
folder="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

mkdir -p "$output_dir"

vlog() {
    if [ "$verbose" = true ]; then
        echo "$@"
    fi
}

require_cmd() {
    if ! command -v "$1" >/dev/null 2>&1; then
        echo "Error: required command not found: $1"
        exit 1
    fi
}

# Basic input validation
if [ ! -f "$input_file" ] || [ ! -r "$input_file" ]; then
    echo "Error: input file not found or not readable: $input_file"
    exit 1
fi

if [ "${#delimiter}" -ne 1 ]; then
    echo "Error: --delimiter must be a single character"
    print_help
    exit 1
fi

require_cmd normalizer
require_cmd iconv
require_cmd file
require_cmd duckdb

# Check if final output file exists
output_file="${output_dir}/${base_name}.csv"

if [ -f "$output_file" ]; then
    if [ "$force_overwrite" = false ]; then
        echo "Warning: Output file already exists:"
        echo "  - $output_file"
        read -p "Do you want to overwrite it? [y/N] " -r
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Aborted by user."
            exit 0
        fi
    fi
fi

# Always overwrite temporary error file
rm -f "${output_dir}/reject_errors.csv"

# Check and convert encoding to UTF-8 if needed
set +e
encoding=$(normalizer --minimal "$input_file" 2>/dev/null)
exit_code=$?
set -e

# Ignore SIGPIPE (141) as it's expected behavior with head
if [ $exit_code -eq 141 ]; then
    exit_code=0
fi

vlog "normalizer exit code: $exit_code"
vlog "Detected encoding: $encoding"

# Normalize known encoding aliases for iconv compatibility
case "${encoding^^}" in
    MACROMAN)
        vlog "Adjusting encoding from MACROMAN to MACINTOSH"
        encoding="MACINTOSH"
        ;;
    UTF_8)
        vlog "Adjusting encoding from UTF_8 to UTF-8"
        encoding="UTF-8"
        ;;
    UTF_8_SIG)
        vlog "Adjusting encoding from UTF_8_SIG to UTF-8-SIG"
        encoding="UTF-8-SIG"
        ;;
esac


# If normalizer failed (excluding SIGPIPE), try alternative method
if [ $exit_code -ne 0 ] || [ -z "$encoding" ]; then
    vlog "normalizer failed, trying alternative method..."
    encoding=$(file -b --mime-encoding "$input_file")
    vlog "Alternative encoding detection: $encoding"
fi

# Convert encoding to lowercase for case-insensitive comparison
encoding_lower=$(echo "$encoding" | tr '[:upper:]' '[:lower:]')
if [ "$encoding_lower" != "utf-8" ] && [ "$encoding_lower" != "ascii" ] && [ "$encoding_lower" != "utf-8-sig" ]; then
    echo "Converting file from $encoding to UTF-8..."
    temp_file="${output_dir}/${base_name}_utf8.csv"
    iconv -f "$encoding" -t UTF-8 "$input_file" > "$temp_file"
    input_file="$temp_file"
fi

# Process the input file
duckdb -c "copy (from read_csv('$input_file',store_rejects = true,sample_size=-1,all_varchar=true)) TO '/dev/null';copy (FROM reject_errors) to '${output_dir}/reject_errors.csv'"

# Check if there are any errors
if [ "$(wc -l < "${output_dir}/reject_errors.csv")" -gt 1 ]; then
    echo "Error: DuckDB encountered invalid rows while processing the CSV file."
    echo "Details of the errors can be found in: ${output_dir}/reject_errors.csv"
    echo "Please fix the issues and try again."
    exit 1
fi

# Create final output file
copy_options="(header true, format csv"
if [ "$delimiter" != "," ]; then
    copy_options+=", delimiter '$delimiter'"
fi
copy_options+=")"

if [ "$normalize_names" = true ]; then
    duckdb -c "copy (select * from read_csv('$input_file',sample_size=-1,normalize_names=true,all_varchar=true)) to '$output_file' $copy_options"
else
    duckdb -c "copy (select * from read_csv('$input_file',sample_size=-1,all_varchar=true)) to '$output_file' $copy_options"
fi

# Clean up temporary files
# Only remove error file if it's empty or has just the header
reject_rows=$(wc -l < "${output_dir}/reject_errors.csv" 2>/dev/null || echo 0)
if [ -f "${output_dir}/reject_errors.csv" ] && [ "$reject_rows" -le 1 ]; then
    rm -f "${output_dir}/reject_errors.csv"
fi

# Clean up UTF-8 conversion file if it exists
if [ -f "${output_dir}/${base_name}_utf8.csv" ]; then
    rm -f "${output_dir}/${base_name}_utf8.csv"
fi
