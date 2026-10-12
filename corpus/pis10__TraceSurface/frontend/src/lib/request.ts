

export type RequestShape = {
  method?: string | null;
  url?: string | null;
  headers?: Record<string, unknown> | null;
  body?: unknown;
};

function bodyToString(body: unknown) {
  if (!body) return "";
  if (typeof body === "object") return JSON.stringify(body);
  return String(body);
}

export function requestToCurl({ method, url, headers, body }: RequestShape) {
  const verb = method || "GET";
  const target = url || "/";
  let cmd = `curl -i -X ${verb} '${target}'`;
  for (const [key, value] of Object.entries(headers || {})) {
    cmd += ` \\\n  -H '${key}: ${String(value)}'`;
  }
  const bodyText = bodyToString(body);
  if (bodyText) cmd += ` \\\n  --data-raw '${bodyText}'`;
  return cmd;
}

// 根据请求参数生成原始 HTTP 报文（用于复制粘贴）
export function requestToRawHttp({ method, url, headers, body }: RequestShape) {
  let host = "";
  let pathQuery = url || "/";
  try {
    const parsed = new URL(url || "");
    host = parsed.host;
    pathQuery = `${parsed.pathname || "/"}${parsed.search || ""}`;
  } catch {
    // Leave the original URL as the request target.
  }

  const bodyText = bodyToString(body);
  const bodyBytes = bodyText ? new TextEncoder().encode(bodyText).length : 0;
  const lines = [`${method || "GET"} ${pathQuery} HTTP/1.1`];
  if (host) lines.push(`Host: ${host}`);
  for (const [key, value] of Object.entries(headers || {})) {
    const lowered = key.toLowerCase();
    if (lowered === "host" || lowered === "content-length") continue;
    lines.push(`${key}: ${String(value)}`);
  }
  if (bodyText) lines.push(`Content-Length: ${bodyBytes}`);
  lines.push("", bodyText);
  return lines.join("\r\n");
}
