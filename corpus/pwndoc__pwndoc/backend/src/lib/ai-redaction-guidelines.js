const normalizeString = (value) => String(value || '').trim();

const normalizeRedactionGuidelines = (raw = {}) => {
    return {
        content: String(raw.content || '')
    };
};

const getRedactionGuidelinesFromSettings = (settings = {}) => {
    return normalizeRedactionGuidelines(settings?.ai?.public?.redactionGuidelines || {});
};

const resolveRedactionGuidelinesForRequest = (settings = {}) => {
    const guidelines = getRedactionGuidelinesFromSettings(settings);

    return {
        content: normalizeString(guidelines.content)
    };
};

const getRedactionGuidelinesText = (resolved = {}) => {
    return resolved.content || '';
};

const appendRedactionGuidelinesToSystemPrompt = (systemPrompt, resolved = {}) => {
    const guidelinesText = getRedactionGuidelinesText(resolved);
    if (!guidelinesText)
        return systemPrompt;

    return [
        systemPrompt,
        'Follow these organization writing guidelines when writing or editing report content:',
        guidelinesText
    ].join(' ');
};

const validateRedactionGuidelinesPayload = (payload) => {
    if (payload === null || typeof payload !== 'object' || Array.isArray(payload))
        return { valid: false, message: 'Invalid redactionGuidelines payload' };

    if (typeof payload.content !== 'string')
        return { valid: false, message: 'Invalid redactionGuidelines.content payload' };

    return { valid: true };
};

const buildRedactionGuidelinesSettingsUpdate = (payload = {}) => {
    const normalized = normalizeRedactionGuidelines(payload);

    return {
        'ai.public.redactionGuidelines.content': normalized.content
    };
};

module.exports = {
    normalizeRedactionGuidelines,
    getRedactionGuidelinesFromSettings,
    resolveRedactionGuidelinesForRequest,
    getRedactionGuidelinesText,
    appendRedactionGuidelinesToSystemPrompt,
    validateRedactionGuidelinesPayload,
    buildRedactionGuidelinesSettingsUpdate
};
