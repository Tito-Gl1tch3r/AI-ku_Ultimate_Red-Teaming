import { Server } from '../mcp/server';
import puppeteer, { Browser, Page } from 'puppeteer';
import { formatToolResult, ToolResult } from '../types';
import * as fs from 'fs-extra';
import * as path from 'path';

let browser: Browser | null = null;

async function getBrowser(): Promise<Browser> {
  if (!browser) {
    browser = await puppeteer.launch({
      headless: true,
      args: ['--no-sandbox', '--disable-setuid-sandbox'],
    });
  }
  return browser;
}

export function registerRenderTools(server: Server) {
  // Take screenshot
  server.tool(
    'render.screenshot',
    {
      description: 'Take a screenshot of a webpage',
      inputSchema: {
        type: 'object',
        properties: {
          url: { type: 'string', description: 'URL to screenshot' },
          fullPage: { type: 'boolean', description: 'Capture full page', default: false },
          waitTime: { type: 'number', description: 'Wait time in ms before screenshot', default: 2000 },
        },
        required: ['url'],
      },
    },
    async ({ url, fullPage = false, waitTime = 2000 }: any): Promise<ToolResult> => {
      let page: Page | null = null;
      try {
        const browserInstance = await getBrowser();
        page = await browserInstance.newPage();
        
        await page.setViewport({ width: 1920, height: 1080 });
        await page.goto(url, { waitUntil: 'networkidle2', timeout: 30000 });
        await new Promise(resolve => setTimeout(resolve, waitTime));

        const screenshotsDir = path.join(process.cwd(), 'screenshots');
        await fs.ensureDir(screenshotsDir);
        
        const filename = `screenshot_${Date.now()}.png`;
        const filepath = path.join(screenshotsDir, filename);
        
        await page.screenshot({
          path: filepath,
          fullPage,
        });

        await page.close();

        return formatToolResult(true, {
          url,
          screenshot: filepath,
          filename,
        });
      } catch (error: any) {
        if (page) await page.close().catch(() => {});
        return formatToolResult(false, null, error.message);
      }
    }
  );

  // Extract DOM
  server.tool(
    'render.extract_dom',
    {
      description: 'Extract and return the DOM structure of a webpage',
      inputSchema: {
        type: 'object',
        properties: {
          url: { type: 'string', description: 'URL to extract DOM from' },
          waitTime: { type: 'number', description: 'Wait time in ms', default: 2000 },
        },
        required: ['url'],
      },
    },
    async ({ url, waitTime = 2000 }: any): Promise<ToolResult> => {
      let page: Page | null = null;
      try {
        const browserInstance = await getBrowser();
        page = await browserInstance.newPage();
        
        await page.goto(url, { waitUntil: 'networkidle2', timeout: 30000 });
        await new Promise(resolve => setTimeout(resolve, waitTime));

        const html = await page.content();
        const title = await page.title();
        const forms = await page.$$eval('form', (forms) =>
          forms.map((form) => ({
            action: form.action,
            method: form.method,
            inputs: Array.from(form.querySelectorAll('input')).map((input: any) => ({
              name: input.name,
              type: input.type,
              id: input.id,
            })),
          }))
        );

        const links = await page.$$eval('a', (links) =>
          links.map((link: any) => ({
            href: link.href,
            text: link.textContent?.trim(),
          }))
        );

        await page.close();

        return formatToolResult(true, {
          url,
          title,
          html: html.substring(0, 50000), // Limit size
          forms,
          links: links.slice(0, 100), // Limit links
          summary: {
            formsCount: forms.length,
            linksCount: links.length,
          },
        });
      } catch (error: any) {
        if (page) await page.close().catch(() => {});
        return formatToolResult(false, null, error.message);
      }
    }
  );

  // Extract forms
  server.tool(
    'render.extract_forms',
    {
      description: 'Extract all forms from a webpage',
      inputSchema: {
        type: 'object',
        properties: {
          url: { type: 'string', description: 'URL to extract forms from' },
        },
        required: ['url'],
      },
    },
    async ({ url }: any): Promise<ToolResult> => {
      let page: Page | null = null;
      try {
        const browserInstance = await getBrowser();
        page = await browserInstance.newPage();
        
        await page.goto(url, { waitUntil: 'networkidle2', timeout: 30000 });

        const forms = await page.$$eval('form', (forms) =>
          forms.map((form, index) => ({
            index,
            action: form.action,
            method: form.method,
            enctype: form.enctype,
            inputs: Array.from(form.querySelectorAll('input')).map((input: any) => ({
              name: input.name,
              type: input.type,
              id: input.id,
              placeholder: input.placeholder,
              required: input.required,
            })),
            textareas: Array.from(form.querySelectorAll('textarea')).map((textarea: any) => ({
              name: textarea.name,
              id: textarea.id,
              placeholder: textarea.placeholder,
            })),
            selects: Array.from(form.querySelectorAll('select')).map((select: any) => ({
              name: select.name,
              id: select.id,
              options: Array.from(select.options).map((opt: any) => opt.value),
            })),
          }))
        );

        await page.close();

        return formatToolResult(true, {
          url,
          forms,
          count: forms.length,
        });
      } catch (error: any) {
        if (page) await page.close().catch(() => {});
        return formatToolResult(false, null, error.message);
      }
    }
  );

  // Execute JavaScript in page context
  server.tool(
    'render.execute_js',
    {
      description: 'Execute JavaScript in the context of a webpage',
      inputSchema: {
        type: 'object',
        properties: {
          url: { type: 'string', description: 'URL to load' },
          script: { type: 'string', description: 'JavaScript code to execute' },
        },
        required: ['url', 'script'],
      },
    },
    async ({ url, script }: any): Promise<ToolResult> => {
      let page: Page | null = null;
      try {
        const browserInstance = await getBrowser();
        page = await browserInstance.newPage();
        
        await page.goto(url, { waitUntil: 'networkidle2', timeout: 30000 });

        const result = await page.evaluate((scriptToRun) => {
          try {
            return eval(scriptToRun);
          } catch (e) {
            return { error: e instanceof Error ? e.message : String(e) };
          }
        }, script);

        await page.close();

        return formatToolResult(true, {
          url,
          result,
        });
      } catch (error: any) {
        if (page) await page.close().catch(() => {});
        return formatToolResult(false, null, error.message);
      }
    }
  );
}

// Cleanup function
export async function closeBrowser(): Promise<void> {
  if (browser) {
    await browser.close();
    browser = null;
  }
}

