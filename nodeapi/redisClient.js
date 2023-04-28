const redis = require('redis');
const client = redis.createClient();

client.on('error', (error) => {
  console.error(`Error: ${error}`);
});

client.on('connect', () => {
  console.log('Connected to Redis server');
});

module.exports = client;