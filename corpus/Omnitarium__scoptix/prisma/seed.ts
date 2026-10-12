import "dotenv/config";

import { EngineProvider } from "@prisma/client";
import type { CategoryIconKey } from "../lib/category-icons";
import { BUILTIN_EXTENSION_CATEGORIES } from "../lib/extension-category-labels";

const BUILTIN_CATEGORY_ICON_KEYS: Record<string, CategoryIconKey> = {
  js: "hash",
  document: "file",
  executable: "terminal",
  other: "folder",
};
import { encryptSecretWithKey } from "../lib/encryption";
import { resolveAppEncryptionKey } from "../lib/app-encryption";
import { prisma } from "../lib/prisma";
import { utcDateOnly, currentIsoWeekKey, currentMonthKey } from "../lib/quota-constants";

async function main() {
  const today = utcDateOnly(new Date());
  const weekKey = currentIsoWeekKey();
  const monthKey = currentMonthKey();

  const cats = [...BUILTIN_EXTENSION_CATEGORIES];

  for (const c of cats) {
    const iconKey = BUILTIN_CATEGORY_ICON_KEYS[c.slug] ?? "file";
    await prisma.extensionCategory.upsert({
      where: { slug: c.slug },
      create: { ...c, iconKey },
      update: { displayName: c.displayName, iconKey },
    });
  }

  const js = await prisma.extensionCategory.findUniqueOrThrow({ where: { slug: "js" } });
  const doc = await prisma.extensionCategory.findUniqueOrThrow({ where: { slug: "document" } });
  const exe = await prisma.extensionCategory.findUniqueOrThrow({ where: { slug: "executable" } });
  const other = await prisma.extensionCategory.findUniqueOrThrow({ where: { slug: "other" } });

  const suffixPairs: { suffix: string; id: number }[] = [
    { suffix: ".js", id: js.id },
    { suffix: ".mjs", id: js.id },
    { suffix: ".cjs", id: js.id },
    { suffix: ".pdf", id: doc.id },
    { suffix: ".csv", id: doc.id },
    { suffix: ".doc", id: doc.id },
    { suffix: ".docx", id: doc.id },
    { suffix: ".exe", id: exe.id },
    { suffix: ".dll", id: exe.id },
    { suffix: ".html", id: other.id },
    { suffix: ".htm", id: other.id },
  ];

  for (const s of suffixPairs) {
    await prisma.extensionSuffixRule.upsert({
      where: { suffix: s.suffix },
      create: { suffix: s.suffix, extensionCategoryId: s.id },
      update: { extensionCategoryId: s.id },
    });
  }

  await prisma.appSetting.upsert({
    where: { key: "global_proxy_url" },
    create: { key: "global_proxy_url", value: { url: null } },
    update: {},
  });

  await prisma.appSetting.upsert({
    where: { key: "engines_enabled_default" },
    create: { key: "engines_enabled_default", value: { engines: [EngineProvider.VIRUSTOTAL] } },
    update: {},
  });

  const demoKey = process.env.VT_SEED_API_KEY;
  if (demoKey) {
    const key = await resolveAppEncryptionKey(prisma);
    await prisma.apiKey.create({
      data: {
        provider: EngineProvider.VIRUSTOTAL,
        label: "Seed VT key (dev)",
        secretEncrypted: encryptSecretWithKey(key, demoKey),
        usageCountDate: today,
        usageCount: 0,
        usageWeekKey: weekKey,
        usageCountWeekly: 0,
        usageMonthKey: monthKey,
        usageCountMonthly: 0,
        isDisabled: false,
      },
    });
  }

  console.info("Seed complete.");
}

main()
  .catch((e) => {
    console.error(e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
