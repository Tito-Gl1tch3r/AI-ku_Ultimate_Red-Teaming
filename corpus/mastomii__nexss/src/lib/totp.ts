/**
 * TOTP (Time-based One-Time Password) utilities for 2FA
 */

import { authenticator } from 'otplib';
import QRCode from 'qrcode';
import crypto from 'crypto';

// Configure authenticator
authenticator.options = {
    digits: 6,
    step: 30, // 30 seconds
    window: 1, // Allow 1 step before/after for clock drift
};

/**
 * Generate a new TOTP secret
 */
export function generateSecret(): string {
    return authenticator.generateSecret();
}

/**
 * Generate a TOTP token from a secret (for testing)
 */
export function generateToken(secret: string): string {
    return authenticator.generate(secret);
}

/**
 * Verify a TOTP token
 */
export function verifyToken(token: string, secret: string): boolean {
    try {
        return authenticator.verify({ token, secret });
    } catch {
        return false;
    }
}

/**
 * Generate otpauth URI for authenticator apps
 */
export function generateOtpauthUri(
    secret: string,
    username: string,
    issuer: string = 'NeXSS'
): string {
    return authenticator.keyuri(username, issuer, secret);
}

/**
 * Generate QR code as data URL
 */
export async function generateQRCode(otpauthUri: string): Promise<string> {
    return QRCode.toDataURL(otpauthUri, {
        width: 256,
        margin: 2,
        color: {
            dark: '#000000',
            light: '#ffffff',
        },
    });
}

/**
 * Generate backup codes
 */
export function generateBackupCodes(count: number = 10): string[] {
    const codes: string[] = [];
    for (let i = 0; i < count; i++) {
        const code = crypto.randomBytes(4).toString('hex').toUpperCase();
        codes.push(`${code.slice(0, 4)}-${code.slice(4)}`);
    }
    return codes;
}

/**
 * Hash a backup code for storage
 */
export async function hashBackupCode(code: string): Promise<string> {
    const normalized = code.replace(/-/g, '').toUpperCase();
    const hash = crypto.createHash('sha256').update(normalized).digest('hex');
    return hash;
}

/**
 * Hash all backup codes for storage
 */
export async function hashBackupCodes(codes: string[]): Promise<string[]> {
    return Promise.all(codes.map(hashBackupCode));
}

/**
 * Verify a backup code against hashed codes
 */
export async function verifyBackupCode(
    inputCode: string,
    hashedCodes: string[]
): Promise<{ valid: boolean; index: number }> {
    const inputHash = await hashBackupCode(inputCode);
    const index = hashedCodes.findIndex(hash => hash === inputHash);
    return { valid: index !== -1, index };
}

/**
 * Get encryption key from JWT_SECRET (derive a 32-byte key using SHA-256)
 */
function getEncryptionKey(): Buffer {
    const jwtSecret = process.env.JWT_SECRET || 'fallback-secret-change-me';
    // Derive a 32-byte key from JWT_SECRET using SHA-256
    return crypto.createHash('sha256').update(jwtSecret).digest();
}

/**
 * Encrypt TOTP secret using AES-256-GCM
 * Format: iv:authTag:encryptedData (all base64)
 */
export function encryptSecret(secret: string): string {
    const key = getEncryptionKey();
    const iv = crypto.randomBytes(12); // 96-bit IV for GCM

    const cipher = crypto.createCipheriv('aes-256-gcm', key, iv);
    let encrypted = cipher.update(secret, 'utf8', 'base64');
    encrypted += cipher.final('base64');

    const authTag = cipher.getAuthTag();

    // Combine IV, auth tag, and encrypted data
    return `${iv.toString('base64')}:${authTag.toString('base64')}:${encrypted}`;
}

/**
 * Decrypt TOTP secret using AES-256-GCM
 */
export function decryptSecret(encryptedData: string): string {
    // Check if data is already encrypted (contains colons for our format)
    if (!encryptedData.includes(':')) {
        // Legacy plain text - return as-is for backward compatibility
        return encryptedData;
    }

    const key = getEncryptionKey();
    const parts = encryptedData.split(':');

    if (parts.length !== 3) {
        throw new Error('Invalid encrypted data format');
    }

    const iv = Buffer.from(parts[0], 'base64');
    const authTag = Buffer.from(parts[1], 'base64');
    const encrypted = parts[2];

    const decipher = crypto.createDecipheriv('aes-256-gcm', key, iv);
    decipher.setAuthTag(authTag);

    let decrypted = decipher.update(encrypted, 'base64', 'utf8');
    decrypted += decipher.final('utf8');

    return decrypted;
}
