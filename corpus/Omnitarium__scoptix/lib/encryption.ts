import crypto from "node:crypto";

const ALGO = "aes-256-gcm";
const IV_LEN = 12;
const TAG_LEN = 16;

function normalizeBase64(s: string): string {
  // Accept base64url and missing padding.
  const t = s.replace(/[\r\n\s]/g, "").replace(/-/g, "+").replace(/_/g, "/");
  const pad = t.length % 4 === 0 ? "" : "=".repeat(4 - (t.length % 4));
  return t + pad;
}

function getKey(): Buffer {
  const raw = process.env.APP_ENCRYPTION_KEY?.trim();
  if (!raw) {
    throw new Error(
      [
        "APP_ENCRYPTION_KEY is not set.",
        "Provide a 32-byte key as base64/base64url (recommended) or 64-char hex.",
        "Generate (Linux/macOS): openssl rand -base64 32",
      ].join(" "),
    );
  }

  // Support 64-char hex (32 bytes).
  if (/^[0-9a-fA-F]{64}$/.test(raw)) {
    return Buffer.from(raw, "hex");
  }

  const buf = Buffer.from(normalizeBase64(raw), "base64");
  if (buf.length !== 32) {
    throw new Error(
      [
        "APP_ENCRYPTION_KEY must decode to exactly 32 bytes.",
        "Expected base64/base64url of 32 random bytes (or 64-char hex).",
        "Generate: openssl rand -base64 32",
      ].join(" "),
    );
  }
  return buf;
}

export function encryptSecretWithKey(key: Buffer, plain: string): string {
  const iv = crypto.randomBytes(IV_LEN);
  const cipher = crypto.createCipheriv(ALGO, key, iv);
  const enc = Buffer.concat([cipher.update(plain, "utf8"), cipher.final()]);
  const tag = cipher.getAuthTag();
  return Buffer.concat([iv, tag, enc]).toString("base64");
}

export function decryptSecretWithKey(key: Buffer, payload: string): string {
  const raw = Buffer.from(payload, "base64");
  const iv = raw.subarray(0, IV_LEN);
  const tag = raw.subarray(IV_LEN, IV_LEN + TAG_LEN);
  const data = raw.subarray(IV_LEN + TAG_LEN);
  const decipher = crypto.createDecipheriv(ALGO, key, iv);
  decipher.setAuthTag(tag);
  return Buffer.concat([decipher.update(data), decipher.final()]).toString("utf8");
}

export function encryptSecret(plain: string): string {
  return encryptSecretWithKey(getKey(), plain);
}

export function decryptSecret(payload: string): string {
  return decryptSecretWithKey(getKey(), payload);
}
