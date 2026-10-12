import { prisma } from "@/lib/prisma";
import { resolveUsageCounters } from "@/lib/quota-constants";
import { parseActiveEnginesFromSetting } from "@/lib/active-engines";

export type SettingsInitialSnapshot = {
  proxyUrl: string | null;
  keys: Array<{
    id: string;
    label: string;
    provider: string;
    proxyUrl: string | null;
    usageCount: number;
    usageCountWeekly: number;
    usageCountMonthly: number;
    isDisabled: boolean;
    lastUsedAt: string | null;
  }>;
  cats: Array<{
    id: number;
    slug: string;
    displayName: string;
    iconKey: string | null;
    suffixRules: Array<{ id: number; suffix: string }>;
  }>;
  activeEngines: string[];
};

export async function loadSettingsInitialSnapshot(): Promise<SettingsInitialSnapshot> {
  const [proxyRow, apiKeys, extensionCategories, activeEnginesRow] = await Promise.all([
    prisma.appSetting.findUnique({ where: { key: "global_proxy_url" } }),
    prisma.apiKey.findMany({ orderBy: { createdAt: "asc" } }),
    prisma.extensionCategory.findMany({
      orderBy: [{ displayName: "asc" }, { slug: "asc" }],
      include: { suffixRules: true },
    }),
    prisma.appSetting.findUnique({ where: { key: "active_engines" } }),
  ]);

  const proxyUrl =
    ((proxyRow?.value as { url?: string | null } | undefined) ?? { url: null }).url ??
    null;

  const keys = apiKeys.map((k) => {
    const usage = resolveUsageCounters(k);
    return {
      id: k.id,
      provider: k.provider as unknown as string,
      label: k.label,
      proxyUrl: k.proxyUrl,
      usageCount: usage.daily,
      usageCountWeekly: usage.weekly,
      usageCountMonthly: usage.monthly,
      isDisabled: k.isDisabled,
      lastUsedAt: k.lastUsedAt ? k.lastUsedAt.toISOString() : null,
    };
  });

  const cats = extensionCategories.map((c) => ({
    id: c.id,
    slug: c.slug,
    displayName: c.displayName,
    iconKey: c.iconKey,
    suffixRules: c.suffixRules.map((s) => ({ id: s.id, suffix: s.suffix })),
  }));

  const activeEngines = parseActiveEnginesFromSetting(activeEnginesRow?.value).map(String);

  return {
    proxyUrl,
    keys,
    cats,
    activeEngines,
  };
}

