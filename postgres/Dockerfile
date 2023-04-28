FROM postgres:12
#COPY ./setup-master.sh /docker-entrypoint-initdb.d/setup-master.sh this line setups db for replication
COPY ./setup-db.sh /docker-entrypoint-initdb.d/setup-db.sh
# README ->  https://www.imdb.com/interfaces/
ADD https://datasets.imdbws.com/title.basics.tsv.gz /tmp/title.basics.tsv.gz
RUN gunzip -f /tmp/title.basics.tsv.gz
WORKDIR /db
# COPY movie.dump ./
RUN cp /tmp/title.basics.tsv ./ && \
    chmod 777 /db/title.basics.tsv && \
    chown postgres /db/title.basics.tsv

COPY import.sql ./

COPY ./certs /var/lib/postgresql/certs

# rivate key file "/var/lib/postgresql/certs/server.key" has group or world access
#  File must have permissions u=rw (0600) or less if owned by the database user, or permissions u=rw,g=r (0640) or less if owned by root.
RUN chmod 600 /var/lib/postgresql/certs/server.* && \
    chown postgres /var/lib/postgresql/certs/server.*