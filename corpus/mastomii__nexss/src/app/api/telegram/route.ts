import { NextRequest, NextResponse } from 'next/server';
import { getSession } from '@/lib/auth';
import { query } from '@/lib/db';
import { 
    getChatIdFromUpdates, 
    sendTelegramMessage, 
    testBotToken,
    isValidBotToken 
} from '@/lib/telegram';

interface Setting {
    key: string;
    value: string;
}

// GET - Get telegram settings
export async function GET() {
    try {
        const session = await getSession();
        if (!session) {
            return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
        }

        const settings = await query<Setting>(
            `SELECT key, value FROM settings WHERE key LIKE 'telegram_%'`
        );

        const result: Record<string, string> = {};
        for (const setting of settings) {
            // Mask the bot token for security
            if (setting.key === 'telegram_bot_token' && setting.value) {
                result[setting.key] = setting.value.substring(0, 10) + '...' + setting.value.slice(-5);
            } else {
                result[setting.key] = setting.value;
            }
        }

        return NextResponse.json({ settings: result });
    } catch (error) {
        console.error('[Telegram] GET error:', error);
        return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
    }
}

// POST - Test token, get chat ID, send test message
export async function POST(request: NextRequest) {
    try {
        const session = await getSession();
        if (!session) {
            return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
        }

        if (session.rank < 3) {
            return NextResponse.json({ error: 'Admin access required' }, { status: 403 });
        }

        const body = await request.json();
        const { action, botToken } = body;

        if (!botToken) {
            return NextResponse.json({ error: 'Bot token is required' }, { status: 400 });
        }

        // Validate token format
        if (!isValidBotToken(botToken)) {
            return NextResponse.json({ 
                success: false, 
                error: 'Invalid bot token format. Token should be like: 123456789:ABCdefGHIjklMNOpqrsTUVwxyz' 
            });
        }

        switch (action) {
            case 'test_token': {
                const result = await testBotToken(botToken);
                return NextResponse.json(result);
            }

            case 'get_chat_id': {
                const result = await getChatIdFromUpdates(botToken);
                return NextResponse.json(result);
            }

            case 'send_test': {
                const { chatId } = body;
                if (!chatId) {
                    return NextResponse.json({ error: 'Chat ID is required' }, { status: 400 });
                }

                const message = `✅ <b>NeXSS Test Notification</b>

This is a test message from your NeXSS dashboard.

If you received this, notifications are working correctly! 🎉`;

                const result = await sendTelegramMessage(botToken, chatId, message);
                return NextResponse.json(result);
            }

            default:
                return NextResponse.json({ error: 'Invalid action' }, { status: 400 });
        }
    } catch (error) {
        console.error('[Telegram] POST error:', error);
        return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
    }
}
