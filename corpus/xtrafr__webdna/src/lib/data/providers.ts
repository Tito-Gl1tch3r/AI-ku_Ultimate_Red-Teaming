export interface ProviderInfo {
  name: string;
  matchPatterns: string[];
  description: string;
  website: string;
  logo?: string;
  category: 'Cloud' | 'CDN' | 'Hosting' | 'Infrastructure';
}

export const providers: ProviderInfo[] = [
  {
    name: 'Google Cloud',
    matchPatterns: ['Google LLC', 'Google', 'GCP'],
    description: 'A suite of cloud computing services that runs on the same infrastructure that Google uses internally for its end-user products, such as Google Search, Gmail, and YouTube.',
    website: 'https://cloud.google.com',
    category: 'Cloud'
  },
  {
    name: 'Amazon Web Services',
    matchPatterns: ['Amazon.com', 'AWS', 'Amazon Data Services'],
    description: 'The world\'s most comprehensive and broadly adopted cloud platform, offering over 200 fully featured services from data centers globally.',
    website: 'https://aws.amazon.com',
    category: 'Cloud'
  },
  {
    name: 'Cloudflare',
    matchPatterns: ['Cloudflare', 'Cloudflare, Inc.'],
    description: 'A global network designed to make everything you connect to the Internet secure, private, fast, and reliable. Known for its CDN and DDoS protection.',
    website: 'https://cloudflare.com',
    category: 'CDN'
  },
  {
    name: 'Microsoft Azure',
    matchPatterns: ['Microsoft Corporation', 'Microsoft', 'Azure'],
    description: 'A cloud computing platform and infrastructure created by Microsoft for building, testing, deploying, and managing applications through Microsoft-managed data centers.',
    website: 'https://azure.microsoft.com',
    category: 'Cloud'
  },
  {
    name: 'DigitalOcean',
    matchPatterns: ['DigitalOcean', 'DigitalOcean, LLC'],
    description: 'A cloud infrastructure provider focused on helping developers and businesses deploy and scale applications that run simultaneously on multiple computers.',
    website: 'https://digitalocean.com',
    category: 'Cloud'
  },
  {
    name: 'OVHcloud',
    matchPatterns: ['OVH', 'OVH SAS', 'OVH Hosting'],
    description: 'A global cloud provider that specializes in delivering industry-leading performance and cost-effective solutions to manage, secure, and scale data.',
    website: 'https://ovhcloud.com',
    category: 'Hosting'
  },
  {
    name: 'Hetzner',
    matchPatterns: ['Hetzner', 'Hetzner Online GmbH'],
    description: 'A professional web hosting provider and experienced data center operator. Known for its powerful dedicated servers and cloud instances in Europe.',
    website: 'https://hetzner.com',
    category: 'Hosting'
  },
  {
    name: 'Vercel',
    matchPatterns: ['Vercel', 'Vercel Inc.'],
    description: 'A platform for framework-defined infrastructure, built for high-performance frontend teams. Optimized for Next.js and frontend deployments.',
    website: 'https://vercel.com',
    category: 'Hosting'
  },
  {
    name: 'Netlify',
    matchPatterns: ['Netlify', 'Netlify, Inc.'],
    description: 'A platform for building, deploying, and scaling modern web projects. It provides a workflow that makes it easy to build high-performance websites.',
    website: 'https://netlify.com',
    category: 'Hosting'
  },
  {
    name: 'Akamai',
    matchPatterns: ['Akamai', 'Akamai Technologies'],
    description: 'A global content delivery network (CDN), cybersecurity, and cloud service provider. One of the world\'s largest distributed computing platforms.',
    website: 'https://akamai.com',
    category: 'CDN'
  },
  {
    name: 'Fastly',
    matchPatterns: ['Fastly', 'Fastly, Inc.'],
    description: 'An edge cloud platform that provides content delivery network, Internet security, load balancing, and video & streaming services.',
    website: 'https://fastly.com',
    category: 'CDN'
  }
];

export function findProvider(providerName: string): ProviderInfo | undefined {
  if (!providerName) return undefined;
  return providers.find(p => 
    p.matchPatterns.some(pattern => 
      providerName.toLowerCase().includes(pattern.toLowerCase())
    )
  );
}
