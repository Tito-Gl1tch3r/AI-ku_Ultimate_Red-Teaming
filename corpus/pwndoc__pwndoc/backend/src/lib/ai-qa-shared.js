const QA_SEVERITIES = ['error', 'warning', 'info'];
const QA_CATEGORIES = ['completeness', 'redaction', 'customer', 'instructions', 'references', 'imageCaptions', 'duplicates', 'aiDuplicates', 'aiUnlinkedTranslations', 'other'];

const stripHtml = (value) => {
    return String(value || '')
        .replace(/<[^<>]*>/g, ' ')
        .replace(/&nbsp;/gi, ' ')
        .replace(/\s+/g, ' ')
        .trim();
};

const isEmptyContent = (value) => {
    if (value === null || value === undefined)
        return true;
    if (Array.isArray(value))
        return value.length === 0 || value.every((entry) => !String(entry || '').trim());
    return !stripHtml(value);
};

const normalizeIssue = (issue = {}, source = 'structural') => {
    const severity = QA_SEVERITIES.includes(issue.severity) ? issue.severity : 'warning';
    const category = QA_CATEGORIES.includes(issue.category) ? issue.category : 'other';

    const normalized = {
        severity: severity,
        category: category,
        title: String(issue.title || 'Issue').trim(),
        message: String(issue.message || '').trim(),
        location: String(issue.location || 'report').trim() || 'report',
        source: source
    };

    // Catalog-level issues (duplicates, unlinked translations) reference the templates
    // they involve so consumers can resolve them without parsing location strings.
    const vulnerabilityIds = Array.isArray(issue.vulnerabilityIds) ?
        [...new Set(issue.vulnerabilityIds.map((id) => String(id || '').trim()).filter(Boolean))] :
        [];
    if (vulnerabilityIds.length)
        normalized.vulnerabilityIds = vulnerabilityIds;

    return normalized;
};

// Overlap keeps a boundary item in two consecutive batches so a duplicate/translation
// pair split across a batch edge still has one batch where both members are compared.
const chunkWithOverlap = (items = [], batchSize, overlap = 0) => {
    const size = Number(batchSize) > 0 ? Number(batchSize) : items.length;
    if (!items.length)
        return [];
    if (items.length <= size)
        return [items];

    const step = Math.max(size - Math.max(Number(overlap) || 0, 0), 1);
    const batches = [];
    for (let start = 0; start < items.length; start += step) {
        const end = Math.min(start + size, items.length);
        batches.push(items.slice(start, end));
        if (end >= items.length)
            break;
    }
    return batches;
};

const summarizeCustomFields = (customFields = []) => {
    return (customFields || [])
        .map((field) => {
            const label = field?.customField?.label || field?.label || 'Custom field';
            const fieldType = field?.customField?.fieldType || field?.fieldType || 'text';
            if (fieldType === 'space')
                return null;

            let textValue = field?.text;
            if (Array.isArray(textValue))
                textValue = textValue.join('\n');
            else if (textValue && typeof textValue === 'object')
                textValue = JSON.stringify(textValue);

            const content = stripHtml(textValue);
            if (!content)
                return null;

            return {
                label: label,
                fieldType: fieldType,
                content: content.slice(0, 4000)
            };
        })
        .filter(Boolean);
};

const isPlainObject = (value) => (
    value !== null &&
    typeof value === 'object' &&
    !Array.isArray(value) &&
    !(value instanceof Date)
);

// Drop null/false/blank/empty containers before LLM prompts — keeps tokens on signal only.
const isLlmEmpty = (value) => {
    if (value == null || value === false)
        return true;
    if (typeof value === 'string' && !value.trim())
        return true;
    if (Array.isArray(value) && value.length === 0)
        return true;
    if (isPlainObject(value) && Object.keys(value).length === 0)
        return true;
    return false;
};

const compactLlmValue = (value) => {
    if (Array.isArray(value)) {
        return value
            .map((entry) => compactLlmValue(entry))
            .filter((entry) => {
                if (isLlmEmpty(entry))
                    return false;

                // Catalog records with no content beyond their database identifier
                // cannot help the model and only consume context-window space.
                if (isPlainObject(entry)) {
                    const keys = Object.keys(entry);
                    if (keys.length === 1 && keys[0] === 'vulnerabilityId')
                        return false;
                }

                return true;
            });
    }

    if (isPlainObject(value)) {
        const out = {};
        Object.keys(value).forEach((key) => {
            const compacted = compactLlmValue(value[key]);
            if (!isLlmEmpty(compacted))
                out[key] = compacted;
        });
        return out;
    }

    return value;
};

const stringifyLlmPayload = (value) => JSON.stringify(compactLlmValue(value));

module.exports = {
    QA_SEVERITIES,
    QA_CATEGORIES,
    stripHtml,
    isEmptyContent,
    normalizeIssue,
    chunkWithOverlap,
    summarizeCustomFields,
    isLlmEmpty,
    compactLlmValue,
    stringifyLlmPayload
};
