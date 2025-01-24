#!/bin/bash

set -x
set -e
set -u
set -o pipefail

folder="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

mkdir -p "${folder}"/tmp

duckdb -c "copy (from read_csv('../test/Trasporto Pubblico Locale Settore Pubblico Allargato - Indicatore 2000-2020 Trasferimenti Correnti su Entrate Correnti.csv',store_rejects = true,sample_size=-1)) TO '/dev/null';copy (FROM reject_errors) to '${folder}/tmp/reject_errors.csv'"

duckdb --csv -c "select * from read_csv('../test/Trasporto Pubblico Locale Settore Pubblico Allargato - Indicatore 2000-2020 Trasferimenti Correnti su Entrate Correnti.csv',sample_size=-1)" >"${folder}/tmp/Trasporto Pubblico Locale Settore Pubblico Allargato - Indicatore 2000-2020 Trasferimenti Correnti su Entrate Correnti.csv"
