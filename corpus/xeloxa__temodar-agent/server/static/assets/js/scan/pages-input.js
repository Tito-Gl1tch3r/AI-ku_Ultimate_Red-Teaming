(function() {
const RANDOM_PAGES_MIN = 1;
const RANDOM_PAGES_MAX = 50;
const PAGES_FIXED_ATTR = 'data-pages-fixed';

function getPagesInput() {
    return document.querySelector('#configForm input[name="pages"]');
}

function randomInt(min, max) {
    return Math.floor(Math.random() * (max - min + 1)) + min;
}

function clampPagesValue(value) {
    if (!Number.isFinite(value)) return randomInt(RANDOM_PAGES_MIN, RANDOM_PAGES_MAX);
    return Math.max(RANDOM_PAGES_MIN, Math.min(RANDOM_PAGES_MAX, value));
}

function isPagesFixedByUser() {
    const input = getPagesInput();
    return !!input && input.getAttribute(PAGES_FIXED_ATTR) === '1';
}

function setRandomPagesValue(force = false) {
    const input = getPagesInput();
    if (!input) return;
    if (!force && isPagesFixedByUser()) return;
    input.value = String(randomInt(RANDOM_PAGES_MIN, RANDOM_PAGES_MAX));
    if (!isPagesFixedByUser()) {
        input.setAttribute(PAGES_FIXED_ATTR, '0');
    }
}

function initializePagesAutoRandom() {
    const input = getPagesInput();
    if (!input) return;

    input.setAttribute(PAGES_FIXED_ATTR, '0');
    input.min = String(RANDOM_PAGES_MIN);
    input.max = String(RANDOM_PAGES_MAX);

    const markFixedOrRandom = () => {
        const raw = String(input.value || '').trim();
        if (!raw) {
            input.setAttribute(PAGES_FIXED_ATTR, '0');
            setRandomPagesValue(true);
            return;
        }

        const parsed = Number.parseInt(raw, 10);
        if (!Number.isFinite(parsed)) {
            input.setAttribute(PAGES_FIXED_ATTR, '0');
            setRandomPagesValue(true);
            return;
        }

        const clamped = clampPagesValue(parsed);
        input.value = String(clamped);
        input.setAttribute(PAGES_FIXED_ATTR, '1');
    };

    input.addEventListener('input', () => {
        const raw = String(input.value || '').trim();
        if (!raw) {
            input.setAttribute(PAGES_FIXED_ATTR, '0');
            return;
        }
        const parsed = Number.parseInt(raw, 10);
        if (Number.isFinite(parsed)) {
            input.setAttribute(PAGES_FIXED_ATTR, '1');
        }
    });

    input.addEventListener('blur', markFixedOrRandom);

    setRandomPagesValue(true);
}

function preparePagesValueBeforeScan() {
    const input = getPagesInput();
    if (!input) return randomInt(RANDOM_PAGES_MIN, RANDOM_PAGES_MAX);
    if (!isPagesFixedByUser()) {
        setRandomPagesValue(true);
    }
    const parsed = Number.parseInt(String(input.value || ''), 10);
    const clamped = clampPagesValue(parsed);
    input.value = String(clamped);
    return clamped;
}


    window.initializePagesAutoRandom = initializePagesAutoRandom;
    window.preparePagesValueBeforeScan = preparePagesValueBeforeScan;
})();
