import { parse as parseTld } from "tldts";

/**
 * Extract hostname from VT `undetected_urls` tuple string using WHATWG URL + PSL (tldts).
 * Regex is optional supplement for non-URL fragments (not primary).
 */
export function extractHostIfUnderTarget(
  rawUrlString: string,
  targetDomainNormalized: string,
): string | null {
  const trimmed = rawUrlString.trim();
  if (!trimmed) return null;

  try {
    const u =
      trimmed.startsWith("http://") || trimmed.startsWith("https://")
        ? new URL(trimmed)
        : new URL(`https://${trimmed}`);
    const hostname = u.hostname.toLowerCase().replace(/\.$/, "");
    if (!hostname) return null;

    const targetReg = parseTld(targetDomainNormalized).domain;
    const hostReg = parseTld(hostname).domain;
    if (!targetReg || !hostReg || hostReg !== targetReg) return null;
    return hostname;
  } catch {
    return extractHostRegexSupplement(trimmed, targetDomainNormalized);
  }
}

/** Optional fallback for edge / non-standard strings (documented limitation: may miss or FP). */
function extractHostRegexSupplement(raw: string, targetDomainNormalized: string): string | null {
  const targetReg = parseTld(targetDomainNormalized).domain;
  if (!targetReg) return null;
  const re = /(?:https?:\/\/)?([a-z0-9.-]+\.[a-z]{2,})(?:[\/:?#]|$)/i;
  const m = raw.match(re);
  if (!m?.[1]) return null;
  const hostname = m[1].toLowerCase().replace(/\.$/, "");
  const hostReg = parseTld(hostname).domain;
  if (!hostReg || hostReg !== targetReg) return null;
  return hostname;
}

export function normalizeDomainInput(input: string): string {
  return input.trim().toLowerCase().replace(/\.$/, "");
}
