import type { ApiKey, PrismaClient } from "@prisma/client";
import { EngineProvider } from "@prisma/client";
import type Redis from "ioredis";
import { decryptSecretWithKey } from "@/lib/encryption";
import { resolveAppEncryptionKey } from "@/lib/app-encryption";
import {
  PER_KEY_PER_DAY,
  PER_KEY_PER_MINUTE,
  currentUsagePeriodKeys,
  effectiveIntervalSec,
  utcDateOnly,
} from "@/lib/quota-constants";

const LAST_GLOBAL_MS = "recon:vt:last_global_ms";
const MINUTE_ZSET = (id: string) => `recon:vt:key:${id}:minute`;
const BACKOFF_UNTIL = (id: string) => `recon:vt:key:${id}:backoff_until_ms`;

export type ResolvedVtKey = {
  id: string;
  plainSecret: string;
  proxyUrl: string | null;
};

function sleep(ms: number) {
  return new Promise((r) => setTimeout(r, ms));
}

/** Reset daily counters for keys whose date has rolled over. */
async function resetDailyCountersIfNeeded(prisma: PrismaClient) {
  const today = utcDateOnly(new Date());
  await prisma.apiKey.updateMany({
    where: {
      provider: EngineProvider.VIRUSTOTAL,
      usageCountDate: { lt: today },
    },
    data: {
      usageCount: 0,
      isDisabled: false,
      usageCountDate: today,
    },
  });
}

/**
 * Enforce the global pacing interval between consecutive VT requests.
 *
 * Interval = ceil(60 / (N × 4)) seconds where N = number of active keys.
 *   1 key  → 15 sec
 *   2 keys → 8 sec
 *   3 keys → 5 sec
 *   4 keys → 4 sec
 *
 * No budget-saving logic — pacing is purely rate-limit driven.
 */
async function waitGlobalPacing(redis: Redis, activeKeyCount: number) {
  const eff = effectiveIntervalSec(activeKeyCount);
  if (!Number.isFinite(eff)) {
    await sleep(1_000);
    return;
  }
  const last = await redis.get(LAST_GLOBAL_MS);
  const lastMs = last ? parseInt(last, 10) : 0;
  const wait = lastMs + eff * 1000 - Date.now();
  if (wait > 0) await sleep(wait);
}

/**
 * Try to reserve a slot in this key's per-minute sliding window.
 * Returns the member string if successful, null if the key is already at 4 req/min.
 */
async function tryReserveMinuteSlot(redis: Redis, keyId: string): Promise<string | null> {
  const now = Date.now();
  const z = MINUTE_ZSET(keyId);
  await redis.zremrangebyscore(z, 0, now - 60_000);
  const c = await redis.zcard(z);
  if (c >= PER_KEY_PER_MINUTE) return null;
  const member = `${now}-${Math.random()}`;
  await redis.zadd(z, now, member);
  await redis.pexpire(z, 120_000);
  return member;
}

async function rollbackMinuteSlot(redis: Redis, keyId: string, member: string) {
  await redis.zrem(MINUTE_ZSET(keyId), member);
}

async function markGlobalRequest(redis: Redis) {
  await redis.set(LAST_GLOBAL_MS, String(Date.now()));
}

/**
 * Acquire an available VT API key, respecting:
 * - Global pacing interval (ceil(60 / N×4) sec between requests)
 * - Per-key sliding window (max 4 req/min per key)
 * - Per-key daily cap (500 req/day — disables key when reached, re-enables next UTC day)
 * - Per-key backoff (when 429/403 received)
 */
export async function acquireVtKey(prisma: PrismaClient, redis: Redis, onWait?: () => Promise<void>): Promise<ResolvedVtKey> {
  const appKey = await resolveAppEncryptionKey(prisma);

  for (;;) {
    // Reset daily counters for any keys whose date has rolled over
    await resetDailyCountersIfNeeded(prisma);

    const keys = await prisma.apiKey.findMany({
      where: { provider: EngineProvider.VIRUSTOTAL, isDisabled: false },
      orderBy: { lastUsedAt: "asc" }, // oldest-used first → natural round-robin
    });

    if (keys.length === 0) {
      // No active keys — wait briefly and retry
      await onWait?.();
      await sleep(1_000);
      continue;
    }

    // Enforce global pacing (prevents bursting beyond rate limit)
    await waitGlobalPacing(redis, keys.length);

    const now = Date.now();
    let picked: { k: ApiKey; member: string } | null = null;

    for (const k of keys) {
      // Skip keys that are in backoff period
      const bo = await redis.get(BACKOFF_UNTIL(k.id));
      if (bo && parseInt(bo, 10) > now) continue;

      // Skip and disable keys that have hit their daily cap
      if (k.usageCount >= PER_KEY_PER_DAY) {
        await prisma.apiKey.update({ where: { id: k.id }, data: { isDisabled: true } });
        continue;
      }

      // Try to reserve a slot in this key's per-minute window
      const member = await tryReserveMinuteSlot(redis, k.id);
      if (!member) continue;

      picked = { k, member };
      break;
    }

    if (!picked) {
      // All keys are at capacity (rate-limited or in backoff) — spin briefly
      await onWait?.();
      await sleep(250);
      continue;
    }

    const { k, member } = picked;

    const periods = currentUsagePeriodKeys();
    let usage = k.usageCount;
    let date = k.usageCountDate;
    if (utcDateOnly(date).getTime() !== periods.date.getTime()) {
      usage = 0;
      date = periods.date;
    }
    usage += 1;

    let usageWeekly = k.usageCountWeekly;
    let weekKey = k.usageWeekKey;
    if (weekKey !== periods.weekKey) {
      usageWeekly = 0;
      weekKey = periods.weekKey;
    }
    usageWeekly += 1;

    let usageMonthly = k.usageCountMonthly;
    let monthKey = k.usageMonthKey;
    if (monthKey !== periods.monthKey) {
      usageMonthly = 0;
      monthKey = periods.monthKey;
    }
    usageMonthly += 1;

    const disable = usage >= PER_KEY_PER_DAY;

    try {
      await prisma.apiKey.update({
        where: { id: k.id },
        data: {
          usageCount: usage,
          usageCountDate: date,
          usageCountWeekly: usageWeekly,
          usageWeekKey: weekKey,
          usageCountMonthly: usageMonthly,
          usageMonthKey: monthKey,
          isDisabled: disable,
          lastUsedAt: new Date(),
        },
      });
    } catch (e) {
      // Rollback the minute slot reservation on DB failure
      await rollbackMinuteSlot(redis, k.id, member);
      throw e;
    }

    await markGlobalRequest(redis);

    return {
      id: k.id,
      plainSecret: decryptSecretWithKey(appKey, k.secretEncrypted),
      proxyUrl: k.proxyUrl,
    };
  }
}

export async function recordBackoff(redis: Redis, keyId: string, ms: number) {
  const until = Date.now() + ms;
  await redis.set(BACKOFF_UNTIL(keyId), String(until), "PX", Math.min(ms, 300_000));
}
