import { Server } from '../mcp/server';
import { formatToolResult } from '../types';
import { ToolResult } from '../types';
import * as fs from 'fs-extra';
import * as path from 'path';

// Safe wordlists for bug bounty testing
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

/**
 * Generate safe wordlist for directory/file discovery
 */
function generateDirectoryWordlist(): string[] {
  return SAFE_DIRECTORIES;
}

/**
 * Generate safe wordlist for file discovery
 */
function generateFileWordlist(): string[] {
  return SAFE_FILES;
}

/**
 * Generate safe wordlist for parameter fuzzing
 */
function generateParameterWordlist(): string[] {
  return SAFE_PARAMETERS;
}

/**
 * Generate combined wordlist
 */
function generateCombinedWordlist(): string[] {
  return [
    ...SAFE_DIRECTORIES,
    ...SAFE_FILES,
    ...SAFE_PARAMETERS,
  ];
}

/**
 * Generate wordlist with extensions
 */
function generateWordlistWithExtensions(baseWordlist: string[], extensions: string[]): string[] {
  const result: string[] = [];
  
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

export function registerWordlistTools(server: Server) {
  // Generate directory wordlist
  server.tool(
    'wordlist.generate_directories',
    {
      description: 'Generate a safe wordlist for directory/file discovery',
      inputSchema: {
        type: 'object',
        properties: {
          output: {
            type: 'string',
            description: 'Output file path (optional, if not provided returns as data)',
          },
          withExtensions: {
            type: 'boolean',
            description: 'Include common file extensions',
            default: false,
          },
        },
        required: [],
      },
    },
    async ({ output, withExtensions = false }: any): Promise<ToolResult> => {
      try {
        let wordlist = generateDirectoryWordlist();
        
        if (withExtensions) {
          wordlist = generateWordlistWithExtensions(wordlist, SAFE_EXTENSIONS);
        }

        if (output) {
          const outputPath = path.resolve(output);
          await fs.ensureDir(path.dirname(outputPath));
          await fs.writeFile(outputPath, wordlist.join('\n'), 'utf-8');
          
          return formatToolResult(true, {
            wordlist: wordlist,
            count: wordlist.length,
            output: outputPath,
            message: `Wordlist saved to ${outputPath}`,
          });
        }

        return formatToolResult(true, {
          wordlist,
          count: wordlist.length,
        });
      } catch (error: any) {
        return formatToolResult(false, null, error.message);
      }
    }
  );

  // Generate file wordlist
  server.tool(
    'wordlist.generate_files',
    {
      description: 'Generate a safe wordlist for file discovery',
      inputSchema: {
        type: 'object',
        properties: {
          output: {
            type: 'string',
            description: 'Output file path (optional)',
          },
        },
        required: [],
      },
    },
    async ({ output }: any): Promise<ToolResult> => {
      try {
        const wordlist = generateFileWordlist();

        if (output) {
          const outputPath = path.resolve(output);
          await fs.ensureDir(path.dirname(outputPath));
          await fs.writeFile(outputPath, wordlist.join('\n'), 'utf-8');
          
          return formatToolResult(true, {
            wordlist,
            count: wordlist.length,
            output: outputPath,
            message: `Wordlist saved to ${outputPath}`,
          });
        }

        return formatToolResult(true, {
          wordlist,
          count: wordlist.length,
        });
      } catch (error: any) {
        return formatToolResult(false, null, error.message);
      }
    }
  );

  // Generate parameter wordlist
  server.tool(
    'wordlist.generate_parameters',
    {
      description: 'Generate a safe wordlist for parameter fuzzing',
      inputSchema: {
        type: 'object',
        properties: {
          output: {
            type: 'string',
            description: 'Output file path (optional)',
          },
        },
        required: [],
      },
    },
    async ({ output }: any): Promise<ToolResult> => {
      try {
        const wordlist = generateParameterWordlist();

        if (output) {
          const outputPath = path.resolve(output);
          await fs.ensureDir(path.dirname(outputPath));
          await fs.writeFile(outputPath, wordlist.join('\n'), 'utf-8');
          
          return formatToolResult(true, {
            wordlist,
            count: wordlist.length,
            output: outputPath,
            message: `Wordlist saved to ${outputPath}`,
          });
        }

        return formatToolResult(true, {
          wordlist,
          count: wordlist.length,
        });
      } catch (error: any) {
        return formatToolResult(false, null, error.message);
      }
    }
  );

  // Generate combined wordlist
  server.tool(
    'wordlist.generate_combined',
    {
      description: 'Generate a combined safe wordlist (directories + files + parameters)',
      inputSchema: {
        type: 'object',
        properties: {
          output: {
            type: 'string',
            description: 'Output file path (optional)',
          },
          withExtensions: {
            type: 'boolean',
            description: 'Include common file extensions for directories',
            default: false,
          },
        },
        required: [],
      },
    },
    async ({ output, withExtensions = false }: any): Promise<ToolResult> => {
      try {
        let wordlist = generateCombinedWordlist();
        
        if (withExtensions) {
          const dirs = generateDirectoryWordlist();
          const dirsWithExt = generateWordlistWithExtensions(dirs, SAFE_EXTENSIONS);
          wordlist = [...new Set([...dirsWithExt, ...SAFE_FILES, ...SAFE_PARAMETERS])];
        }

        if (output) {
          const outputPath = path.resolve(output);
          await fs.ensureDir(path.dirname(outputPath));
          await fs.writeFile(outputPath, wordlist.join('\n'), 'utf-8');
          
          return formatToolResult(true, {
            wordlist,
            count: wordlist.length,
            output: outputPath,
            message: `Wordlist saved to ${outputPath}`,
          });
        }

        return formatToolResult(true, {
          wordlist,
          count: wordlist.length,
        });
      } catch (error: any) {
        return formatToolResult(false, null, error.message);
      }
    }
  );

  // Generate custom wordlist
  server.tool(
    'wordlist.generate_custom',
    {
      description: 'Generate a custom wordlist from provided words',
      inputSchema: {
        type: 'object',
        properties: {
          words: {
            type: 'array',
            items: { type: 'string' },
            description: 'Array of words to include in wordlist',
          },
          output: {
            type: 'string',
            description: 'Output file path (optional)',
          },
          withExtensions: {
            type: 'boolean',
            description: 'Add common file extensions to each word',
            default: false,
          },
        },
        required: ['words'],
      },
    },
    async ({ words, output, withExtensions = false }: any): Promise<ToolResult> => {
      try {
        let wordlist: string[] = [...new Set(words as string[])]; // Remove duplicates
        
        if (withExtensions) {
          wordlist = generateWordlistWithExtensions(wordlist, SAFE_EXTENSIONS);
        }

        if (output) {
          const outputPath = path.resolve(output);
          await fs.ensureDir(path.dirname(outputPath));
          await fs.writeFile(outputPath, wordlist.join('\n'), 'utf-8');
          
          return formatToolResult(true, {
            wordlist,
            count: wordlist.length,
            output: outputPath,
            message: `Wordlist saved to ${outputPath}`,
          });
        }

        return formatToolResult(true, {
          wordlist,
          count: wordlist.length,
        });
      } catch (error: any) {
        return formatToolResult(false, null, error.message);
      }
    }
  );
}

