import type { ComponentType } from "react";
import {
  IconCloud,
  IconDatabase,
  IconFileText,
  IconFolder,
  IconGlobe,
  IconHash,
  IconKey,
  IconLink,
  IconLock,
  IconMail,
  IconServer,
  IconTerminal,
} from "@/components/ui-icons";

export const CATEGORY_ICON_KEYS = [
  "folder",
  "file",
  "terminal",
  "hash",
  "globe",
  "database",
  "server",
  "link",
  "lock",
  "key",
  "cloud",
  "mail",
] as const;

export type CategoryIconKey = (typeof CATEGORY_ICON_KEYS)[number];

export const DEFAULT_CATEGORY_ICON_KEY: CategoryIconKey = "file";

export const CATEGORY_ICON_OPTIONS: { key: CategoryIconKey; label: string }[] = [
  { key: "folder", label: "Archives" },
  { key: "file", label: "Documents" },
  { key: "terminal", label: "Executables" },
  { key: "hash", label: "Scripts" },
  { key: "globe", label: "Web" },
  { key: "database", label: "Data" },
  { key: "server", label: "Server" },
  { key: "link", label: "URLs" },
  { key: "lock", label: "Protected" },
  { key: "key", label: "Secrets" },
  { key: "cloud", label: "Cloud" },
  { key: "mail", label: "Email" },
];

export function isCategoryIconKey(value: string | null | undefined): value is CategoryIconKey {
  return CATEGORY_ICON_KEYS.includes(value as CategoryIconKey);
}

export function resolveCategoryIconKey(
  iconKey: string | null | undefined,
  slug?: string,
): CategoryIconKey {
  if (isCategoryIconKey(iconKey)) return iconKey;
  if (slug) {
    const s = slug.toLowerCase();
    if (s.includes("archive")) return "folder";
    if (s.includes("exec")) return "terminal";
    if (s.includes("script") || s === "js") return "hash";
    if (s.includes("doc")) return "file";
  }
  return DEFAULT_CATEGORY_ICON_KEY;
}

type CategoryIconComponent = ComponentType<{ className?: string }>;

export function getCategoryIconComponent(iconKey: CategoryIconKey): CategoryIconComponent {
  switch (iconKey) {
    case "folder":
      return IconFolder;
    case "file":
      return IconFileText;
    case "terminal":
      return IconTerminal;
    case "hash":
      return IconHash;
    case "globe":
      return IconGlobe;
    case "database":
      return IconDatabase;
    case "server":
      return IconServer;
    case "link":
      return IconLink;
    case "lock":
      return IconLock;
    case "key":
      return IconKey;
    case "cloud":
      return IconCloud;
    case "mail":
      return IconMail;
    default:
      return IconFileText;
  }
}

export function getCategoryIconForCategory(
  iconKey: string | null | undefined,
  slug: string,
): CategoryIconComponent {
  return getCategoryIconComponent(resolveCategoryIconKey(iconKey, slug));
}
