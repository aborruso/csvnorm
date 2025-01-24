#!/bin/bash

set -x
set -e
set -u
set -o pipefail

# Check if input file is provided
if [ $# -eq 0 ]; then
    echo "Usage: $0 <input_csv_file> [-f|--force]"
    echo "  -f, --force   Force overwrite of existing output files"
    exit 1
fi

input_file="$1"
force_overwrite=false

# Check for force flag
if [ $# -gt 1 ] && { [ "$2" == "-f" ] || [ "$2" == "--force" ]; }; then
    force_overwrite=true
fi
# Convert filename to snake_case
base_name=$(basename "$input_file" .csv | sed -E 's/([A-Z])/_\1/g' | tr '-' '_' | tr '[:upper:]' '[:lower:]' | sed -E 's/^_//')
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
if [ "$encoding" != "utf-8" ]; then
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
duckdb --csv -c "select * from read_csv('$input_file',sample_size=-1,normalize_names=true)" >"$output_file"

# Clean up temporary files
rm -f "${folder}/tmp/reject_errors.csv"
if [ -f "${folder}/tmp/${base_name}_utf8.csv" ]; then
    rm -f "${folder}/tmp/${base_name}_utf8.csv"
fi
