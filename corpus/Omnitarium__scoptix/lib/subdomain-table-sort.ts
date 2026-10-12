export type SubdomainSortField = "hostname" | "ipCount" | "latestIp" | "lastResolved";
export type SubdomainSortDir = "asc" | "desc";
export type SubdomainTableSort = { field: SubdomainSortField; dir: SubdomainSortDir };

export const SUBDOMAIN_SORTABLE_FIELDS: readonly SubdomainSortField[] = [
  "hostname",
  "ipCount",
  "latestIp",
  "lastResolved",
];

const DEFAULT_SORT: SubdomainTableSort = { field: "hostname", dir: "asc" };

const FIRST_CLICK_DIR: Record<SubdomainSortField, SubdomainSortDir> = {
  hostname: "asc",
  ipCount: "desc",
  latestIp: "asc",
  lastResolved: "desc",
};

function isSubdomainSortField(value: string | undefined): value is SubdomainSortField {
  return SUBDOMAIN_SORTABLE_FIELDS.includes(value as SubdomainSortField);
}

export function parseSubdomainTableSort(
  sortRaw: string | undefined,
  dirRaw: string | undefined,
): SubdomainTableSort {
  const field: SubdomainSortField = isSubdomainSortField(sortRaw) ? sortRaw : DEFAULT_SORT.field;
  if (dirRaw === "asc" || dirRaw === "desc") {
    return { field, dir: dirRaw };
  }
  if (isSubdomainSortField(sortRaw)) {
    return { field: sortRaw, dir: FIRST_CLICK_DIR[sortRaw] };
  }
  return DEFAULT_SORT;
}

export function nextSubdomainSort(clicked: SubdomainSortField, current: SubdomainTableSort): SubdomainTableSort {
  if (current.field === clicked) {
    return { field: clicked, dir: current.dir === "asc" ? "desc" : "asc" };
  }
  return { field: clicked, dir: FIRST_CLICK_DIR[clicked] };
}

export function subdomainSortSearchParams(sort: SubdomainTableSort): Record<string, string> {
  return { subSort: sort.field, subDir: sort.dir };
}

export function buildSubdomainSortHref(
  basePath: string,
  fixedParams: Record<string, string>,
  next: SubdomainTableSort,
): string {
  const p = new URLSearchParams({ ...fixedParams, ...subdomainSortSearchParams(next) });
  return `${basePath}?${p.toString()}`;
}

export const SUBDOMAIN_SORT_FIELD_LABELS: Record<SubdomainSortField, string> = {
  hostname: "Hostname",
  ipCount: "Historical IPs",
  latestIp: "Latest IP",
  lastResolved: "Last Resolved",
};

export function sortSubdomainRows<T extends {
  hostnameNormalized: string;
  ipCount: number;
  latestIp: string | null;
  lastResolvedAt: Date | null;
}>(rows: T[], sort: SubdomainTableSort): T[] {
  return [...rows].sort((a, b) => {
    let cmp = 0;
    switch (sort.field) {
      case "hostname":
        cmp = a.hostnameNormalized.localeCompare(b.hostnameNormalized);
        break;
      case "ipCount":
        cmp = a.ipCount - b.ipCount;
        break;
      case "latestIp":
        cmp = (a.latestIp || "").localeCompare(b.latestIp || "");
        break;
      case "lastResolved": {
        const timeA = a.lastResolvedAt ? a.lastResolvedAt.getTime() : 0;
        const timeB = b.lastResolvedAt ? b.lastResolvedAt.getTime() : 0;
        cmp = timeA - timeB;
        break;
      }
    }
    return sort.dir === "asc" ? cmp : -cmp;
  });
}
