#!/bin/bash

#set -x
set -e
set -u
set -o pipefail

# Check if input file is provided
if [ $# -eq 0 ]; then
    echo "Usage: $0 <input_csv_file> [options]"
    echo "Options:"
    echo "  -f, --force         Force overwrite of existing output files"
    echo "  -n, --no-normalize  Keep original column names (disable snake_case normalization)"
    echo "                      By default, column names are converted to snake_case format"
    echo "                      (e.g., 'Column Name' becomes 'column_name'). Use this option"
    echo "                      to preserve the original column names as they appear in the"
    echo "                      input file."
    exit 1
fi

input_file="$1"
force_overwrite=false

# Parse options
force_overwrite=false
normalize_names=true

while [[ $# -gt 0 ]]; do
    case $1 in
        -f|--force)
            force_overwrite=true
            shift
            ;;
        -n|--no-normalize)
            normalize_names=false
            shift
            ;;
        *)
            # First non-option argument is the input file
            if [[ -z "$input_file" ]]; then
                input_file="$1"
            fi
            shift
            ;;
    esac
done
# Convert filename to clean snake_case
base_name=$(basename "$input_file" .csv | \
    tr '[:upper:]' '[:lower:]' | \
    sed -E 's/[^a-z0-9]+/_/g' | \
    sed -E 's/_+/_/g' | \
    sed -E 's/^_|_$//g')
folder="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

mkdir -p "${folder}"/tmp

# Check if final output file exists
output_file="${folder}/tmp/${base_name}.csv"

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
rm -f "${folder}/tmp/reject_errors.csv"

# Check and convert encoding to UTF-8 if needed
encoding=$(head -n 10000 "$input_file" | chardetect --minimal)
if [ "$encoding" != "utf-8" ] && [ "$encoding" != "ascii" ]; then
    echo "Converting file from $encoding to UTF-8..."
    temp_file="${folder}/tmp/${base_name}_utf8.csv"
    iconv -f "$encoding" -t UTF-8 "$input_file" > "$temp_file"
    input_file="$temp_file"
fi

# Process the input file
duckdb -c "copy (from read_csv('$input_file',store_rejects = true,sample_size=-1)) TO '/dev/null';copy (FROM reject_errors) to '${folder}/tmp/reject_errors.csv'"

# Check if there are any errors
if [ $(wc -l < "${folder}/tmp/reject_errors.csv") -gt 1 ]; then
    echo "Error: DuckDB encountered invalid rows while processing the CSV file."
    echo "Details of the errors can be found in: ${folder}/tmp/reject_errors.csv"
    echo "Please fix the issues and try again."
    exit 1
fi

# Create final output file
if [ "$normalize_names" = true ]; then
    duckdb --csv -c "select * from read_csv('$input_file',sample_size=-1,normalize_names=true)" >"$output_file"
else
    duckdb --csv -c "select * from read_csv('$input_file',sample_size=-1)" >"$output_file"
fi

# Clean up temporary files
# Only remove error file if it's empty or has just the header
if [ $(wc -l < "${folder}/tmp/reject_errors.csv" 2>/dev/null || echo 0) -le 1 ]; then
    rm -f "${folder}/tmp/reject_errors.csv"
fi

# Clean up UTF-8 conversion file if it exists
if [ -f "${folder}/tmp/${base_name}_utf8.csv" ]; then
    rm -f "${folder}/tmp/${base_name}_utf8.csv"
fi
