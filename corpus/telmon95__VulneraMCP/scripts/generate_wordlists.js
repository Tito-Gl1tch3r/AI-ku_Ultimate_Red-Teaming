#!/usr/bin/env node

/**
 * Generate safe wordlists for bug bounty testing
 * These wordlists are designed to be safe and legal for testing
 */

const fs = require('fs');
const path = require('path');

const SAFE_DIRECTORIES = [
  // Common directories
  'admin', 'administrator', 'api', 'app', 'assets', 'backup', 'backups',
  'bin', 'blog', 'cdn', 'config', 'css', 'dashboard', 'data', 'db',
  'dev', 'docs', 'download', 'downloads', 'email', 'files', 'ftp',
  'git', 'help', 'images', 'img', 'includes', 'index', 'js', 'lib',
  'login', 'logs', 'mail', 'media', 'mobile', 'old', 'panel', 'php',
  'private', 'public', 'secure', 'server', 'site', 'src', 'static',
  'store', 'test', 'tmp', 'tools', 'uploads', 'user', 'users', 'www',
  // API endpoints
  'v1', 'v2', 'api/v1', 'api/v2', 'rest', 'graphql', 'webhook',
  // Common files
  '.env', '.git', '.svn', '.htaccess', 'robots.txt', 'sitemap.xml',
  'config.php', 'config.json', 'package.json', 'composer.json',
  // Admin panels
  'admin.php', 'admin.html', 'wp-admin', 'administrator',
  // Testing endpoints
  'test', 'testing', 'staging', 'dev', 'development',
];

const SAFE_FILES = [
  // Configuration files
  '.env', '.env.local', '.env.production', '.env.development',
  'config.php', 'config.json', 'config.yaml', 'config.yml',
  'settings.php', 'settings.json', 'application.properties',
  'web.xml', 'pom.xml', 'package.json', 'composer.json',
  // Documentation
  'README.md', 'README.txt', 'CHANGELOG.md', 'LICENSE',
  'robots.txt', 'sitemap.xml', 'sitemap.txt',
  // Common files
  'index.php', 'index.html', 'index.jsp', 'index.aspx',
  'login.php', 'login.html', 'logout.php',
  'admin.php', 'admin.html', 'admin.jsp',
  // Backup files
  'backup.sql', 'backup.tar', 'backup.zip', 'backup.tar.gz',
  'database.sql', 'dump.sql',
  // Log files
  'access.log', 'error.log', 'debug.log', 'application.log',
];

const SAFE_PARAMETERS = [
  // Common parameters
  'id', 'user', 'user_id', 'username', 'email', 'password',
  'token', 'api_key', 'key', 'secret', 'auth', 'session',
  'page', 'limit', 'offset', 'sort', 'order', 'filter',
  'q', 'query', 'search', 'term', 'keyword',
  'action', 'method', 'cmd', 'command', 'exec',
  'file', 'path', 'dir', 'directory', 'url', 'uri',
  'redirect', 'return', 'callback', 'next', 'continue',
  // API parameters
  'api_key', 'api_token', 'access_token', 'bearer',
  'client_id', 'client_secret', 'oauth_token',
  // Testing parameters
  'test', 'debug', 'verbose', 'format', 'output',
];

const SAFE_EXTENSIONS = [
  '.php', '.jsp', '.asp', '.aspx', '.html', '.htm',
  '.json', '.xml', '.yaml', '.yml', '.txt', '.md',
  '.sql', '.log', '.bak', '.backup', '.old', '.tmp',
  '.zip', '.tar', '.tar.gz', '.gz',
];

function generateWordlistWithExtensions(baseWordlist, extensions) {
  const result = [];
  
  for (const word of baseWordlist) {
    result.push(word);
    for (const ext of extensions) {
      if (!word.endsWith(ext)) {
        result.push(`${word}${ext}`);
      }
    }
  }
  
  return [...new Set(result)]; // Remove duplicates
}

// Create wordlists directory
const wordlistsDir = path.join(__dirname, '..', 'wordlists');
if (!fs.existsSync(wordlistsDir)) {
  fs.mkdirSync(wordlistsDir, { recursive: true });
}

// Generate directory wordlist
const directories = SAFE_DIRECTORIES.join('\n');
fs.writeFileSync(path.join(wordlistsDir, 'directories.txt'), directories);
console.log(`✓ Generated directories.txt (${SAFE_DIRECTORIES.length} entries)`);

// Generate directory wordlist with extensions
const directoriesWithExt = generateWordlistWithExtensions(SAFE_DIRECTORIES, SAFE_EXTENSIONS);
fs.writeFileSync(path.join(wordlistsDir, 'directories-extensions.txt'), directoriesWithExt.join('\n'));
console.log(`✓ Generated directories-extensions.txt (${directoriesWithExt.length} entries)`);

// Generate file wordlist
const files = SAFE_FILES.join('\n');
fs.writeFileSync(path.join(wordlistsDir, 'files.txt'), files);
console.log(`✓ Generated files.txt (${SAFE_FILES.length} entries)`);

// Generate parameter wordlist
const parameters = SAFE_PARAMETERS.join('\n');
fs.writeFileSync(path.join(wordlistsDir, 'parameters.txt'), parameters);
console.log(`✓ Generated parameters.txt (${SAFE_PARAMETERS.length} entries)`);

// Generate combined wordlist
const combined = [...new Set([...SAFE_DIRECTORIES, ...SAFE_FILES, ...SAFE_PARAMETERS])];
fs.writeFileSync(path.join(wordlistsDir, 'combined.txt'), combined.join('\n'));
console.log(`✓ Generated combined.txt (${combined.length} entries)`);

// Generate combined wordlist with extensions
const combinedWithExt = [...new Set([...directoriesWithExt, ...SAFE_FILES, ...SAFE_PARAMETERS])];
fs.writeFileSync(path.join(wordlistsDir, 'combined-extensions.txt'), combinedWithExt.join('\n'));
console.log(`✓ Generated combined-extensions.txt (${combinedWithExt.length} entries)`);

console.log(`\n✅ All wordlists generated in ${wordlistsDir}/`);
console.log('\nWordlist files:');
console.log('  - directories.txt : Directory discovery wordlist');
console.log('  - directories-extensions.txt : Directories with file extensions');
console.log('  - files.txt : File discovery wordlist');
console.log('  - parameters.txt : Parameter fuzzing wordlist');
console.log('  - combined.txt : Combined wordlist (all categories)');
console.log('  - combined-extensions.txt : Combined with extensions');







