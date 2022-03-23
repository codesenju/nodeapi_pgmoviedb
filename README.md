# nodejs_postgres

## restore db
pg_restore -d movie /db/movie.dump

## make db dump
pg_dump -Fc movie > movie.dump