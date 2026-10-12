import { NextRequest, NextResponse } from 'next/server';
import { readFile } from 'fs/promises';
import { join } from 'path';
import { existsSync } from 'fs';
import { getObjectStorageConfig, createS3Client } from '@/lib/object-storage';
import { GetObjectCommand } from '@aws-sdk/client-s3';
import { getSession } from '@/lib/auth';

interface RouteParams {
    params: Promise<{ filename: string }>;
}

export async function GET(request: NextRequest, { params }: RouteParams) {
    try {
        // Auth check required
        const session = await getSession();
        if (!session) {
            return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
        }

        const { filename } = await params;
        
        // Validate filename to prevent directory traversal
        if (filename.includes('..') || filename.includes('\\')) {
            return NextResponse.json({ error: 'Invalid filename' }, { status: 400 });
        }

        // Check URL params for storage type hint
        const searchParams = request.nextUrl.searchParams;
        const storageType = searchParams.get('storage');

        // Determine content type based on extension
        const ext = filename.split('.').pop()?.toLowerCase();
        let contentType = 'image/png';
        if (ext === 'jpg' || ext === 'jpeg') {
            contentType = 'image/jpeg';
        } else if (ext === 'webp') {
            contentType = 'image/webp';
        }

        // If storage type is s3, fetch from object storage
        if (storageType === 's3') {
            const config = await getObjectStorageConfig();
            const client = createS3Client(config);
            
            if (!client || !config.bucket) {
                return NextResponse.json({ error: 'Object storage not configured' }, { status: 500 });
            }

            try {
                // The filename might be the full key (screenshots/xxx.png)
                const key = filename.includes('/') ? filename : `screenshots/${filename}`;
                
                const response = await client.send(new GetObjectCommand({
                    Bucket: config.bucket,
                    Key: key,
                }));

                if (!response.Body) {
                    return NextResponse.json({ error: 'Screenshot not found in storage' }, { status: 404 });
                }

                // Convert stream to buffer
                const chunks: Uint8Array[] = [];
                const reader = response.Body.transformToWebStream().getReader();
                
                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;
                    chunks.push(value);
                }
                
                const buffer = Buffer.concat(chunks);

                return new NextResponse(buffer, {
                    headers: {
                        'Content-Type': response.ContentType || contentType,
                        'Cache-Control': 'public, max-age=31536000, immutable',
                    },
                });
            } catch (s3Error) {
                console.error('[Screenshots] S3 error:', s3Error);
                return NextResponse.json({ error: 'Failed to fetch from storage' }, { status: 404 });
            }
        }

        // Default: fetch from local storage
        const filePath = join(process.cwd(), 'data', 'screenshots', filename);
        
        if (!existsSync(filePath)) {
            return NextResponse.json({ error: 'Screenshot not found' }, { status: 404 });
        }

        const fileBuffer = await readFile(filePath);

        return new NextResponse(fileBuffer, {
            headers: {
                'Content-Type': contentType,
                'Cache-Control': 'public, max-age=31536000, immutable',
            },
        });
    } catch (error) {
        console.error('[Screenshots] Error serving file:', error);
        return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
    }
}
