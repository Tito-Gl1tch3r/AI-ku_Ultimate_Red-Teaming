import { NextResponse } from 'next/server';
import { checkDatabaseHealth, HealthCheckResult } from '@/lib/db-health';

export const dynamic = 'force-dynamic';

// Cache for health check result to avoid repeated DB calls
let cachedHealth: HealthCheckResult | null = null;
let cacheTime = 0;
const CACHE_TTL = 5000; // 5 seconds

export async function GET(request: Request) {
    try {
        // Check if this is a force refresh request
        const url = new URL(request.url);
        const forceRefresh = url.searchParams.get('refresh') === 'true';
        
        const now = Date.now();
        
        // Use cache if available and not expired
        if (!forceRefresh && cachedHealth && (now - cacheTime) < CACHE_TTL) {
            return NextResponse.json(cachedHealth);
        }
        
        const health = await checkDatabaseHealth();
        
        // Update cache
        cachedHealth = health;
        cacheTime = now;
        
        return NextResponse.json(health);
    } catch (error) {
        console.error('[Setup Health] Error:', error);
        return NextResponse.json({
            status: 'no_connection',
            message: 'Failed to check database health',
            details: {
                connectionError: error instanceof Error ? error.message : 'Unknown error',
            },
        });
    }
}
