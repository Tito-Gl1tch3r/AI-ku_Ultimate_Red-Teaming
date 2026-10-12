import { NextResponse } from "next/server";
import {
  buildScanExportFilename,
  buildScanExportPayload,
  ExportUnavailableError,
  loadScanExportContext,
  parseScanExportType,
} from "@/lib/scan-export";

export const dynamic = "force-dynamic";

export async function GET(req: Request, ctx: { params: Promise<{ id: string }> }) {
  const { id } = await ctx.params;
  const type = parseScanExportType(new URL(req.url).searchParams.get("type"));

  if (!type) {
    return NextResponse.json(
      { error: "Invalid export type. Use findings, subdomains, urls, or all." },
      { status: 400 },
    );
  }

  const context = await loadScanExportContext(id);
  if (!context) {
    return NextResponse.json({ error: "Not found" }, { status: 404 });
  }

  try {
    const payload = await buildScanExportPayload(id, type, context.availability);
    const filename = buildScanExportFilename(
      context.scan.targetDomain.domainNormalized,
      id,
      type,
    );

    const body =
      typeof payload.body === "string"
        ? payload.body
        : new Uint8Array(payload.body);

    return new NextResponse(body, {
      headers: {
        "Content-Type": payload.contentType,
        "Content-Disposition": `attachment; filename="${filename}"`,
        "Cache-Control": "no-store",
      },
    });
  } catch (error) {
    if (error instanceof ExportUnavailableError) {
      return NextResponse.json({ error: error.message }, { status: 409 });
    }
    throw error;
  }
}
