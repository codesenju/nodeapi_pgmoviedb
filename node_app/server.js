const express = require('express');

const app_port = 3000
const app = express();

// Connect to postgresql container instance
const Pool = require("pg").Pool;
const pool = new Pool({
  user: "postgres",
  host: "postgres",
  database: "movie",
  password: "12345",
  port: 5432
});


app.get('/', function (req, res) {
    res.send('Health OK!')
  })

//Create Query
app.get("/api/v1/movies", (req, res) => {
    pool.query(
      `select * from basic fetch first 50 rows only`,
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
      `select * from basic where LOWER(primarytitle) like LOWER('%${req.params.title}%') AND titletype like 'movie%'`,
      [],
      (error, results) => {
        if (error) {
          throw error;
        }
        res.status(200).json(results.rows);
      }
    );
  });

app.listen(app_port, () => {
  console.log(`Server is running on port `+ app_port);
});