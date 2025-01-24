#!/bin/bash

set -x
set -e
set -u
set -o pipefail

folder="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

duckdb -c "copy (from read_csv('../test/Trasporto Pubblico Locale Settore Pubblico Allargato - Indicatore 2000-2020 Trasferimenti Correnti su Entrate Correnti.csv',store_rejects = true,sample_size=-1)) TO '/dev/null';copy (FROM reject_errors) to 'reject_errors.csv'"
