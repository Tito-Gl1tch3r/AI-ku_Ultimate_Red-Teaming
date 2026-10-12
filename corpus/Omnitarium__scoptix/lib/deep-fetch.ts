import axios from "axios";
import { SocksProxyAgent } from "socks-proxy-agent";
import { assertUrlSafeForServerFetch } from "@/lib/ssrf-guard";

const MAX_BYTES = 2 * 1024 * 1024;
const TIMEOUT_MS = 15_000;

export async function deepFetchText(params: {
  url: string;
  proxyUrl?: string | null;
}): Promise<{ text: string; bytes: number }> {
  assertUrlSafeForServerFetch(params.url);
  const agent = params.proxyUrl ? new SocksProxyAgent(params.proxyUrl) : undefined;
  const res = await axios.get<ArrayBuffer>(params.url, {
    responseType: "arraybuffer",
    timeout: TIMEOUT_MS,
    maxContentLength: MAX_BYTES,
    maxBodyLength: MAX_BYTES,
    httpsAgent: agent,
    httpAgent: agent,
    proxy: false,
    maxRedirects: 5,
    beforeRedirect: (options) => {
      assertUrlSafeForServerFetch(options.href);
    },
    validateStatus: (s) => s >= 200 && s < 400,
    transformResponse: [(data) => data],
  });
  const buf = Buffer.from(res.data as ArrayBuffer);
  if (buf.length > MAX_BYTES) {
    throw new Error("Response exceeds size limit");
  }
  const text = buf.toString("utf8");
  return { text, bytes: buf.length };
}
