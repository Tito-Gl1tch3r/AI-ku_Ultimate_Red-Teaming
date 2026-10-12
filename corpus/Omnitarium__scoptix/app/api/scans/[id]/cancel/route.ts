import { NextResponse } from "next/server";
import { ScanJobStatus } from "@prisma/client";
import { prisma } from "@/lib/prisma";
import { getScanQueue } from "@/lib/queue";

/**
 * POST /api/scans/[id]/cancel
 *
 * Cancels a QUEUED or RUNNING scan job.
 * - Updates DB status to CANCELLED.
 * - Attempts to remove the job from BullMQ (works for QUEUED jobs).
 * - For RUNNING jobs, the worker pipeline checks for CANCELLED status
 *   at regular checkpoints and will stop gracefully.
 */
export async function POST(_req: Request, ctx: { params: Promise<{ id: string }> }) {
  const { id } = await ctx.params;

  const job = await prisma.scanJob.findUnique({ where: { id } });
  if (!job) {
    return NextResponse.json({ error: "Scan not found" }, { status: 404 });
  }

  if (job.status !== ScanJobStatus.QUEUED && job.status !== ScanJobStatus.RUNNING) {
    return NextResponse.json({ error: "Scan is not active" }, { status: 400 });
  }

  // 1. Mark as CANCELLED in DB
  const updated = await prisma.scanJob.update({
    where: { id },
    data: {
      status: ScanJobStatus.CANCELLED,
      completedAt: new Date(),
    },
  });

  // 2. Try to remove from BullMQ queue (works if still queued)
  if (job.bullmqJobId) {
    try {
      const queue = getScanQueue();
      const bullJob = await queue.getJob(job.bullmqJobId);
      if (bullJob) {
        await bullJob.remove().catch(() => {});
      }
    } catch {
      // Job may already be processing — the pipeline checkpoint will handle it
    }
  }

  return NextResponse.json({ scan: updated });
}
