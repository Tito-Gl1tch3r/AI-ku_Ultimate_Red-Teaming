import type { Prisma } from "@prisma/client";
import { isStructuredSearchQuery, parseUrlSearchGroups } from "@/lib/url-search-query";

const MIN_PLAIN_LEN = 3;
const MIN_TERM_LEN = 2;

function termMatchesFinding(term: string): Prisma.AnalysisFindingWhereInput {
  return {
    OR: [
      { snippet: { contains: term, mode: "insensitive" } },
      { discoveredUrl: { urlText: { contains: term, mode: "insensitive" } } },
    ],
  };
}

/** Whether `q` should be applied to the findings filter. */
export function isFindingsSearchQueryActive(searchStr: string): boolean {
  return findingsSearchWhere(searchStr) !== undefined;
}

export function findingsSearchWhere(
  searchStr: string,
): Prisma.AnalysisFindingWhereInput | undefined {
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
    return termMatchesFinding(term);
  }

  for (const g of groups) {
    for (const t of g) {
      if (t.length < MIN_TERM_LEN) return undefined;
    }
  }

  if (groups.length === 1 && groups[0].length === 1) {
    return termMatchesFinding(groups[0][0]);
  }

  return {
    OR: groups.map((andTerms) => ({
      AND: andTerms.map((term) => termMatchesFinding(term)),
    })),
  };
}
