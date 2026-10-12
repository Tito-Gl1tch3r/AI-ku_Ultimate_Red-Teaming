const QA_CHECK_KEYS = ['completeness', 'references', 'imageCaptions', 'duplicates', 'aiDuplicates', 'aiUnlinkedTranslations', 'redaction', 'customer', 'instructions'];
const QA_SCOPES = ['programmatic', 'ai', 'all'];

const defaultQaChecks = () => ({
    completeness: true,
    references: true,
    imageCaptions: true,
    duplicates: true,
    aiDuplicates: true,
    aiUnlinkedTranslations: true,
    redaction: true,
    customer: true,
    instructions: true
});

const normalizeQaChecks = (raw = {}) => {
    const normalized = defaultQaChecks();

    QA_CHECK_KEYS.forEach((key) => {
        if (Object.prototype.hasOwnProperty.call(raw, key))
            normalized[key] = raw[key] !== false;
    });

    return normalized;
};

const getQaChecksFromSettings = (settings = {}) => {
    return normalizeQaChecks(settings?.ai?.public?.qaChecks || {});
};

const isQaCheckEnabled = (qaChecks = {}, key) => {
    if (!QA_CHECK_KEYS.includes(key))
        return false;
    return normalizeQaChecks(qaChecks)[key] !== false;
};

const hasEnabledAiQaChecks = (qaChecks = {}) => {
    return ['redaction', 'customer', 'instructions'].some((key) => isQaCheckEnabled(qaChecks, key));
};

const hasEnabledQaChecks = (qaChecks = {}) => {
    return QA_CHECK_KEYS.some((key) => isQaCheckEnabled(qaChecks, key));
};

const validateQaChecksPayload = (payload) => {
    if (payload === null || typeof payload !== 'object' || Array.isArray(payload))
        return { valid: false, message: 'Invalid qaChecks payload' };

    for (const key of Object.keys(payload)) {
        if (!QA_CHECK_KEYS.includes(key))
            return { valid: false, message: `Invalid qaChecks key: ${key}` };
        if (typeof payload[key] !== 'boolean')
            return { valid: false, message: `Invalid qaChecks.${key} payload` };
    }

    return { valid: true };
};

const buildQaChecksSettingsUpdate = (payload = {}) => {
    const normalized = normalizeQaChecks(payload);
    const update = {};

    QA_CHECK_KEYS.forEach((key) => {
        update[`ai.public.qaChecks.${key}`] = normalized[key];
    });

    return update;
};

const buildEnabledQaChecksPrompt = (qaChecks = {}) => {
    const enabledAreas = [];

    if (isQaCheckEnabled(qaChecks, 'redaction'))
        enabledAreas.push('redaction guideline compliance');
    if (isQaCheckEnabled(qaChecks, 'customer'))
        enabledAreas.push('customer and company alignment');
    if (isQaCheckEnabled(qaChecks, 'instructions'))
        enabledAreas.push('organization QA instructions, including any additional required sections or fields defined there');

    if (!enabledAreas.length)
        return '';

    return `Only evaluate these areas: ${enabledAreas.join(', ')}.`;
};

const filterAiIssuesByEnabledChecks = (issues = [], qaChecks = {}) => {
    return issues.filter((issue) => {
        if (QA_CHECK_KEYS.includes(issue.category))
            return isQaCheckEnabled(qaChecks, issue.category);
        return true;
    });
};

const normalizeQaScope = (value) => {
    const scope = String(value || '').trim().toLowerCase();
    return QA_SCOPES.includes(scope) ? scope : null;
};

// `settings` is null when the settings read itself failed — treat that as disabled rather
// than letting optional chaining default a missing document to "enabled".
const isAiEnabled = (settings) => Boolean(settings) && settings?.ai?.public?.enabled !== false;

const isAiQaIssue = (issue = {}) => issue.source === 'ai';

const mergeQaIssues = (existingIssues = [], newIssues = [], scope = 'all') => {
    if (scope === 'all')
        return Array.isArray(newIssues) ? newIssues : [];

    const existing = Array.isArray(existingIssues) ? existingIssues : [];
    const incoming = Array.isArray(newIssues) ? newIssues : [];

    if (scope === 'programmatic')
        return [...existing.filter(isAiQaIssue), ...incoming.filter((issue) => !isAiQaIssue(issue))];

    return [...existing.filter((issue) => !isAiQaIssue(issue)), ...incoming.filter(isAiQaIssue)];
};

const emptyQaCounts = () => ({
    total: 0,
    error: 0,
    warning: 0,
    info: 0
});

const buildIssueCounts = (issues = []) => ({
    total: issues.length,
    error: issues.filter((issue) => issue.severity === 'error').length,
    warning: issues.filter((issue) => issue.severity === 'warning').length,
    info: issues.filter((issue) => issue.severity === 'info').length
});

// Count line for saved/merged reports. Empty fallbacks stay generic — callers that need
// template-vs-report wording pass emptyFallback.
const buildIssueSummary = (issues = [], { aiSummary = '', emptyFallback = 'No issues were flagged.' } = {}) => {
    const counts = buildIssueCounts(issues);
    const narrative = String(aiSummary || '').trim();

    if (!issues.length)
        return narrative || emptyFallback;

    const parts = [`${issues.length} issue(s) flagged`];
    if (counts.error)
        parts.push(`${counts.error} error(s)`);
    if (counts.warning)
        parts.push(`${counts.warning} warning(s)`);
    if (counts.info)
        parts.push(`${counts.info} info(s)`);

    return narrative ? `${parts.join(', ')}. ${narrative}` : `${parts.join(', ')}.`;
};

const resolveMergedEmptyFallback = (partialResult = {}) => {
    const vulnerabilityCount = Number(partialResult.vulnerabilityCount) || 0;
    if (vulnerabilityCount > 1)
        return `No issues were flagged across ${vulnerabilityCount} vulnerability templates.`;
    if (vulnerabilityCount === 1 || partialResult.mode === 'single')
        return 'No issues were flagged. The vulnerability template looks ready to use.';
    return 'No issues were flagged. The report appears ready for generation.';
};

const finalizeMergedQaResult = (existingStored = {}, partialResult = {}, mergedIssues = []) => {
    const progressIncomplete = partialResult.progress && partialResult.progress.done === false;
    // Keep AI prose only when this pass contributed AI analysis; otherwise counts alone.
    const aiSummary = partialResult.aiAnalysis ?
        String(partialResult.summary || '').replace(/^\d+ issue\(s\) flagged[^.]*\.\s*/i, '').trim() :
        '';

    let summary = buildIssueSummary(mergedIssues, {
        aiSummary: aiSummary,
        emptyFallback: resolveMergedEmptyFallback(partialResult)
    });

    // Don't claim "no issues across the catalog" while chunks are still running.
    if (progressIncomplete && !mergedIssues.length)
        summary = '';

    return {
        summary: summary,
        issues: mergedIssues,
        aiAnalysis: Boolean(
            partialResult.aiAnalysis ||
            existingStored.aiAnalysis ||
            mergedIssues.some(isAiQaIssue)
        ),
        provider: partialResult.provider || existingStored.provider || null,
        model: partialResult.model || existingStored.model || null,
        counts: buildIssueCounts(mergedIssues)
    };
};

module.exports = {
    QA_CHECK_KEYS,
    QA_SCOPES,
    defaultQaChecks,
    normalizeQaChecks,
    getQaChecksFromSettings,
    isQaCheckEnabled,
    hasEnabledAiQaChecks,
    hasEnabledQaChecks,
    validateQaChecksPayload,
    buildQaChecksSettingsUpdate,
    buildEnabledQaChecksPrompt,
    filterAiIssuesByEnabledChecks,
    normalizeQaScope,
    isAiEnabled,
    isAiQaIssue,
    mergeQaIssues,
    emptyQaCounts,
    buildIssueCounts,
    buildIssueSummary,
    finalizeMergedQaResult
};
