import { NextRequest, NextResponse } from 'next/server';
import { logout, getSession, logAction } from '@/lib/auth';
import { getClientIP } from '@/lib/utils';
import { cookies } from 'next/headers';

export async function POST(request: NextRequest) {
    try {
        const cookieStore = await cookies();
        const token = cookieStore.get('nexss_session')?.value;
        const session = await getSession();
        const ip = getClientIP(request);

        if (token) {
            await logout(token);
        }

        if (session) {
            await logAction(session.userId, 'logout', 'User logged out', ip);
        }

        const response = NextResponse.json({ success: true });

        // Clear session cookie
        response.cookies.set('nexss_session', '', {
            httpOnly: true,
            secure: process.env.NODE_ENV === 'production',
            sameSite: 'lax',
            maxAge: 0,
            path: '/',
        });

        return response;
    } catch (error) {
        console.error('[Auth] Logout error:', error);
        return NextResponse.json(
            { error: 'Internal server error' },
            { status: 500 }
        );
    }
}
