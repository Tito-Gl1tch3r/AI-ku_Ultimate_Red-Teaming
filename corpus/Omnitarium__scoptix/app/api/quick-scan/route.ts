import { NextResponse } from "next/server";
import { ScanJobStatus } from "@prisma/client";
import { z } from "zod";
import { prisma } from "@/lib/prisma";
import { getScanQueue } from "@/lib/queue";
import { upsertTargetDomain } from "@/lib/targets";
import { detectInputType } from "@/lib/domain-detect";
import { parseActiveEnginesFromSetting } from "@/lib/active-engines";
import { normalizeDomainInput } from "@/lib/extract-hosts";

const bodySchema = z.object({
  domain: z.string().min(3).max(255),
  deepScan: z.boolean().optional(),
  deepScanCategorySlugs: z.array(z.string()).optional(),
  skipList: z.array(z.string()).optional(),
});

/**
 * POST /api/quick-scan
 *
 * One-click scan: accepts a domain string, auto-creates target,
 * auto-detects active engines, auto-detects domain vs subdomain,
 * creates scan job, and enqueues it.
 */
export async function POST(req: Request) {
  const json = await req.json().catch(() => null);
  const parsed = bodySchema.safeParse(json);
  if (!parsed.success) {
    return NextResponse.json({ error: "Invalid body" }, { status: 400 });
  }

  const rawDomain = parsed.data.domain.trim();
  const normalized = normalizeDomainInput(rawDomain);
  if (!normalized || normalized.length < 3) {
    return NextResponse.json({ error: "Invalid domain" }, { status: 400 });
  }

  // Auto-detect: domain or subdomain
  const inputType = detectInputType(normalized);

  // Upsert target (use the exact input domain as the target workspace, preventing it from being stripped to root)
  const target = await upsertTargetDomain(prisma, normalized);

  // If input is a subdomain, also upsert it into the subdomain table
  if (inputType === "subdomain") {
    const hn = normalized.toLowerCase();
    const existing = await prisma.subdomain.findUnique({
      where: {
        targetDomainId_hostnameNormalized: {
          targetDomainId: target.id,
          hostnameNormalized: hn,
        },
      },
    });
    if (!existing) {
      await prisma.subdomain.create({
        data: {
          targetDomainId: target.id,
          hostname: hn,
          hostnameNormalized: hn,
          sourceFlags: { userInput: true },
        },
      });
    }
  }

  // Fetch active engines from settings
  const engineSetting = await prisma.appSetting.findUnique({
    where: { key: "active_engines" },
  });
  const activeEngines = parseActiveEnginesFromSetting(engineSetting?.value);

  if (activeEngines.length === 0) {
    return NextResponse.json(
      { error: "No active engines configured in Settings." },
      { status: 400 },
    );
  }

  // Create scan job
  const expandSubdomains = inputType === "domain";
  const job = await prisma.scanJob.create({
    data: {
      targetDomainId: target.id,
      status: ScanJobStatus.QUEUED,
      config: {
        deepScan: Boolean(parsed.data.deepScan),
        deepScanCategorySlugs: parsed.data.deepScanCategorySlugs ?? [],
        expandSubdomains,
        enginesEnabled: activeEngines,
        inputHostname: normalized, // store the original input for the pipeline
        inputType,
        skipList: parsed.data.skipList ?? [],
      },
    },
  });

  const queue = getScanQueue();
  const bullJob = await queue.add("scan", { scanJobId: job.id }, { jobId: job.id });

  const updated = await prisma.scanJob.update({
    where: { id: job.id },
    data: { bullmqJobId: String(bullJob.id) },
  });

  return NextResponse.json({
    scan: updated,
    targetId: target.id,
    inputType,
    enginesDetected: activeEngines,
  });
}
