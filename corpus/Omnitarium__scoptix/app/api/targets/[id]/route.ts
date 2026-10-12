import { NextResponse } from "next/server";
import { ScanJobStatus } from "@prisma/client";
import { prisma } from "@/lib/prisma";
import { getScanQueue } from "@/lib/queue";

export async function GET(_req: Request, ctx: { params: Promise<{ id: string }> }) {
  const { id } = await ctx.params;
  const target = await prisma.targetDomain.findUnique({
    where: { id },
    include: {
      subdomains: { orderBy: { hostnameNormalized: "asc" }, take: 5000 },
      scanJobs: { orderBy: { createdAt: "desc" }, take: 50 },
    },
  });
  if (!target) return NextResponse.json({ error: "Not found" }, { status: 404 });
  return NextResponse.json({ target });
}

/**
 * DELETE /api/targets/[id]
 *
 * Deletes a target and ALL its child data (subdomains, URLs, findings, scans).
 * If any scans are currently RUNNING or QUEUED, they are cancelled first.
 */
export async function DELETE(_req: Request, ctx: { params: Promise<{ id: string }> }) {
  const { id } = await ctx.params;

  const target = await prisma.targetDomain.findUnique({ where: { id } });
  if (!target) {
    return NextResponse.json({ error: "Target not found" }, { status: 404 });
  }

  // 1. Find all active scans for this target and cancel them
  const activeScans = await prisma.scanJob.findMany({
    where: {
      targetDomainId: id,
      status: { in: [ScanJobStatus.QUEUED, ScanJobStatus.RUNNING] },
    },
  });

  if (activeScans.length > 0) {
    // Mark all active scans as CANCELLED
    await prisma.scanJob.updateMany({
      where: {
        id: { in: activeScans.map((s) => s.id) },
      },
      data: {
        status: ScanJobStatus.CANCELLED,
        completedAt: new Date(),
      },
    });

    // Remove from BullMQ queue
    const queue = getScanQueue();
    for (const scan of activeScans) {
      if (scan.bullmqJobId) {
        try {
          const bullJob = await queue.getJob(scan.bullmqJobId);
          if (bullJob) await bullJob.remove().catch(() => {});
        } catch {
          // Already processed or removed — safe to ignore
        }
      }
    }
  }

  // 2. Delete the target — Prisma cascade will clean subdomains, URLs, findings, scan jobs
  await prisma.targetDomain.delete({ where: { id } });

  return NextResponse.json({ ok: true });
}

