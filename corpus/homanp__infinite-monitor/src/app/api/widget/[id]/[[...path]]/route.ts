import { NextRequest } from "next/server";
import { ensureWidget, fetchFromWidget } from "@/lib/widget-runner";
import { getWidgetCode } from "@/db/widgets";

const LOADING_HTML = `<!DOCTYPE html>
<html class="dark">
<head><meta charset="UTF-8"><meta http-equiv="refresh" content="2"></head>
<body style="margin:0;background:#27272a;display:flex;align-items:center;justify-content:center;height:100vh;font-family:ui-monospace,monospace;color:#71717a;font-size:12px;">
<div style="text-align:center">
<div style="animation:spin 1s linear infinite;display:inline-block;width:16px;height:16px;border:2px solid #52525b;border-top-color:#a1a1aa;border-radius:50%;margin-bottom:8px"></div>
<div>Building widget…</div>
</div>
<style>@keyframes spin{to{transform:rotate(360deg)}}</style>
</body>
</html>`;

function escapeHtml(value: string): string {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function errorHtml(message?: string): string {
  const detail = message ? `<pre style="margin:0;white-space:pre-wrap;word-break:break-word;color:#f4f4f5;max-width:640px">${escapeHtml(message)}</pre>` : "<div>No error details were captured.</div>";
  return `<!DOCTYPE html>
<html class="dark">
<head><meta charset="UTF-8"><meta http-equiv="refresh" content="30"></head>
<body style="margin:0;background:#27272a;display:flex;align-items:center;justify-content:center;height:100vh;font-family:ui-monospace,monospace;color:#a1a1aa;font-size:12px;padding:16px;">
<div style="max-width:680px;width:100%;border:1px solid #3f3f46;background:#18181b;padding:16px">
<div style="color:#f59e0b;text-transform:uppercase;letter-spacing:0.08em;font-size:11px;margin-bottom:8px">Widget build failed</div>
${detail}
</div>
</body>
</html>`;
}

export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ id: string; path?: string[] }> }
) {
  const { id, path: pathSegments } = await params;

  const code = getWidgetCode(id);
  if (!code) {
    return new Response(LOADING_HTML, {
      status: 200,
      headers: { "Content-Type": "text/html; charset=utf-8" },
    });
  }

  const widget = await ensureWidget(id);

  if (widget.status === "error") {
    return new Response(errorHtml(widget.error), {
      status: 200,
      headers: { "Content-Type": "text/html; charset=utf-8" },
    });
  }

  if (widget.status !== "ready") {
    return new Response(LOADING_HTML, {
      status: 200,
      headers: { "Content-Type": "text/html; charset=utf-8" },
    });
  }

  const subPath = pathSegments?.join("/") ?? "";

  try {
    const result = await fetchFromWidget(id, subPath, {
      Accept: req.headers.get("accept") ?? "*/*",
    });

    if (!result) {
      return new Response(LOADING_HTML, {
        status: 200,
        headers: { "Content-Type": "text/html; charset=utf-8" },
      });
    }

    if (!subPath && result.contentType.includes("text/html")) {
      const baseTag = `<base href="/api/widget/${id}/">`;
      const patched = result.body.replace("<head>", `<head>${baseTag}`);
      return new Response(patched, {
        status: result.status,
        headers: {
          "Content-Type": "text/html; charset=utf-8",
          "Cache-Control": "no-store",
        },
      });
    }

    return new Response(result.body, {
      status: result.status,
      headers: {
        "Content-Type": result.contentType,
        "Cache-Control": "no-store",
      },
    });
  } catch {
    return new Response(LOADING_HTML, {
      status: 200,
      headers: { "Content-Type": "text/html; charset=utf-8" },
    });
  }
}
