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