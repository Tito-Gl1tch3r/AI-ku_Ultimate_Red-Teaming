import { NextResponse } from "next/server";
import { EngineProvider, ScanJobStatus } from "@prisma/client";
import { z } from "zod";
import { prisma } from "@/lib/prisma";
import { getScanQueue } from "@/lib/queue";
import { parseActiveEnginesFromSetting } from "@/lib/active-engines";

const bodySchema = z.object({
  targetDomainId: z.string().uuid(),
  deepScan: z.boolean().optional(),
  deepScanCategorySlugs: z.array(z.string()).optional(),
  expandSubdomains: z.boolean().optional(),
  maxSubdomains: z.number().int().min(1).max(50_000).optional(),
  enginesEnabled: z.array(z.nativeEnum(EngineProvider)).optional(),
});

export async function GET() {
  const jobs = await prisma.scanJob.findMany({
    orderBy: { createdAt: "desc" },
    take: 100,
    include: { targetDomain: true },
  });
  return NextResponse.json({ scans: jobs });
}

export async function POST(req: Request) {
  const json = await req.json().catch(() => null);
  const parsed = bodySchema.safeParse(json);
  if (!parsed.success) {
    return NextResponse.json({ error: "Invalid body" }, { status: 400 });
  }

  const target = await prisma.targetDomain.findUnique({ where: { id: parsed.data.targetDomainId } });
  if (!target) return NextResponse.json({ error: "Target not found" }, { status: 404 });

  let engines = parsed.data.enginesEnabled;
  if (!engines || engines.length === 0) {
    const engineSetting = await prisma.appSetting.findUnique({
      where: { key: "active_engines" },
    });
    engines = parseActiveEnginesFromSetting(engineSetting?.value);
  }

  const job = await prisma.scanJob.create({
    data: {
      targetDomainId: target.id,
      status: ScanJobStatus.QUEUED,
      config: {
        deepScan: Boolean(parsed.data.deepScan),
        deepScanCategorySlugs: parsed.data.deepScanCategorySlugs ?? [],
        expandSubdomains: Boolean(parsed.data.expandSubdomains),
        maxSubdomains: parsed.data.maxSubdomains,
        enginesEnabled: engines,
      },
    },
  });

  const queue = getScanQueue();
  const bullJob = await queue.add("scan", { scanJobId: job.id }, { jobId: job.id });

  const updated = await prisma.scanJob.update({
    where: { id: job.id },
    data: { bullmqJobId: String(bullJob.id) },
  });

  return NextResponse.json({ scan: updated });
}
