#!/bin/bash
# pg_restore is a utility for restoring a PostgreSQL database from an archive created by pg_dump.
# Here we are restoring movie.dump into the movie database.
pg_restore -d movie /db/movie.dump
echo "Movie database restored!"