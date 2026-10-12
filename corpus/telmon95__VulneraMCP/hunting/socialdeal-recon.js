#!/usr/bin/env node

/**
 * Social Deal Reconnaissance Script
 * Systematic reconnaissance following program rules
 */

require('dotenv').config();
const axios = require('axios');
const RateLimiter = require('./rate-limiter');
const config = require('./socialdeal-config.json');
const { initPostgres, saveFinding } = require('../dist/integrations/postgres');

const rateLimiter = new RateLimiter(config.rateLimit.maxRequestsPerSecond);

async function saveFindingToDB(target, type, severity, description, payload, response, score) {
  try {
    const pool = initPostgres();
    const client = await pool.connect();
    try {
      await client.query(
        `INSERT INTO findings (target, type, severity, description, payload, response, score, timestamp)
         VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
         RETURNING id`,
        [target, type, severity, description, payload || null, response || null, score || 0]
      );
      console.log(`✅ Finding saved: ${type} on ${target}`);
    } finally {
      client.release();
    }
  } catch (error) {
    console.error(`❌ Error saving finding: ${error.message}`);
  }
}

async function testEndpoint(url, method = 'GET', headers = {}, body = null) {
  try {
    const result = await rateLimiter.execute(async () => {
      const response = await axios({
        method,
        url,
        headers: {
          'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
          ...headers
        },
        data: body,
        timeout: 10000,
        validateStatus: () => true // Accept all status codes
      });
      return response;
    });

    return {
      url,
      method,
      status: result.status,
      headers: result.headers,
      body: result.data,
      size: JSON.stringify(result.data).length
    };
  } catch (error) {
    return {
      url,
      method,
      error: error.message
    };
  }
}

async function runReconnaissance() {
  console.log('🔍 Starting Social Deal Reconnaissance');
  console.log(`📋 Rate Limit: ${config.rateLimit.maxRequestsPerSecond} requests/second`);
  console.log('');

  const findings = [];

  // Test main domain
  console.log('1️⃣  Testing main domain: www.socialdeal.nl');
  const mainDomain = await testEndpoint('https://www.socialdeal.nl');
  console.log(`   Status: ${mainDomain.status}`);
  
  // Check for security headers
  const securityHeaders = {
    'Content-Security-Policy': mainDomain.headers['content-security-policy'],
    'X-Frame-Options': mainDomain.headers['x-frame-options'],
    'X-Content-Type-Options': mainDomain.headers['x-content-type-options'],
    'Strict-Transport-Security': mainDomain.headers['strict-transport-security'],
    'X-XSS-Protection': mainDomain.headers['x-xss-protection']
  };
  
  const missingHeaders = Object.entries(securityHeaders)
    .filter(([key, value]) => !value)
    .map(([key]) => key);
  
  if (missingHeaders.length > 0) {
    console.log(`   ⚠️  Missing security headers: ${missingHeaders.join(', ')}`);
    // Note: Missing headers are out of scope, but good to note
  }

  // Test in-scope URLs
  console.log('\n2️⃣  Testing in-scope URLs');
  for (const url of config.inScope.urls) {
    const result = await testEndpoint(url);
    console.log(`   ${url}: ${result.status || 'Error'}`);
  }

  // Check for exposed files/directories
  console.log('\n3️⃣  Checking for common exposed files/directories');
  const commonPaths = [
    '/robots.txt',
    '/sitemap.xml',
    '/.env',
    '/.git/config',
    '/phpinfo.php',
    '/info.php',
    '/server-status',
    '/.well-known/security.txt'
  ];

  for (const path of commonPaths) {
    const url = `https://www.socialdeal.nl${path}`;
    const result = await testEndpoint(url);
    if (result.status === 200) {
      console.log(`   ✅ Found: ${path} (Status: ${result.status})`);
      if (path === '/.env' || path === '/.git/config') {
        await saveFindingToDB(
          url,
          'Information Disclosure',
          'medium',
          `Exposed file found: ${path}`,
          null,
          JSON.stringify(result.body).substring(0, 1000),
          5
        );
      }
    }
  }

  console.log('\n✅ Reconnaissance complete!');
  console.log('📊 Check dashboard at http://localhost:3000 to view findings');
}

// Run if called directly
if (require.main === module) {
  runReconnaissance().catch(console.error);
}

module.exports = { testEndpoint, saveFindingToDB, runReconnaissance };


