import 'dotenv/config';
import { Server } from './mcp/server';
import { registerReconTools } from './tools/recon';
import { registerJsTools } from './tools/js';
import { registerSecurityTools } from './tools/security';
import { registerCSRFTools } from './tools/csrf';
import { registerApiTools } from './tools/api';
import { registerAuthTools } from './tools/auth';
import { registerCloudTools } from './tools/cloud';
import { registerScannerTools } from './tools/scanner';
import { registerReportTools } from './tools/report';
// Burp and Caido integrations are optional (excluded from public repo)
let registerBurpTools: any = null;
let registerCaidoTools: any = null;
try {
  registerBurpTools = require('./tools/burp').registerBurpTools;
} catch (e) {
  // Burp integration not available
}
try {
  registerCaidoTools = require('./tools/caido').registerCaidoTools;
} catch (e) {
  // Caido integration not available
}

import { registerRenderTools, closeBrowser } from './tools/render';
import { registerDatabaseTools } from './tools/database';
import { registerTrainingTools } from './tools/training';
import { registerTrainingExtractorTools } from './tools/training_extractor';
import { registerZAPTools } from './tools/zap';
import { registerWordlistTools } from './tools/wordlist';
import { registerGraphTools } from './tools/graph';
import { initPostgres } from './integrations/postgres';
import { initRedis } from './integrations/redis';

const server = new Server({
  name: 'bugbounty-mcp',
  version: '1.1.1',
});

// Register all tool modules
registerReconTools(server);
registerJsTools(server);
registerSecurityTools(server);
registerCSRFTools(server);
registerApiTools(server);
registerAuthTools(server);
registerCloudTools(server);
registerScannerTools(server);
registerReportTools(server);
if (registerBurpTools) {
  registerBurpTools(server);
}
registerRenderTools(server);
if (registerCaidoTools) {
  registerCaidoTools(server);
}
registerDatabaseTools(server);
registerTrainingTools(server);
registerTrainingExtractorTools(server);
registerZAPTools(server);
registerWordlistTools(server);
registerGraphTools(server);

// Initialize connections
async function initialize() {
  try {
    // Initialize PostgreSQL (non-blocking)
    try {
      initPostgres();
      console.error('PostgreSQL connection initialized');
    } catch (error) {
      console.error('PostgreSQL initialization failed:', error);
    }

    // Initialize Redis (non-blocking, optional)
    try {
      const redisInit = initRedis();
      if (redisInit) {
        console.error('✓ Redis connection initialized');
      } else {
        console.error('ℹ Redis not available (optional - server will work without it)');
      }
    } catch (error) {
      console.error('ℹ Redis not available (optional - server will work without it)');
    }
  } catch (error) {
    console.error('Initialization error:', error);
  }
}

// Start server
server.on('start', () => {
  console.error('🚀 Bug Bounty MCP Server started!');
  console.error('Available tool categories:');
  console.error('  - recon.* : Reconnaissance tools (subfinder, httpx, amass, dns, gau, ffuf)');
  console.error('  - js.* : JavaScript analysis (download, beautify, endpoints, secrets)');
  console.error('  - security.* : Security testing (XSS, SQLi, IDOR, CSP, auth bypass)');
  console.error('  - api.* : API testing (GraphQL, rate limit, BOLA, swagger)');
  console.error('  - auth.* : Auth attacks (JWT, OAuth, session, reset, MFA)');
  console.error('  - cloud.* : Cloud misconfig (S3, Azure, GCP, keys, tfstate)');
  console.error('  - scanner.* : Target flow orchestration');
  console.error('  - report.* : Report generation');
  console.error('  - wordlist.* : Wordlist generation (directories, files, parameters, combined)');
  console.error('  - graph.* : Graph analysis and pattern detection (nodes, edges, patterns, clusters)');
  if (registerBurpTools) {
    console.error('  - burp.* : Burp Suite integration (search, send_raw, get_traffic)');
  }
  if (registerCaidoTools) {
    console.error('  - caido.* : Caido integration (query, search, analyze_auth)');
  }
  console.error('  - render.* : Rendering tools (screenshot, extract_dom, extract_forms)');
  console.error('  - db.* : Database operations (save_finding, get_findings, init)');
  console.error('  - training.* : Training data (import, match, stats, extract_from_writeup)');
  console.error('  - security.test_csrf : Advanced CSRF testing with PoC generation');
  console.error('  - zap.* : ZAP integration (spider, active_scan, alerts, proxy_process)');
  console.error('\nServer ready for MCP connections!');
});

// Error handlers
process.on('unhandledRejection', (reason, promise) => {
  console.error('Unhandled Rejection at:', promise, 'reason:', reason);
});

process.on('uncaughtException', (error) => {
  console.error('Uncaught Exception:', error);
  // Don't exit immediately - let the server try to handle it
});

// Graceful shutdown
process.on('SIGINT', async () => {
  console.error('\nShutting down...');
  await closeBrowser();
  process.exit(0);
});

process.on('SIGTERM', async () => {
  console.error('\nShutting down...');
  await closeBrowser();
  process.exit(0);
});

// Start
(async () => {
  await initialize();
  await server.start();
})();

