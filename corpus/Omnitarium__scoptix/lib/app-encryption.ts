import crypto from "node:crypto";
import type { PrismaClient } from "@prisma/client";

const SETTING_KEY = "app_encryption_key";

function normalizeBase64(s: string): string {
  const t = s.replace(/[\r\n\s]/g, "").replace(/-/g, "+").replace(/_/g, "/");
  const pad = t.length % 4 === 0 ? "" : "=".repeat(4 - (t.length % 4));
  return t + pad;
}

function tryParseKey(raw: string): Buffer | null {
  const s = raw.trim();
  if (!s) return null;

  if (/^[0-9a-fA-F]{64}$/.test(s)) {
    return Buffer.from(s, "hex");
  }

  const buf = Buffer.from(normalizeBase64(s), "base64");
  return buf.length === 32 ? buf : null;
}

function toB64(buf: Buffer): string {
  return buf.toString("base64");
}

export async function resolveAppEncryptionKey(prisma: PrismaClient): Promise<Buffer> {
  // Prefer env, if valid.
  const env = process.env.APP_ENCRYPTION_KEY;
  if (env) {
    const parsed = tryParseKey(env);
    if (parsed) return parsed;
  }

  // Fall back to DB-stored key (auto-provisioned).
  const row = await prisma.appSetting.findUnique({ where: { key: SETTING_KEY } });
  const fromDb = (row?.value as { b64?: string } | null | undefined)?.b64;
  if (fromDb) {
    const parsed = tryParseKey(fromDb);
    if (parsed) return parsed;
  }

  // First-time bootstrap: generate and persist.
  const fresh = crypto.randomBytes(32);
  await prisma.appSetting.upsert({
    where: { key: SETTING_KEY },
    create: { key: SETTING_KEY, value: { b64: toB64(fresh) } },
    update: { value: { b64: toB64(fresh) } },
  });
  return fresh;
}

