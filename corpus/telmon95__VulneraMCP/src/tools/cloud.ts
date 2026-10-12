import { Server } from '../mcp/server';
import axios from 'axios';
import { formatToolResult, ToolResult } from '../types';
import { saveFinding, saveTestResult } from '../integrations/postgres';

function isXmlListing(body: string): boolean {
  const normalized = body.toLowerCase();
  return normalized.includes('listbucketresult') || normalized.includes('enumerationresults');
}

function scanKeys(source: string): any {
  const awsKeyPattern = /AKIA[0-9A-Z]{16}/g;
  const awsSecretPattern = /(?:aws_secret_access_key|aws_secret)[\s:=]+["'`]?([A-Za-z0-9/+=]{40})/gi;
  const gcpKeyPattern = /AIza[0-9A-Za-z\-_]{35}/g;
  const azureKeyPattern = /(?:AccountKey=)([A-Za-z0-9+/=]{80,})/g;

  const matches = {
    awsKeys: Array.from(new Set(source.match(awsKeyPattern) || [])),
    awsSecrets: [] as string[],
    gcpKeys: Array.from(new Set(source.match(gcpKeyPattern) || [])),
    azureKeys: Array.from(new Set(source.match(azureKeyPattern) || [])),
  };

  let match: RegExpExecArray | null;
  while ((match = awsSecretPattern.exec(source)) !== null) {
    matches.awsSecrets.push(match[1]);
  }
  matches.awsSecrets = Array.from(new Set(matches.awsSecrets));

  return matches;
}

export function registerCloudTools(server: Server) {
  // S3 bucket enumeration
  server.tool(
    'cloud.s3_enum',
    {
      description: 'Check S3 buckets for public listing',
      inputSchema: {
        type: 'object',
        properties: {
          buckets: { type: 'array', items: { type: 'string' } },
        },
        required: ['buckets'],
      },
    },
    async ({ buckets }: any): Promise<ToolResult> => {
      try {
        const results: any[] = [];
        for (const bucket of buckets) {
          const url = `https://${bucket}.s3.amazonaws.com/`;
          const response = await axios.get(url, { validateStatus: () => true, timeout: 15000 });
          const body = typeof response.data === 'string' ? response.data : JSON.stringify(response.data);
          const publicListing = response.status === 200 && isXmlListing(body);

          if (publicListing) {
            await saveFinding({
              target: url,
              type: 'Public S3 Bucket',
              severity: 'high',
              description: `Public listing detected for S3 bucket: ${bucket}`,
              response: body.substring(0, 1000),
              timestamp: new Date(),
              score: 8,
            });
          }

          results.push({ bucket, status: response.status, publicListing });
        }

        await saveTestResult('cloud.s3_enum', 'cloud_s3_enum', true, { results });

        return formatToolResult(true, { results });
      } catch (error: any) {
        return formatToolResult(false, null, error.message);
      }
    }
  );

  // Azure Blob enumeration
  server.tool(
    'cloud.azure_blob_enum',
    {
      description: 'Check Azure Blob storage for public listing',
      inputSchema: {
        type: 'object',
        properties: {
          account: { type: 'string' },
          containers: { type: 'array', items: { type: 'string' } },
        },
        required: ['account'],
      },
    },
    async ({ account, containers = [] }: any): Promise<ToolResult> => {
      try {
        const results: any[] = [];
        const rootUrl = `https://${account}.blob.core.windows.net/?comp=list`;
        const rootResp = await axios.get(rootUrl, { validateStatus: () => true, timeout: 15000 });
        const rootBody = typeof rootResp.data === 'string' ? rootResp.data : JSON.stringify(rootResp.data);
        const rootPublic = rootResp.status === 200 && isXmlListing(rootBody);

        results.push({ scope: 'account', status: rootResp.status, publicListing: rootPublic });

        if (rootPublic) {
          await saveFinding({
            target: rootUrl,
            type: 'Public Azure Blob',
            severity: 'high',
            description: `Public Azure blob account listing: ${account}`,
            response: rootBody.substring(0, 1000),
            timestamp: new Date(),
            score: 8,
          });
        }

        for (const container of containers) {
          const url = `https://${account}.blob.core.windows.net/${container}?restype=container&comp=list`;
          const response = await axios.get(url, { validateStatus: () => true, timeout: 15000 });
          const body = typeof response.data === 'string' ? response.data : JSON.stringify(response.data);
          const publicListing = response.status === 200 && isXmlListing(body);

          if (publicListing) {
            await saveFinding({
              target: url,
              type: 'Public Azure Blob',
              severity: 'high',
              description: `Public Azure container listing: ${container}`,
              response: body.substring(0, 1000),
              timestamp: new Date(),
              score: 8,
            });
          }

          results.push({ scope: container, status: response.status, publicListing });
        }

        await saveTestResult('cloud.azure_blob_enum', 'cloud_azure_enum', true, { results });

        return formatToolResult(true, { results });
      } catch (error: any) {
        return formatToolResult(false, null, error.message);
      }
    }
  );

  // GCP bucket enumeration
  server.tool(
    'cloud.gcp_bucket_enum',
    {
      description: 'Check GCP buckets for public listing',
      inputSchema: {
        type: 'object',
        properties: {
          buckets: { type: 'array', items: { type: 'string' } },
        },
        required: ['buckets'],
      },
    },
    async ({ buckets }: any): Promise<ToolResult> => {
      try {
        const results: any[] = [];
        for (const bucket of buckets) {
          const url = `https://storage.googleapis.com/${bucket}/`;
          const response = await axios.get(url, { validateStatus: () => true, timeout: 15000 });
          const body = typeof response.data === 'string' ? response.data : JSON.stringify(response.data);
          const publicListing = response.status === 200 && isXmlListing(body);

          if (publicListing) {
            await saveFinding({
              target: url,
              type: 'Public GCP Bucket',
              severity: 'high',
              description: `Public listing detected for GCP bucket: ${bucket}`,
              response: body.substring(0, 1000),
              timestamp: new Date(),
              score: 8,
            });
          }

          results.push({ bucket, status: response.status, publicListing });
        }

        await saveTestResult('cloud.gcp_bucket_enum', 'cloud_gcp_enum', true, { results });

        return formatToolResult(true, { results });
      } catch (error: any) {
        return formatToolResult(false, null, error.message);
      }
    }
  );

  // Exposed keys scan
  server.tool(
    'cloud.exposed_keys_scan',
    {
      description: 'Scan content for exposed cloud keys and secrets',
      inputSchema: {
        type: 'object',
        properties: {
          source: { type: 'string' },
        },
        required: ['source'],
      },
    },
    async ({ source }: any): Promise<ToolResult> => {
      try {
        return formatToolResult(true, { matches: scanKeys(source) });
      } catch (error: any) {
        return formatToolResult(false, null, error.message);
      }
    }
  );

  server.tool(
    'cloud.detect_keys_in_js',
    {
      description: 'Detect cloud keys in JavaScript content',
      inputSchema: {
        type: 'object',
        properties: {
          source: { type: 'string' },
        },
        required: ['source'],
      },
    },
    async ({ source }: any): Promise<ToolResult> => {
      try {
        return formatToolResult(true, { matches: scanKeys(source) });
      } catch (error: any) {
        return formatToolResult(false, null, error.message);
      }
    }
  );

  server.tool(
    'cloud.detect_keys_in_html',
    {
      description: 'Detect cloud keys in HTML content',
      inputSchema: {
        type: 'object',
        properties: {
          source: { type: 'string' },
        },
        required: ['source'],
      },
    },
    async ({ source }: any): Promise<ToolResult> => {
      try {
        return formatToolResult(true, { matches: scanKeys(source) });
      } catch (error: any) {
        return formatToolResult(false, null, error.message);
      }
    }
  );

  server.tool(
    'cloud.detect_keys_in_env',
    {
      description: 'Detect cloud keys in .env content',
      inputSchema: {
        type: 'object',
        properties: {
          source: { type: 'string' },
        },
        required: ['source'],
      },
    },
    async ({ source }: any): Promise<ToolResult> => {
      try {
        return formatToolResult(true, { matches: scanKeys(source) });
      } catch (error: any) {
        return formatToolResult(false, null, error.message);
      }
    }
  );

  server.tool(
    'cloud.bucket_permission_probe',
    {
      description: 'Probe bucket permissions (read/list only, no writes)',
      inputSchema: {
        type: 'object',
        properties: {
          provider: { type: 'string', enum: ['s3', 'azure', 'gcp'] },
          bucket: { type: 'string' },
          account: { type: 'string' },
          container: { type: 'string' },
        },
        required: ['provider'],
      },
    },
    async ({ provider, bucket, account, container }: any): Promise<ToolResult> => {
      try {
        let url = '';
        if (provider === 's3' && bucket) {
          url = `https://${bucket}.s3.amazonaws.com/`;
        } else if (provider === 'gcp' && bucket) {
          url = `https://storage.googleapis.com/${bucket}/`;
        } else if (provider === 'azure' && account && container) {
          url = `https://${account}.blob.core.windows.net/${container}?restype=container&comp=list`;
        } else {
          return formatToolResult(false, null, 'Missing bucket/account/container');
        }

        const headResp = await axios.head(url, { validateStatus: () => true, timeout: 15000 });
        let listRespStatus = headResp.status;
        let listable = false;

        if (headResp.status === 200) {
          const getResp = await axios.get(url, { validateStatus: () => true, timeout: 15000 });
          listRespStatus = getResp.status;
          const body = typeof getResp.data === 'string' ? getResp.data : JSON.stringify(getResp.data);
          listable = getResp.status === 200 && isXmlListing(body);
        }

        return formatToolResult(true, {
          url,
          headStatus: headResp.status,
          listStatus: listRespStatus,
          listable,
        });
      } catch (error: any) {
        return formatToolResult(false, null, error.message);
      }
    }
  );

  server.tool(
    'cloud.storage_misconfig_check',
    {
      description: 'Check storage targets for read/list misconfigurations',
      inputSchema: {
        type: 'object',
        properties: {
          targets: {
            type: 'array',
            items: {
              type: 'object',
              properties: {
                provider: { type: 'string', enum: ['s3', 'azure', 'gcp'] },
                bucket: { type: 'string' },
                account: { type: 'string' },
                container: { type: 'string' },
              },
            },
          },
        },
        required: ['targets'],
      },
    },
    async ({ targets }: any): Promise<ToolResult> => {
      try {
        const results: any[] = [];
        for (const target of targets) {
          const provider = target.provider;
          const bucket = target.bucket;
          const account = target.account;
          const container = target.container;
          let url = '';
          if (provider === 's3' && bucket) url = `https://${bucket}.s3.amazonaws.com/`;
          if (provider === 'gcp' && bucket) url = `https://storage.googleapis.com/${bucket}/`;
          if (provider === 'azure' && account && container) {
            url = `https://${account}.blob.core.windows.net/${container}?restype=container&comp=list`;
          }
          if (!url) {
            results.push({ target, error: 'Missing fields' });
            continue;
          }
          const headResp = await axios.head(url, { validateStatus: () => true, timeout: 15000 });
          const getResp = await axios.get(url, { validateStatus: () => true, timeout: 15000 });
          const body = typeof getResp.data === 'string' ? getResp.data : JSON.stringify(getResp.data);
          results.push({
            target,
            headStatus: headResp.status,
            listStatus: getResp.status,
            listable: getResp.status === 200 && isXmlListing(body),
          });
        }

        return formatToolResult(true, { results });
      } catch (error: any) {
        return formatToolResult(false, null, error.message);
      }
    }
  );

  // Terraform or .env leaks
  server.tool(
    'cloud.terraform_leak_scan',
    {
      description: 'Probe for exposed terraform state or .env files',
      inputSchema: {
        type: 'object',
        properties: {
          baseUrl: { type: 'string' },
        },
        required: ['baseUrl'],
      },
    },
    async ({ baseUrl }: any): Promise<ToolResult> => {
      try {
        const paths = [
          '/terraform.tfstate',
          '/terraform.tfstate.backup',
          '/.terraform/terraform.tfstate',
          '/tfstate',
          '/state/terraform.tfstate',
          '/.env',
          '/.env.production',
        ];

        const results: any[] = [];
        for (const p of paths) {
          const url = baseUrl.replace(/\/$/, '') + p;
          const response = await axios.get(url, { validateStatus: () => true, timeout: 15000 });
          const body = typeof response.data === 'string' ? response.data : JSON.stringify(response.data);
          const exposed = response.status === 200 && body.length > 0;

          if (exposed) {
            await saveFinding({
              target: url,
              type: 'Exposed Config File',
              severity: 'high',
              description: `Exposed config/terraform state file at ${p}`,
              response: body.substring(0, 1000),
              timestamp: new Date(),
              score: 8,
            });
          }

          results.push({ path: p, status: response.status, exposed });
        }

        await saveTestResult(baseUrl, 'cloud_terraform_leak_scan', true, { results });

        return formatToolResult(true, { results });
      } catch (error: any) {
        return formatToolResult(false, null, error.message);
      }
    }
  );
}
