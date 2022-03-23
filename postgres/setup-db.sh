#!/bin/bash
# Import title.basics.tsv
echo "Importing title.basics.tsv:"
psql -U postgres -d movie -f /db/import.sql
echo "title.basics.tsv imported!"