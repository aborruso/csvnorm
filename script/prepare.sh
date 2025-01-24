#!/bin/bash

set -x
set -e
set -u
set -o pipefail

# Check if input file is provided
if [ $# -eq 0 ]; then
    echo "Usage: $0 <input_csv_file>"
    exit 1
fi

input_file="$1"
base_name=$(basename "$input_file" .csv)
folder="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

mkdir -p "${folder}"/tmp

# Process the input file
duckdb -c "copy (from read_csv('$input_file',store_rejects = true,sample_size=-1)) TO '/dev/null';copy (FROM reject_errors) to '${folder}/tmp/reject_errors.csv'"

# Check if there are any errors
if [ $(wc -l < "${folder}/tmp/reject_errors.csv") -gt 1 ]; then
    echo "Error: Invalid rows found in CSV file. Check ${folder}/tmp/reject_errors.csv for details."
    exit 1
fi

duckdb --csv -c "select * from read_csv('$input_file',sample_size=-1)" >"${folder}/tmp/${base_name}_normalized.csv"
