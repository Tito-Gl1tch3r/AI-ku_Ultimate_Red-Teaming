import { NextRequest, NextResponse } from 'next/server';
import { getSession, logAction } from '@/lib/auth';
import { query, queryOne, User } from '@/lib/db';
import { getClientIP } from '@/lib/utils';
import { verifyToken, decryptSecret } from '@/lib/totp';
import bcrypt from 'bcrypt';

interface User2FA extends User {
    totp_secret: string | null;
    totp_enabled: boolean;
    backup_codes: string | null;
}

// POST - Disable 2FA
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

        // Verify TOTP token (optional but recommended)
        if (token && user.totp_secret) {
            const secret = decryptSecret(user.totp_secret);
            const isValid = verifyToken(token, secret);
            if (!isValid) {
                return NextResponse.json(
                    { error: 'Invalid 2FA code' },
                    { status: 401 }
                );
            }
        }

        // Disable 2FA
        await query(
            `UPDATE users SET 
                totp_enabled = false, 
                totp_secret = NULL,
                backup_codes = NULL,
                totp_verified_at = NULL,
                updated_at = NOW() 
            WHERE id = $1`,
            [session.userId]
        );

        const ip = getClientIP(request);
        await logAction(session.userId, '2fa_disabled', '2FA has been disabled', ip);

        return NextResponse.json({
            success: true,
            message: '2FA has been disabled',
        });
    } catch (error) {
        console.error('[2FA Disable] Error:', error);
        return NextResponse.json(
            { error: 'Internal server error' },
            { status: 500 }
        );
    }
}
