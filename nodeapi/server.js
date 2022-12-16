// Constants
const express = require('express');
const APP_PORT = '3000';
const HOST = '0.0.0.0';
const table_name = 'title_basics'
require('dotenv').config()
const url_port =  "pgmoviedb.api.local:5432"
const db = "movie"
//####################################################
const pgpassword = process.env.PGPASSWORD
//####################################################
//XRAY
//var AWSXRay = require('aws-xray-sdk');

//const { Pool, Client } = AWSXRay.capturePostgres(require('pg'))
// const { Pool, Client } = require('pg')
//####################################################
const connectionString = `postgresql://postgres:${pgpassword}@${url_port}/${db}`
console.log("App integrated with xray for postgres - updated with segment code block.")
// Connect to postgresql container instance
//####################
//##XRAY INTEGRATION##
//####################
var AWSXRay = require('aws-xray-sdk');
AWSXRay.setContextMissingStrategy("LOG_ERROR");
var capturePostgres = require('aws-xray-sdk-postgres');
var pg = capturePostgres(require('pg'));
var pool = new pg.Pool({
  connectionString,
});
var client = new pg.Client();
//###########
//###########
// App
const app = express();
app.use(AWSXRay.express.openSegment("Nodeapi"));

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
      `select * from ${table_name} where LOWER(primarytitle) like LOWER('%${req.params.title}%') AND titletype like 'movie%'`,
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
      `select * from ${table_name} where LOWER(primarytitle) like LOWER('%${req.params.title}%') AND titletype  'tvSeries%'`,
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
      `select * from ${table_name} where LOWER(primarytitle) like LOWER('%${req.params.title}%') AND titletype like 'tvMiniSeries%'`,
      [],
      (error, results) => {
        if (error) {
          throw error;
        }
        res.status(200).json(results.rows);
      }
    );
  });;

app.use(AWSXRay.express.closeSegment());
app.listen(APP_PORT, HOST);

console.log(`Running on http://${HOST}:${APP_PORT}`);
