const FINDING_FIELD_KEYS = new Set([
  'description',
  'observation',
  'remediation',
  'references',
  'poc',
  'affected',
  'cvssv3',
  'cvssv4',
  'retestDescription',
  'category',
  'vulnType',
  'title'
]);

export const isGeneralInformationLocation = (location = '') => {
  const value = String(location || '').trim().toLowerCase();
  if (value === 'general')
    return true;
  if (value.startsWith('general/'))
    return true;

  if (value.startsWith('field:')) {
    const field = value.slice('field:'.length);
    return !FINDING_FIELD_KEYS.has(field);
  }

  const fieldPathMatch = value.match(/^field path:\s*(.+)$/);
  if (!fieldPathMatch)
    return false;

  return !/^finding\./.test(fieldPathMatch[1].trim());
};

// Classifies a location into what it points at. Only the finding's/section's identity
// matters for navigation now — any trailing field suffix (built-in or custom) is stripped
// and discarded, since "go to" only ever lands on the finding/section as a whole.
export const parseIssueLocation = (location = '') => {
  const value = String(location || '').trim() || 'report';

  if (value === 'general' || value === 'network' || value === 'report')
    return { type: 'page', page: value };

  if (isGeneralInformationLocation(value))
    return { type: 'page', page: 'general' };

  const sectionMatch = value.match(/^section:(.+)$/);
  if (sectionMatch)
    return { type: 'section', sectionName: sectionMatch[1] };

  if (value.startsWith('finding:')) {
    let rest = value.slice('finding:'.length);
    let findingId = null;

    const idMatch = rest.match(/^([0-9a-fA-F]{24})::(.*)$/);
    if (idMatch) {
      findingId = idMatch[1];
      rest = idMatch[2];
    }

    // Drop any trailing "/fieldName" or "/Custom Field Label" suffix — we only need the title.
    const slashIndex = rest.indexOf('/');
    const findingTitle = slashIndex === -1 ? rest : rest.slice(0, slashIndex);

    return { type: 'finding', findingId, findingTitle };
  }

  return { type: 'unknown', raw: value };
};

// Resolves a parsed finding location to the actual finding object. Shared by buildIssueRoute
// and the QA panel's grouping, so both agree on which finding an issue belongs to.
export const resolveFindingForLocation = (parsed, findings = []) => {
  if (parsed.type !== 'finding')
    return null;

  const title = String(parsed.findingTitle || '').trim();
  let finding = null;

  if (parsed.findingId)
    finding = findings.find((entry) => String(entry?._id || entry?.id || '') === parsed.findingId);

  // Title is a display fallback for locations that predate id-tagging, or an id that no
  // longer resolves (finding deleted since the QA run).
  if (!finding)
    finding = findings.find((entry) => String(entry?.title || '').trim() === title);

  return finding || null;
};

export const buildIssueRoute = (auditId, parsed, { findings = [], sections = [] } = {}) => {
  if (!auditId)
    return null;

  if (parsed.type === 'page') {
    if (parsed.page === 'network')
      return { path: `/audits/${auditId}/network` };
    return { path: `/audits/${auditId}/general` };
  }

  if (parsed.type === 'section') {
    const section = sections.find((entry) => {
      const name = String(entry?.name || '').trim();
      const field = String(entry?.field || '').trim();
      return name === parsed.sectionName || field === parsed.sectionName;
    });

    if (section?._id)
      return { path: `/audits/${auditId}/sections/${section._id}` };

    return { path: `/audits/${auditId}/general` };
  }

  if (parsed.type === 'finding') {
    const finding = resolveFindingForLocation(parsed, findings);
    if (finding?._id)
      return { path: `/audits/${auditId}/findings/${finding._id}` };
  }

  return { path: `/audits/${auditId}/general` };
};

