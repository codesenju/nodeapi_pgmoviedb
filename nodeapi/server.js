// Constants
const express = require('express');
const APP_PORT = '3000';
const HOST = '0.0.0.0';
const table_name = 'title_basics'
let pgpasswd = 'null'
//###################################################
//###CODE BLOCK TO GET SECRET FROM SECRET MANAGER###
//###################################################
// Load the AWS SDK
var AWS = require('aws-sdk'),
    region = "us-east-1",
    secretName = "postgres/password",
    secret,
    decodedBinarySecret;
// Create a Secrets Manager client
var client = new AWS.SecretsManager({
    region: region
});
// In this sample we only handle the specific exceptions for the 'GetSecretValue' API.
// See https://docs.aws.amazon.com/secretsmanager/latest/apireference/API_GetSecretValue.html
// We rethrow the exception by default.
client.getSecretValue({SecretId: secretName}, function(err, data) {
    if (err) {
        if (err.code === 'DecryptionFailureException')
            // Secrets Manager can't decrypt the protected secret text using the provided KMS key.
            // Deal with the exception here, and/or rethrow at your discretion.
            throw err;
        else if (err.code === 'InternalServiceErrorException')
            // An error occurred on the server side.
            // Deal with the exception here, and/or rethrow at your discretion.
            throw err;
        else if (err.code === 'InvalidParameterException')
            // You provided an invalid value for a parameter.
            // Deal with the exception here, and/or rethrow at your discretion.
            throw err;
        else if (err.code === 'InvalidRequestException')
            // You provided a parameter value that is not valid for the current state of the resource.
            // Deal with the exception here, and/or rethrow at your discretion.
            throw err;
        else if (err.code === 'ResourceNotFoundException')
            // We can't find the resource that you asked for.
            // Deal with the exception here, and/or rethrow at your discretion.
            throw err;
    }
    else {
        // Decrypts secret using the associated KMS CMK.
        // Depending on whether the secret is a string or binary, one of these fields will be populated.
        if ('SecretString' in data) {
            secret = data.SecretString;
        } else {
            let buff = new Buffer(data.SecretBinary, 'base64');
            decodedBinarySecret = buff.toString('ascii');
        }
    }
    
    // Your code goes here. | save password in variable pgpasswd 
    var obj = JSON.parse(secret)
    pgpasswd = obj.POSTGRES_PASSWORD
    
// snippet-end:[secretsmanager.JavaScript.secrets.GetSecretValue]
//####################################################
//####################################################

// Connect to postgresql container instance
const Pool = require("pg").Pool;
const pool = new Pool({
  user: "postgres",
  host: "pgmoviedb.api.local",
  database: "movie",
  password: pgpasswd,
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

app.listen(APP_PORT, HOST);

console.log(`Running on http://${HOST}:${APP_PORT}`);

});
