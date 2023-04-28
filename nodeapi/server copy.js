// Constants
const express = require('express');
const APP_PORT = '3000';
const HOST = '0.0.0.0';
const table_name = 'title_basics'
const morgan = require('morgan'); // Import morgan package

console.log("App integrated with xray for postgres - updated with segment code block.")
console.log("Added retry attempts and error handling.\n\nHave a nice day!\n\n")
// Connect to postgresql container instance
var AWSXRay = require('aws-xray-sdk');
AWSXRay.setContextMissingStrategy("LOG_ERROR");
var capturePostgres = require('aws-xray-sdk-postgres');
var pg = capturePostgres(require('pg'));

const Pool = require("pg").Pool;
const pool = new pg.Pool({
  user: process.env.DB_USERNAME,
  host: process.env.DB_HOST,
  database: process.env.DB_NAME,
  password: process.env.DB_PASSWORD,
  port: process.env.DB_PORT,
  connectionTimeoutMillis: 5000, // Retry connection attempts every 5 seconds
  idleTimeoutMillis: 30000, // Close idle clients after 30 seconds
  max: 100, // Maximum number of clients in the pool
  keepAlive: true,
});

// App
const app = express();

// Add logging middleware MORGAN
app.use(morgan('combined'));


app.get('/healthz', (req, res) => {
  res.send('Health OK!');
});

app.get('/', (req, res) => {
  res.send('<h1>Welcome to nodeapi.</h1>');
});


// Retry logic
const retryInterval = 5000; // retry every 5 seconds
const maxRetryCount = 10; // retry a maximum of 10 times
let retryCount = 0;

function connectDB(callback) {
  pool.connect((err, client, release) => {
    if (err) {
      if (retryCount >= maxRetryCount) {
        console.error(`Could not connect to database after ${maxRetryCount} attempts. Exiting...`);
        process.exit(1);
      }
      console.error(`Failed to connect to database, retrying in ${retryInterval / 1000} seconds...`);
      retryCount++;
      setTimeout(() => {
        connectDB(callback);
      }, retryInterval);
    } else {
      console.log("Connected to database successfully!");
      retryCount = 0;
      callback(client, release);
    }
  });
}

// XRAY --//
app.use(AWSXRay.express.openSegment("postgres"));
//-------//

//Create Query
app.get("/api/v1/movies", (req, res) => {
  connectDB((client, release) => {
    client.query(`select * from ${table_name} where titletype = 'movie' fetch first 20 rows only`, (error, results) => {
      release();
      if (error) {
        console.error(`Failed to execute query: ${error.message}`);
        res.status(500).send("Internal Server Error");
      } else {
        res.status(200).json(results.rows);
      }
    });
  });
});

app.get("/api/v1/tvseries", (req, res) => {
  connectDB((client, release) => {
    client.query(`select * from ${table_name} where titletype = 'tvSeries' fetch first 20 rows only`, (error, results) => {
      release();
      if (error) {
        console.error(`Failed to execute query: ${error.message}`);
        res.status(500).send("Internal Server Error");
      } else {
        res.status(200).json(results.rows);
      }
    });
  });
});

app.get("/api/v1/tvminiseries", (req, res) => {
  pool.query(`
    select * from ${ table_name } where titletype = 'tvMiniSeries' fetch first 20 rows only`,
    [],
    (error, results) => {
      if (error) {
        console.error('Error occurred:', error.stack);
        res.status(500).send('Internal Server Error');
      } else {
        res.status(200).json(results.rows);
      }
    }
  );
});

app.get("/api/v1/movies/:title", (req, res) => {
  pool.query(`
    select * from ${ table_name } where LOWER(primarytitle) like LOWER('%${req.params.title}%') AND titletype = 'movie'`,
    [],
    (error, results) => {
      if (error) {
        console.error('Error occurred:', error.stack);
        res.status(500).send('Internal Server Error');
      } else {
        res.status(200).json(results.rows);
      }
    }
  );
});

app.get("/api/v1/tvseries/:title", (req, res) => {
  pool.query(`
    select * from ${ table_name } where LOWER(primarytitle) like LOWER('%${req.params.title}%') AND titletype = 'tvSeries'`,
    [],
    (error, results) => {
      if (error) {
        console.error('Error occurred:', error.stack);
        res.status(500).send('Internal Server Error');
      } else {
        res.status(200).json(results.rows);
      }
    }
  );
});

app.get("/api/v1/tvMiniSeries/:title", (req, res) => {
  pool.query(`
    select * from ${ table_name } where LOWER(primarytitle) like LOWER('%${req.params.title}%') AND titletype = 'tvMiniSeries'`,
    [],
    (error, results) => {
      if (error) {
        console.error('Error occurred:', error.stack);
        res.status(500).send('Internal Server Error');
      } else {
        res.status(200).json(results.rows);
      }
    }
  );
});

// XRAY --//
app.use(AWSXRay.express.closeSegment("postgres"));
//--------//

// Add a retry logic in case of failure to connect to the database
const retryIntervalMs = 5000;
let attempts = 0;
const maxAttempts = 5;

function connect() {
  console.log(`Trying to connect to database.Attempt ${ attempts + 1} of ${ maxAttempts }.`);
pool.connect((error, client) => {
  if (error) {
    console.error(F`ailed to connect to database: ${ error }`);
    attempts++;
    if (attempts >= maxAttempts) {
      console.error(`Failed to connect to database after ${ maxAttempts } attempts.Exiting.`);
      process.exit(1);
    } else {
      console.log(`Retrying in ${ retryIntervalMs / 1000} seconds...`);
setTimeout(connect, retryIntervalMs);
  }
  } else {
  console.log(`Connected to database after ${ attempts + 1} attempts.`);
  }
  });
  }

connect();

app.listen(APP_PORT, HOST, () => {
  console.log(`Running on http://${HOST}:${APP_PORT}`);
  });