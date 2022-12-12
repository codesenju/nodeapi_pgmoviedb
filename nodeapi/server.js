// Constants
const express = require('express');
const APP_PORT = '3000';
const HOST = '0.0.0.0';
const table_name = 'title_basics'

// Connect to postgresql container instance
const Pool = require("pg").Pool;
const pool = new Pool({
  user: "postgres",
  host: "pgmoviedb.api.local",
  database: "movie",
  password: "12345",
  port: 5432
});

// App
const app = express();
app.get('/health', (req, res) => {
  res.send('Health OK!');
});

app.get('/', (req, res) => {
  res.send('<h1>Welcome to nodeapi.</h1>');
});

//Create Query
app.get("/api/v1/movies", (req, res) => {
    pool.query(
      `select * from ${table_name} where titletype = 'movie'  fetch first 20 rows only`,
      [],
      (error, results) => {
        if (error) {
          throw error;
        }
        res.status(200).json(results.rows);
      }
    );
  });
  
app.get("/api/v1/tvseries", (req, res) => {
    pool.query(
      `select * from ${table_name} where titletype = 'tvSeries' fetch first 20 rows only`,
      [],
      (error, results) => {
        if (error) {
          throw error;
        }
        res.status(200).json(results.rows);
      }
    );
  });
  
app.get("/api/v1/tvminiseries", (req, res) => {
    pool.query(
      `select * from ${table_name} where titletype = 'tvMiniSeries' fetch first 20 rows only`,
      [],
      (error, results) => {
        if (error) {
          throw error;
        }
        res.status(200).json(results.rows);
      }
    );
  });
  
  app.get("/api/v1/movies/:title", (req, res) => {
    pool.query(
      `select * from ${table_name} where LOWER(primarytitle) like LOWER('%${req.params.title}%') AND titletype = 'movie'`,
      [],
      (error, results) => {
        if (error) {
          throw error;
        }
        res.status(200).json(results.rows);
      }
    );
  });

  app.get("/api/v1/tvseries/:title", (req, res) => {
    pool.query(
      `select * from ${table_name} where LOWER(primarytitle) like LOWER('%${req.params.title}%') AND titletype = 'tvSeries'`,
      [],
      (error, results) => {
        if (error) {
          throw error;
        }
        res.status(200).json(results.rows);
      }
    );
  });
  
  app.get("/api/v1/tvMiniSeries/:title", (req, res) => {
    pool.query(
      `select * from ${table_name} where LOWER(primarytitle) like LOWER('%${req.params.title}%') AND titletype = 'tvMiniSeries'`,
      [],
      (error, results) => {
        if (error) {
          throw error;
        }
        res.status(200).json(results.rows);
      }
    );
  });


  app.listen(APP_PORT, HOST);
  console.log(`Running on http://${HOST}:${APP_PORT}`);