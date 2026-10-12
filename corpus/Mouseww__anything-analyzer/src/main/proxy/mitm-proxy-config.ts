import { readFileSync, writeFileSync, existsSync } from "fs";
import { join } from "path";
import { app } from "electron";

export interface MitmProxyConfig {
  enabled: boolean;
  port: number;
  caInstalled: boolean;
  systemProxy: boolean;
}

const DEFAULT_CONFIG: MitmProxyConfig = {
  enabled: false,
  port: 8888,
  caInstalled: false,
  systemProxy: false,
};

function getConfigPath(): string {
  return join(app.getPath("userData"), "mitm-proxy-config.json");
}

export function loadMitmProxyConfig(): MitmProxyConfig {
  const configPath = getConfigPath();
  if (!existsSync(configPath)) return { ...DEFAULT_CONFIG };

  try {
    const raw = readFileSync(configPath, "utf-8");
    return { ...DEFAULT_CONFIG, ...JSON.parse(raw) };
  } catch {
    return { ...DEFAULT_CONFIG };
  }
}

export function saveMitmProxyConfig(config: MitmProxyConfig): void {
  writeFileSync(getConfigPath(), JSON.stringify(config, null, 2), "utf-8");
}
