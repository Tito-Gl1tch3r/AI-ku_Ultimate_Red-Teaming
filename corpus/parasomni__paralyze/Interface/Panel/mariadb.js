const mariadb = require('mariadb');

async function logShutdownEvent() {
  const conn = await pool.getConnection();
  await conn.query("INSERT INTO events (type) VALUES ('shutdown')");
  conn.release();
}

module.exports = { logShutdownEvent };

// mariadb.js
import mariadb from 'mariadb';

export async function checkMariaDBConnection() {
  let conn;
  try {
    conn = await mariadb.createConnection({
      host: 'localhost',
      user: 'root',
      password: 'sup3rS3cur3P@ssw0rd',
      database: 'botNetwork'
    });
    await conn.query("SELECT 1");
    return true;
  } catch (err) {
    console.error("MariaDB connection error:", err.message);
    return false;
  } finally {
    if (conn) conn.end();
  }
}

import fs from 'fs';
import mariadb from 'mariadb';

function parseConfig(filePath) {
  const config = {};
  const lines = fs.readFileSync(filePath, 'utf8').split('\n');
  for (const line of lines) {
    const [key, value] = line.trim().split('=');
    if (key && value) config[key] = value;
  }
  return config;
}

export async function checkMariaDBConnection() {
  const config = parseConfig('db_controller.conf');
  let conn;
  try {
    conn = await mariadb.createConnection({
      host: config.server,
      port: parseInt(config.port),
      user: config.user,
      password: config.password,
      database: config.database
    });
    await conn.query("SELECT 1");
    return true;
  } catch (err) {
    console.error("MariaDB connection error:", err.message);
    return false;
  } finally {
    if (conn) conn.end();
  }
}
