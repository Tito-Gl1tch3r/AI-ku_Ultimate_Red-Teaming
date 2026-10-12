import type { Prisma } from "@prisma/client";

export type SearchBuilderRow = {
  id: string;
  term: string;
  operator: "AND" | "OR";
};

/** Tokenize respecting double-quoted phrases (AND/OR only apply outside quotes). */
export function tokenizeSearchString(searchStr: string): string[] {
  const tokens: string[] = [];
  let inQuote = false;
  let currentToken = "";

  for (let i = 0; i < searchStr.length; i++) {
    const char = searchStr[i];
    if (char === '"') {
      inQuote = !inQuote;
      currentToken += char;
    } else if (char === " " && !inQuote) {
      if (currentToken) {
        tokens.push(currentToken);
        currentToken = "";
      }
    } else {
      currentToken += char;
    }
  }
  if (currentToken) tokens.push(currentToken);
  return tokens;
}

export function isStructuredSearchQuery(searchStr: string): boolean {
  const trimmed = searchStr.trim();
  if (!trimmed) return false;
  if (trimmed.includes('"')) return true;
  const tokens = tokenizeSearchString(trimmed);
  return tokens.some((t) => {
    const u = t.toUpperCase();
    return u === "AND" || u === "OR";
  });
}

function cleanToken(token: string): string {
  let cleanTerm = token;
  if (cleanTerm.startsWith('"') && cleanTerm.endsWith('"') && cleanTerm.length >= 2) {
    cleanTerm = cleanTerm.slice(1, -1);
  }
  return cleanTerm;
}

/** Parse query into OR-groups of AND terms (same semantics as searchbuildersample). */
export function parseUrlSearchGroups(searchStr: string): string[][] {
  const trimmed = searchStr.trim();
  if (!trimmed) return [];

  if (!isStructuredSearchQuery(trimmed)) {
    return [[trimmed]];
  }

  const tokens = tokenizeSearchString(trimmed);
  const orGroups: string[][] = [];
  let currentAndGroup: string[] = [];

  for (const token of tokens) {
    const upper = token.toUpperCase();
    if (upper === "OR") {
      if (currentAndGroup.length > 0) {
        orGroups.push(currentAndGroup);
        currentAndGroup = [];
      }
    } else if (upper === "AND") {
      // implicit AND between terms
    } else {
      const cleanTerm = cleanToken(token);
      if (cleanTerm) currentAndGroup.push(cleanTerm);
    }
  }
  if (currentAndGroup.length > 0) orGroups.push(currentAndGroup);
  return orGroups;
}

const MIN_PLAIN_LEN = 3;
const MIN_TERM_LEN = 2;

/** Whether `q` should be applied to the database filter. */
export function isUrlSearchQueryActive(searchStr: string): boolean {
  return urlTextSearchWhere(searchStr) !== undefined;
}

export function urlTextSearchWhere(searchStr: string): Prisma.DiscoveredUrlWhereInput | undefined {
  const trimmed = searchStr.trim();
  if (!trimmed) return undefined;

  const groups = parseUrlSearchGroups(trimmed)
    .map((g) => g.filter((t) => t.length > 0))
    .filter((g) => g.length > 0);
  if (groups.length === 0) return undefined;

  const structured = isStructuredSearchQuery(trimmed);

  if (!structured) {
    const term = groups[0][0];
    if (!term || term.length < MIN_PLAIN_LEN) return undefined;
    return { urlText: { contains: term, mode: "insensitive" } };
  }

  for (const g of groups) {
    for (const t of g) {
      if (t.length < MIN_TERM_LEN) return undefined;
    }
  }

  if (groups.length === 1 && groups[0].length === 1) {
    return { urlText: { contains: groups[0][0], mode: "insensitive" } };
  }

  return {
    OR: groups.map((andTerms) => ({
      AND: andTerms.map((term) => ({ urlText: { contains: term, mode: "insensitive" } })),
    })),
  };
}

export function buildAdvancedSearchString(rows: Pick<SearchBuilderRow, "term" | "operator">[]): string {
  let q = "";
  for (const row of rows) {
    if (!row.term.trim()) continue;
    const cleanTerm = row.term.trim().replace(/"/g, "");
    const formattedTerm = `"${cleanTerm}"`;
    if (q === "") q += formattedTerm;
    else q += ` ${row.operator} ${formattedTerm}`;
  }
  return q;
}

export function parseQueryToBuilderRows(q: string): SearchBuilderRow[] {
  const trimmed = q.trim();
  if (!trimmed) return [{ id: "1", term: "", operator: "AND" }];

  if (!isStructuredSearchQuery(trimmed)) {
    return [{ id: "1", term: trimmed, operator: "AND" }];
  }

  const groups = parseUrlSearchGroups(trimmed);
  const rows: SearchBuilderRow[] = [];
  let id = 1;

  for (let gi = 0; gi < groups.length; gi++) {
    for (let ti = 0; ti < groups[gi].length; ti++) {
      const operator: "AND" | "OR" = rows.length === 0 ? "AND" : ti === 0 ? "OR" : "AND";
      rows.push({ id: String(id++), term: groups[gi][ti], operator });
    }
  }

  return rows.length > 0 ? rows : [{ id: "1", term: "", operator: "AND" }];
}

/** Human-readable summary for active structured queries. */
export function describeUrlSearchQuery(searchStr: string): string | null {
  const trimmed = searchStr.trim();
  if (!trimmed || !isUrlSearchQueryActive(trimmed)) return null;

  const groups = parseUrlSearchGroups(trimmed);
  return groups
    .map((g) => g.map((t) => `"${t}"`).join(" AND "))
    .join(" OR ");
}
