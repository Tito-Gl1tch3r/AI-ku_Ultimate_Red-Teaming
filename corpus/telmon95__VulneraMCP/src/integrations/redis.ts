import { createClient, RedisClientType } from 'redis';

let redisClient: RedisClientType | null = null;
let redisAvailable = false;
let redisInitialized = false;

export function initRedis(): boolean {
  if (redisInitialized) return redisAvailable;
  redisInitialized = true;

  // Check if Redis is explicitly disabled
  if (process.env.REDIS_DISABLED === 'true') {
    return false;
  }

  try {
    redisClient = createClient({
      socket: {
        host: process.env.REDIS_HOST || 'localhost',
        port: parseInt(process.env.REDIS_PORT || '6379'),
        reconnectStrategy: false, // Don't auto-reconnect
        connectTimeout: 2000, // Quick timeout
      },
      password: process.env.REDIS_PASSWORD || undefined,
    });

    // Completely suppress error events - don't log anything
    redisClient.on('error', () => {
      redisAvailable = false;
    });

    redisClient.on('connect', () => {
      redisAvailable = true;
    });

    redisClient.on('ready', () => {
      redisAvailable = true;
    });

    // Try to connect asynchronously, don't wait or log errors
    redisClient.connect().catch(() => {
      redisAvailable = false;
    });

    return false; // Return false initially, will be set to true on connect
  } catch (error) {
    redisAvailable = false;
    return false;
  }
}

async function getRedisClient(): Promise<RedisClientType | null> {
  if (!redisClient) {
    initRedis();
  }
  
  if (!redisAvailable || !redisClient) {
    return null;
  }

  try {
    if (!redisClient.isOpen) {
      await redisClient.connect();
    }
    return redisClient;
  } catch {
    redisAvailable = false;
    return null;
  }
}

export async function setWorkingMemory(key: string, value: any, ttl?: number): Promise<void> {
  try {
    const client = await getRedisClient();
    if (!client) return; // Redis not available, fail silently
    
    const serialized = JSON.stringify(value);
    if (ttl) {
      await client.setEx(key, ttl, serialized);
    } else {
      await client.set(key, serialized);
    }
  } catch {
    // Fail silently if Redis is not available
  }
}

export async function getWorkingMemory<T>(key: string): Promise<T | null> {
  try {
    const client = await getRedisClient();
    if (!client) return null; // Redis not available
    
    const value = await client.get(key);
    if (!value) return null;
    try {
      return JSON.parse(value) as T;
    } catch {
      return null;
    }
  } catch {
    return null;
  }
}

export async function deleteWorkingMemory(key: string): Promise<void> {
  try {
    const client = await getRedisClient();
    if (!client) return;
    await client.del(key);
  } catch {
    // Fail silently
  }
}

export async function addToSet(key: string, value: string): Promise<void> {
  try {
    const client = await getRedisClient();
    if (!client) return;
    await client.sAdd(key, value);
  } catch {
    // Fail silently
  }
}

export async function getSet(key: string): Promise<string[]> {
  try {
    const client = await getRedisClient();
    if (!client) return [];
    return await client.sMembers(key);
  } catch {
    return [];
  }
}

export async function incrementCounter(key: string): Promise<number> {
  try {
    const client = await getRedisClient();
    if (!client) return 0;
    return await client.incr(key);
  } catch {
    return 0;
  }
}

export function isRedisAvailable(): boolean {
  return redisAvailable;
}

