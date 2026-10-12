const normalizeString = (value) => String(value || '').trim();

const normalizeQaInstructions = (raw = {}) => {
    return {
        content: String(raw.content || '')
    };
};

const getQaInstructionsFromSettings = (settings = {}) => {
    return normalizeQaInstructions(settings?.ai?.public?.qaInstructions || {});
};

const resolveQaInstructionsForRequest = (settings = {}) => {
    const instructions = getQaInstructionsFromSettings(settings);

    return {
        content: normalizeString(instructions.content)
    };
};

const getQaInstructionsText = (resolved = {}) => {
    return resolved.content || '';
};

const validateQaInstructionsPayload = (payload) => {
    if (payload === null || typeof payload !== 'object' || Array.isArray(payload))
        return { valid: false, message: 'Invalid qaInstructions payload' };

    if (typeof payload.content !== 'string')
        return { valid: false, message: 'Invalid qaInstructions.content payload' };

    return { valid: true };
};

const buildQaInstructionsSettingsUpdate = (payload = {}) => {
    const normalized = normalizeQaInstructions(payload);

    return {
        'ai.public.qaInstructions.content': normalized.content
    };
};

module.exports = {
    normalizeQaInstructions,
    getQaInstructionsFromSettings,
    resolveQaInstructionsForRequest,
    getQaInstructionsText,
    validateQaInstructionsPayload,
    buildQaInstructionsSettingsUpdate
};
