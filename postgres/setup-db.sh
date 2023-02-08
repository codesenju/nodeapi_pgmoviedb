#!/bin/bash
set -e
# Import title.basics.tsv
echo "Importing title.basics.tsv:"
psql -U postgres -d movie -f /db/import.sql || exit 1
echo "title.basics.tsv imported!"