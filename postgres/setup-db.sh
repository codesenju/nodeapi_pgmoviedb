#!/bin/bash
set -e
# Import title.basics.tsv
echo "Importing title.basics.tsv:"
psql -U postgres -d movie -f /db/import.sql || exit 1
echo "title.basics.tsv imported!"

# Configure SSL
psql -U postgres -c "ALTER SYSTEM SET ssl TO 'on'" && \
psql -U postgres -c "ALTER SYSTEM set ssl_cert_file = '/var/lib/postgresql/certs/server.crt';" && \
psql -U postgres -c "ALTER SYSTEM set ssl_key_file = '/var/lib/postgresql/certs/server.key';"