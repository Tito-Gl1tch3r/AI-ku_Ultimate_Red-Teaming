import { NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";

export async function GET(
  request: Request,
  { params }: { params: Promise<{ id: string; hostnameNormalized: string }> },
) {
  try {
    const { id, hostnameNormalized } = await params;
    const targetDomainId = id;
    const scanJobId = new URL(request.url).searchParams.get("scanJobId")?.trim() || null;

    // First find if the subdomain exists in the target
    const subdomain = await prisma.subdomain.findFirst({
      where: { targetDomainId, hostnameNormalized },
      select: { id: true },
    });

    if (!subdomain) {
      return NextResponse.json({ error: "Not found" }, { status: 404 });
    }

    // Get the sightings for this hostname across the target, or filtered by scanJobId
    const sightingsQueryWhere = {
      hostnameNormalized,
      ipResolution: { targetDomainId },
      ...(scanJobId ? { scanJobId } : {}),
    };

    const sightingsRecords = await prisma.ipResolutionSighting.findMany({
      where: sightingsQueryWhere,
      include: {
        ipResolution: {
          select: { ipAddress: true },
        },
      },
      orderBy: { lastResolvedAt: "desc" },
    });

    // Group the sightings by IP address, keeping the most recent observation for each IP
    const sightingsMap = new Map<string, { ipAddress: string; lastResolvedAt: Date }>();
    let firstResolvedAt: Date | null = null;
    let lastResolvedAtOverall: Date | null = null;

    for (const record of sightingsRecords) {
      const ip = record.ipResolution.ipAddress;
      const resolvedAt = record.lastResolvedAt;

      if (!firstResolvedAt || resolvedAt < firstResolvedAt) {
        firstResolvedAt = resolvedAt;
      }
      if (!lastResolvedAtOverall || resolvedAt > lastResolvedAtOverall) {
        lastResolvedAtOverall = resolvedAt;
      }

      if (!sightingsMap.has(ip)) {
        sightingsMap.set(ip, {
          ipAddress: ip,
          lastResolvedAt: resolvedAt,
        });
      } else {
        // Since records are ordered by desc, the first one encountered should be the latest, but just in case
        const existing = sightingsMap.get(ip)!;
        if (resolvedAt > existing.lastResolvedAt) {
          sightingsMap.set(ip, { ipAddress: ip, lastResolvedAt: resolvedAt });
        }
      }
    }

    const uniqueSightings = Array.from(sightingsMap.values()).sort(
      (a, b) => b.lastResolvedAt.getTime() - a.lastResolvedAt.getTime()
    );

    const observedIpCount = scanJobId ? uniqueSightings.length : uniqueSightings.length; // Actually, in global context, it's just unique IPs

    return NextResponse.json({
      scope: scanJobId ? "scan" : "target",
      scanJobId,
      targetDomainId,
      hostnameNormalized,
      summary: {
        firstResolvedAt: firstResolvedAt?.toISOString() ?? null,
        lastResolvedAt: lastResolvedAtOverall?.toISOString() ?? new Date().toISOString(), // Fallback if no sightings
        observedIpCount,
      },
      sightings: uniqueSightings.map((s) => ({
        ipAddress: s.ipAddress,
        lastResolvedAt: s.lastResolvedAt.toISOString(),
      })),
    });
  } catch (error) {
    console.error("Error fetching Hostname sightings:", error);
    return NextResponse.json({ error: "Internal Server Error" }, { status: 500 });
  }
}
