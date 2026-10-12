import { NextRequest, NextResponse } from 'next/server';
import { getSession, logAction } from '@/lib/auth';
import { query, queryOne, User } from '@/lib/db';
import { getClientIP } from '@/lib/utils';
import { generateBackupCodes, hashBackupCodes, verifyToken, decryptSecret } from '@/lib/totp';
import bcrypt from 'bcrypt';

interface User2FA extends User {
    totp_secret: string | null;
    totp_enabled: boolean;
    backup_codes: string | null;
}

// GET - Get backup codes count
export async function GET() {
    try {
        const session = await getSession();
        if (!session) {
            return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
        }

        const user = await queryOne<User2FA>(
            'SELECT backup_codes FROM users WHERE id = $1',
            [session.userId]
        );

        if (!user) {
            return NextResponse.json({ error: 'User not found' }, { status: 404 });
        }

        let remainingCodes = 0;
        if (user.backup_codes) {
            const codes = JSON.parse(user.backup_codes);
            remainingCodes = codes.length;
        }

        return NextResponse.json({ remainingCodes });
    } catch (error) {
        console.error('[2FA Backup] Error:', error);
        return NextResponse.json(
            { error: 'Internal server error' },
            { status: 500 }
        );
    }
}

// POST - Regenerate backup codes
export async function POST(request: NextRequest) {
    try {
        const session = await getSession();
        if (!session) {
            return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
        }

        const body = await request.json();
        const { password, token } = body;

        if (!password) {
            return NextResponse.json(
                { error: 'Password is required' },
                { status: 400 }
            );
        }

        // Get user with 2FA data
        const user = await queryOne<User2FA>(
            'SELECT * FROM users WHERE id = $1',
            [session.userId]
        );

        if (!user) {
            return NextResponse.json({ error: 'User not found' }, { status: 404 });
        }

        if (!user.totp_enabled) {
            return NextResponse.json(
                { error: '2FA is not enabled' },
                { status: 400 }
            );
        }

        // Verify password
        const validPassword = await bcrypt.compare(password, user.password);
        if (!validPassword) {
            return NextResponse.json(
                { error: 'Invalid password' },
                { status: 401 }
            );
        }

        // Verify TOTP token
        if (!token || !user.totp_secret) {
            return NextResponse.json(
                { error: '2FA code is required' },
                { status: 400 }
            );
        }

        const secret = decryptSecret(user.totp_secret);
        const isValid = verifyToken(token, secret);
        if (!isValid) {
            return NextResponse.json(
                { error: 'Invalid 2FA code' },
                { status: 401 }
            );
        }

        // Generate new backup codes
        const backupCodes = generateBackupCodes(10);
        const hashedCodes = await hashBackupCodes(backupCodes);

        // Update backup codes
        await query(
            'UPDATE users SET backup_codes = $1, updated_at = NOW() WHERE id = $2',
            [JSON.stringify(hashedCodes), session.userId]
        );

        const ip = getClientIP(request);
        await logAction(session.userId, '2fa_backup_regenerated', 'Backup codes regenerated', ip);

        return NextResponse.json({
            success: true,
            backupCodes, // Return plain backup codes (show once only!)
            message: 'New backup codes generated. Save them securely!',
        });
    } catch (error) {
        console.error('[2FA Backup Regenerate] Error:', error);
        return NextResponse.json(
            { error: 'Internal server error' },
            { status: 500 }
        );
    }
}
