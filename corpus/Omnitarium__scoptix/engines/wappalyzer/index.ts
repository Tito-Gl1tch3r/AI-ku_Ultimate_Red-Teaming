import axios from "axios";
import { SocksProxyAgent } from "socks-proxy-agent";
import { assertUrlSafeForServerFetch } from "@/lib/ssrf-guard";

// wappalyzer-core has no bundled types; the runtime API is documented inline below.
// eslint-disable-next-line @typescript-eslint/no-var-requires
import Wappalyzer from "wappalyzer-core";
import technologies from "./fingerprints/technologies.json";
import categories from "./fingerprints/categories.json";

const TIMEOUT_MS = 30_000;
const MAX_BYTES = 4 * 1024 * 1024;
const UA =
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36";

// Load the fingerprint database once at module init.
let initialized = false;
function ensureInitialized() {
  if (initialized) return;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  (Wappalyzer as any).setTechnologies(technologies as any);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  (Wappalyzer as any).setCategories(categories as any);
  initialized = true;
}

export type DetectedTechnology = {
  name: string;
  version: string | null;
  categories: string[];
  confidence: number;
  iconName: string | null;
  website: string | null;
  cpe: string | null;
};

/** Extract <script src> URLs from raw HTML (lightweight, no DOM). */
function extractScriptSrc(html: string): string[] {
  const out: string[] = [];
  const re = /<script\b[^>]*\bsrc\s*=\s*["']([^"']+)["'][^>]*>/gi;
  let m: RegExpExecArray | null;
  while ((m = re.exec(html)) && out.length < 200) out.push(m[1]);
  return out;
}

/** Extract <meta name=... content=...> pairs from raw HTML. */
function extractMeta(html: string): Record<string, string[]> {
  const meta: Record<string, string[]> = {};
  const re = /<meta\b[^>]*>/gi;
  let tag: RegExpExecArray | null;
  while ((tag = re.exec(html)) && Object.keys(meta).length < 200) {
    const t = tag[0];
    const name = /\bname\s*=\s*["']([^"']+)["']/i.exec(t)?.[1];
    const content = /\bcontent\s*=\s*["']([^"']*)["']/i.exec(t)?.[1];
    if (name && content != null) {
      const key = name.toLowerCase();
      (meta[key] ??= []).push(content);
    }
  }
  return meta;
}

/**
 * Fingerprint a single URL using the Wappalyzer fingerprint database.
 * Fetches HTML + headers itself (with optional SOCKS proxy) and never throws —
 * returns [] on any failure, matching the graceful behavior of the other engines.
 */
export async function fingerprintUrl(params: {
  url: string;
  proxyUrl?: string | null;
}): Promise<DetectedTechnology[]> {
  ensureInitialized();

  // SSRF guard — same protection as deepFetchText. Do not remove.
  try {
    assertUrlSafeForServerFetch(params.url);
  } catch {
    return [];
  }

  const agent = params.proxyUrl ? new SocksProxyAgent(params.proxyUrl) : undefined;

  let html = "";
  const headers: Record<string, string[]> = {};
  const cookies: Record<string, string[]> = {};
  let finalUrl = params.url;

  try {
    const res = await axios.get<string>(params.url, {
      timeout: TIMEOUT_MS,
      httpsAgent: agent,
      httpAgent: agent,
      proxy: false,
      responseType: "text",
      transformResponse: [(d: string) => d],
      validateStatus: () => true,
      maxRedirects: 5,
      maxContentLength: MAX_BYTES,
      maxBodyLength: MAX_BYTES,
      headers: { "User-Agent": UA, Accept: "text/html,*/*" },
    });

    html = typeof res.data === "string" ? res.data : "";

    // Normalize headers to Record<string, string[]> (lowercased keys).
    for (const [k, v] of Object.entries(res.headers ?? {})) {
      if (v == null) continue;
      headers[k.toLowerCase()] = Array.isArray(v) ? v.map(String) : [String(v)];
    }

    // Parse Set-Cookie names for cookie-based fingerprints.
    const setCookie = res.headers?.["set-cookie"];
    if (Array.isArray(setCookie)) {
      for (const c of setCookie) {
        const name = String(c).split("=")[0]?.trim();
        if (name) (cookies[name] ??= []).push("");
      }
    }

    finalUrl = (res.request?.res?.responseUrl as string | undefined) ?? params.url;
  } catch {
    return [];
  }

  try {
    const scriptSrc = extractScriptSrc(html);
    const meta = extractMeta(html);

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const W = Wappalyzer as any;
    const detections = W.analyze({
      url: finalUrl,
      headers,
      cookies,
      html,
      scriptSrc,
      meta,
    });
    const resolved = W.resolve(detections) as Array<Record<string, unknown>>;

    const seen = new Set<string>();
    const out: DetectedTechnology[] = [];
    for (const t of resolved) {
      const name = typeof t.name === "string" ? t.name : "";
      if (!name || seen.has(name)) continue;
      seen.add(name);
      const cats = Array.isArray(t.categories)
        ? (t.categories as Array<{ name?: unknown }>)
            .map((c) => (typeof c?.name === "string" ? c.name : null))
            .filter((c): c is string => Boolean(c))
        : [];
      out.push({
        name,
        version: t.version ? String(t.version) : null,
        categories: cats,
        confidence: typeof t.confidence === "number" ? t.confidence : 0,
        iconName: t.icon ? String(t.icon) : null,
        website: t.website ? String(t.website) : null,
        cpe: t.cpe ? String(t.cpe) : null,
      });
    }
    return out;
  } catch {
    return [];
  }
}
