const express = require('express');
const { Sequelize, DataTypes } = require('sequelize');
const fs = require('fs');

const APP_PORT = '3000';
const HOST = '0.0.0.0';
const TABLE_NAME = 'title_basics';

const sequelize = new Sequelize(process.env.DB_NAME, process.env.DB_USERNAME, process.env.DB_PASSWORD, {
  host: process.env.DB_HOST,
  port: process.env.DB_PORT,
  dialect: 'postgres',
  dialectOptions: {
    ssl: {
      require: true,
      rejectUnauthorized: false,
      ca: fs.readFileSync('/certs/server.crt').toString(),
    },
  },
  pool: {
    max: 100,
    min: 0,
    acquire: 30000,
    idle: 10000,
  },
});

const Title = sequelize.define(TABLE_NAME, {
  tconst: {
    type: DataTypes.STRING,
    primaryKey: true,
  },
  titletype: DataTypes.STRING,
  primarytitle: DataTypes.STRING,
  originaltitle: DataTypes.STRING,
  isadult: DataTypes.INTEGER,
  startyear: DataTypes.INTEGER,
  endyear: DataTypes.INTEGER,
  runtimeminutes: DataTypes.INTEGER,
  genres: DataTypes.STRING,
}, {
  timestamps: false,
});

const app = express();

// CORS
app.use((req, res, next) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');
  next();
});


app.get('/api/v1/movies', async (req, res) => {
  try {
    const movies = await Title.findAll({
      where: {
        titletype: 'movie',
      },
      limit: 20,
    });
    res.status(200).json(movies);
  } catch (error) {
    console.error(`Failed to execute query: ${error.message}`);
    res.status(500).send('Internal Server Error');
  }
});

app.get('/api/v1/tvseries', async (req, res) => {
  try {
    const tvseries = await Title.findAll({
      where: {
        titletype: 'tvSeries',
      },
      limit: 20,
    });
    res.status(200).json(tvseries);
  } catch (error) {
    console.error(`Failed to execute query: ${error.message}`);
    res.status(500).send('Internal Server Error');
  }
});

app.get('/api/v1/tvminiseries', async (req, res) => {
  try {
    const tvminiseries = await Title.findAll({
      where: {
        titletype: 'tvMiniSeries',
      },
      limit: 20,
    });
    res.status(200).json(tvminiseries);
  } catch (error) {
    console.error(`Failed to execute query: ${error.message}`);
    res.status(500).send('Internal Server Error');
  }
});

app.get('/api/v1/movies/:title', async (req, res) => {
  try {
    const movies = await Title.findAll({
      where: {
        primarytitle: {
          [Sequelize.Op.iLike]: `%${req.params.title}%`,
        },
        titletype: 'movie',
      },
    });
    res.status(200).json(movies);
  } catch (error) {
    console.error(`Failed to execute query: ${error.message}`);
    res.status(500).send('Internal Server Error');
  }
});

app.get('/api/v1/tvseries/:title', async (req, res) => {
  try {
    const tvseries = await Title.findAll({
      where: {
        primarytitle: {
          [Sequelize.Op.iLike]: `%${req.params.title}%`,
        },
        titletype: 'tvSeries',
      },
    });
    res.status(200).json(tvseries);
  } catch (error) {
    console.error(`Failed to execute query: ${error.message}`);
    res.status(500).send('Internal Server Error');
  }
});

app.get('/api/v1/tvminiseries/:title', async (req, res) => {
  try {
    const tvminiseries = await Title.findAll({
      where: {
        primarytitle: {
          [Sequelize.Op.iLike]: `%${req.params.title}%`,
        },
        titletype: 'tvMiniSeries',
      },
    });
    res.status(200).json(tvminiseries);
  } catch (error) {
    console.error(`Failed to execute query: ${error.message}`);
    res.status(500).send('Internal Server Error');
  }
});

app.listen(APP_PORT, HOST, () => {
  console.log(`Running on http://${HOST}:${APP_PORT}`);
  console.log(`Integrated with Sequelize ORM \nSSL connection to postgress enabled`);
});
