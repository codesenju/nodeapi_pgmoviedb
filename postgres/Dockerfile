FROM postgres:12
#COPY ./setup-master.sh /docker-entrypoint-initdb.d/setup-master.sh this line setups db for replication
COPY ./setup-db.sh /docker-entrypoint-initdb.d/setup-db.sh
WORKDIR /db
# COPY movie.dump ./
COPY title.basics.tsv ./
COPY import.sql ./