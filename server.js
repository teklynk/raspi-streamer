const express = require('express');
const bodyParser = require('body-parser');
const fs = require('fs');
require('dotenv').config();

const app = express();
const port = 3000;

app.use(bodyParser.json());

app.get('/', (req, res) => {
  res.sendFile(__dirname + '/index.html');
});

app.post('/start_stream', (req, res) => {
  fetch('http://localhost:5000/start_stream', { method: 'POST' })
    .then(response => response.json())
    .then(data => res.json(data))
    .catch(err => res.status(500).json({ error: err }));
});

app.post('/stop_stream', (req, res) => {
  fetch('http://localhost:5000/stop_stream', { method: 'POST' })
    .then(response => response.json())
    .then(data => res.json(data))
    .catch(err => res.status(500).json({ error: err }));
});

app.post('/start_recording', (req, res) => {
  fetch('http://localhost:5000/start_recording', { method: 'POST' })
    .then(response => response.json())
    .then(data => res.json(data))
    .catch(err => res.status(500).json({ error: err }));
});

app.post('/stop_recording', (req, res) => {
  fetch('http://localhost:5000/stop_recording', { method: 'POST' })
    .then(response => response.json())
    .then(data => res.json(data))
    .catch(err => res.status(500).json({ error: err }));
});

app.post('/update_config', (req, res) => {
  fetch('http://localhost:5000/update_config', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req.body)
  })
    .then(response => response.json())
    .then(data => res.json(data))
    .catch(err => res.status(500).json({ error: err }));
});

app.listen(port, () => {
  console.log(`Web UI running at http://localhost:${port}`);
});
