const crypto = require('crypto');
const mongoose = require('mongoose');
const { runWithConcurrency } = require('./utils');
const {
    getQaChecksFromSettings,
    isQaCheckEnabled,
    hasEnabledAiQaChecks,
    normalizeQaScope,
    mergeQaIssues,
    finalizeMergedQaResult,
    buildIssueCounts,
    buildIssueSummary,
    isAiQaIssue
} = require('./ai-qa-checks');
const {
    buildQaTargets,
    runVulnerabilityQa,
    runDuplicateChecks,
    dedupeIssues,
    sortIssues
} = require('./ai-vuln-qa');
// Top-level (not lazy) so a test sandboxing this module gets these dependencies from the
// same module registry. No cycle: these two require ai-vuln-qa, nothing requires this file.
const {
    buildVulnerabilityCatalog,
    buildDuplicateBatches,
    runAiDuplicateChecks
} = require('./ai-vuln-duplicate-ai');
const { runAiUnlinkedTranslationChecks } = require('./ai-vuln-translation-ai');
const {
    computeVulnerabilityQaFingerprint,
    computeVulnerabilityQaCatalogFingerprint,
    normalizeLocaleQaReport,
    isStoredReportCurrentForScope,
    buildVulnerabilityQaReportCache,
    getLatestVulnerabilityQaReport,
    hasStoredRun
} = require('./ai-vuln-qa-cache');
const { buildQaReportCache } = require('./ai-qa-cache');

// One in-memory job per locale. PwnDoc runs as a single Node process and an in-flight
// LLM call cannot survive a restart anyway; results are persisted incrementally
// (per-vulnerability qaReports + the catalog document), so after a restart the job
// record simply disappears and the next run reuses everything already completed.
const jobs = new Map();

const VULN_QA_ROOM = 'vuln-qa';
const QA_JOB_CONCURRENCY = Math.max(1, Math.min(5, Number.parseInt(process.env.AI_QA_CONCURRENCY, 10) || 3));
const PROGRESS_EMIT_INTERVAL_MS = 1000;
const TRANSIENT_RETRY_DELAY_MS = Number.parseInt(process.env.AI_QA_RETRY_DELAY_MS, 10) >= 0 ?
    Number.parseInt(process.env.AI_QA_RETRY_DELAY_MS, 10) :
    2000;

const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

const serializeJob = (job) => {
    if (!job)
        return null;

    return {
        id: job.id,
        locale: job.locale,
        scope: job.scope,
        state: job.state,
        phase: job.phase,
        startedAt: job.startedAt,
        finishedAt: job.finishedAt,
        total: job.total,
        processed: job.processed,
        reused: job.reused,
        catalogDone: job.catalogDone,
        catalogTotal: job.catalogTotal,
        failures: job.failures,
        revision: job.revision
    };
};

// The socket room can be joined without authentication (see the generic `join` handler
// in app.js), so progress events carry counters only — never issue content. Clients
// fetch the actual report through the authenticated status endpoint.
const buildProgressPayload = (job) => ({
    locale: job.locale,
    jobId: job.id,
    state: job.state,
    phase: job.phase,
    processed: job.processed,
    reused: job.reused,
    total: job.total,
    catalogDone: job.catalogDone,
    catalogTotal: job.catalogTotal,
    revision: job.revision
});

const emitProgress = (job, { force = false } = {}) => {
    if (!job.io)
        return;

    const now = Date.now();
    if (!force && now - job.lastEmitAt < PROGRESS_EMIT_INTERVAL_MS)
        return;

    job.lastEmitAt = now;
    job.io.to(VULN_QA_ROOM).emit('vuln-qa:progress', buildProgressPayload(job));
};

const emitDone = (job) => {
    if (!job.io)
        return;
    job.io.to(VULN_QA_ROOM).emit('vuln-qa:done', buildProgressPayload(job));
};

const isJobActive = (job) => Boolean(job && (job.state === 'running' || job.state === 'cancelling'));

const recordFailure = (job, failure) => {
    job.failures.push({
        vulnerabilityId: failure.vulnerabilityId || null,
        title: failure.title || '',
        message: String(failure.message || 'Unknown error')
    });
};

// Runs template-scoped QA for one vulnerability and persists the qaReports entry.
// When the content fingerprint changed, the previous entry is discarded instead of
// merged: its other-scope issues/timestamps describe content that no longer exists.
const runTemplateTask = async (job, entry, { settings, provider }) => {
    const Vulnerability = mongoose.model('Vulnerability');
    const scope = job.scope;
    const runAi = scope === 'all' || scope === 'ai';
    const aiContentChecksEnabled = hasEnabledAiQaChecks(getQaChecksFromSettings(settings));

    const runOnce = () => runVulnerabilityQa({
        vulnerability: entry.vulnerability,
        locale: job.locale,
        settings: settings,
        provider: provider,
        scope: scope
    });

    let result = await runOnce();
    const aiPassFailed = () => runAi && aiContentChecksEnabled && !result.aiAnalysis && result.aiSkippedReason;

    // One retry with backoff: provider hiccups (rate limits, transient 5xx) are the
    // usual cause with parallel workers, and ai-client itself runs with maxRetries: 0.
    if (aiPassFailed() && !job.cancelRequested) {
        await delay(TRANSIENT_RETRY_DELAY_MS);
        result = await runOnce();
    }

    let persistScope = scope;
    if (aiPassFailed()) {
        recordFailure(job, {
            vulnerabilityId: result.vulnerabilityId,
            title: result.title,
            message: result.aiSkippedReason
        });

        // Persist nothing for a pure AI run, and only the programmatic half for 'all':
        // leaving aiRanAt unset is what makes the next run retry this template.
        if (scope === 'ai')
            return;
        persistScope = 'programmatic';
    }

    const fingerprintMatches = entry.stored?.fingerprint === entry.fingerprint;
    const existingReport = fingerprintMatches ?
        (getLatestVulnerabilityQaReport(entry.vulnerability, job.locale) || {}) :
        {};

    const mergedIssues = mergeQaIssues(existingReport.issues || [], result.issues || [], persistScope);
    const mergedResult = finalizeMergedQaResult(existingReport, result, mergedIssues);
    const qaReport = buildVulnerabilityQaReportCache(entry.fingerprint, mergedResult, {
        locale: job.locale,
        mode: 'single',
        vulnerabilityId: result.vulnerabilityId,
        title: result.title
    }, {
        existing: fingerprintMatches ? existingReport : {},
        scope: persistScope
    });

    await Vulnerability.saveQaReportForLocale(entry.vulnerability._id, job.locale, qaReport);
    job.revision += 1;
};

const buildCatalogUnits = ({ job, vulnerabilities, settings, provider, qaChecks }) => {
    const scope = job.scope;
    const runProgrammatic = scope === 'all' || scope === 'programmatic';
    const runAi = scope === 'all' || scope === 'ai';
    const units = [];

    if (runProgrammatic && isQaCheckEnabled(qaChecks, 'duplicates')) {
        units.push({
            kind: 'duplicates',
            ai: false,
            skipTitle: 'Duplicate check skipped',
            run: async () => ({
                issues: runDuplicateChecks({ vulnerabilities: vulnerabilities, locale: job.locale })
            })
        });
    }

    if (runAi && isQaCheckEnabled(qaChecks, 'aiDuplicates')) {
        const batchCount = buildDuplicateBatches(buildVulnerabilityCatalog(vulnerabilities, job.locale)).length;

        for (let index = 0; index < batchCount; index++) {
            units.push({
                kind: 'aiDuplicates',
                ai: true,
                skipTitle: 'AI duplicate review skipped',
                run: () => runAiDuplicateChecks({
                    vulnerabilities: vulnerabilities,
                    locale: job.locale,
                    settings: settings,
                    provider: provider,
                    typeBatchIndex: index
                })
            });
        }
    }

    if (runAi && isQaCheckEnabled(qaChecks, 'aiUnlinkedTranslations')) {
        units.push({
            kind: 'aiUnlinkedTranslations',
            ai: true,
            skipTitle: 'AI translation link review skipped',
            run: () => runAiUnlinkedTranslationChecks({
                vulnerabilities: vulnerabilities,
                settings: settings,
                provider: provider
            })
        });
    }

    return units;
};

const runCatalogPhase = async (job, { vulnerabilities, targets, settings, provider, qaChecks }) => {
    const VulnerabilityQaCatalog = mongoose.model('VulnerabilityQaCatalog');
    const scope = job.scope;

    const catalogFingerprint = computeVulnerabilityQaCatalogFingerprint(vulnerabilities, job.locale);
    const catalogDoc = await VulnerabilityQaCatalog.getByLocale(job.locale);

    const units = buildCatalogUnits({ job, vulnerabilities, settings, provider, qaChecks });
    if (!units.length || targets.length === 0)
        return;

    if (isStoredReportCurrentForScope(catalogDoc, catalogFingerprint, scope)) {
        job.catalogReused = true;
        return;
    }

    job.catalogTotal = units.length;
    emitProgress(job, { force: true });

    const collected = [];
    let aiAnalysis = false;
    let providerUsed = null;
    let modelUsed = null;
    let anyAiUnitFailed = false;

    const results = await runWithConcurrency(units, QA_JOB_CONCURRENCY, async (unit) => {
        try {
            const result = await unit.run();
            collected.push(...(result.issues || []));
            if (unit.ai && result.provider) {
                aiAnalysis = true;
                providerUsed = providerUsed || result.provider;
                modelUsed = modelUsed || result.model || null;
            }
        } catch (err) {
            if (unit.ai)
                anyAiUnitFailed = true;
            recordFailure(job, { title: unit.kind, message: err?.message || String(err) });
            collected.push({
                severity: 'info',
                category: 'other',
                title: unit.skipTitle,
                message: `${unit.skipTitle.replace(/ skipped$/, '')} could not run: ${err?.message || String(err)}`,
                location: 'vulnerability database',
                source: 'structural'
            });
        }
        job.catalogDone += 1;
        emitProgress(job);
    }, { shouldStop: () => job.cancelRequested });

    // A cancelled catalog phase is not persisted: a half-run catalog merged per scope
    // would silently drop findings. The previous document stays and the assembled
    // report keeps flagging it outdated, which is the truthful state.
    if (results.some((result) => result?.status === 'skipped'))
        return;

    let persistScope = scope;
    if (anyAiUnitFailed) {
        if (scope === 'ai')
            return;
        persistScope = 'programmatic';
    }

    const fingerprintMatches = catalogDoc?.fingerprint === catalogFingerprint;
    const existingIssues = fingerprintMatches && hasStoredRun(catalogDoc) && Array.isArray(catalogDoc.issues) ?
        catalogDoc.issues :
        [];

    const mergedIssues = sortIssues(dedupeIssues(mergeQaIssues(existingIssues, collected, persistScope)));
    const report = buildQaReportCache(catalogFingerprint, {
        summary: buildIssueSummary(mergedIssues, {
            emptyFallback: `No catalog-level issues were flagged across ${targets.length} vulnerability templates.`
        }),
        issues: mergedIssues,
        aiAnalysis: aiAnalysis || (fingerprintMatches && Boolean(catalogDoc?.aiAnalysis)) || mergedIssues.some(isAiQaIssue),
        provider: providerUsed || (fingerprintMatches ? catalogDoc?.provider : null) || null,
        model: modelUsed || (fingerprintMatches ? catalogDoc?.model : null) || null,
        counts: buildIssueCounts(mergedIssues)
    }, {
        existing: fingerprintMatches ? (catalogDoc || {}) : {},
        scope: persistScope
    });
    report.vulnerabilityCount = targets.length;

    await VulnerabilityQaCatalog.saveForLocale(job.locale, report);
    job.revision += 1;
};

const runJob = async (job, { settings, provider }) => {
    const Vulnerability = mongoose.model('Vulnerability');
    const qaChecks = getQaChecksFromSettings(settings);

    const vulnerabilities = await Vulnerability.getAllForQa();
    const targets = buildQaTargets(vulnerabilities, job.locale);
    job.total = targets.length;

    const pending = [];
    for (const target of targets) {
        const fingerprint = computeVulnerabilityQaFingerprint(target.vulnerability, job.locale);
        const stored = normalizeLocaleQaReport(target.vulnerability.qaReports, job.locale);

        if (isStoredReportCurrentForScope(stored, fingerprint, job.scope))
            job.reused += 1;
        else
            pending.push({ ...target, fingerprint, stored });
    }
    emitProgress(job, { force: true });

    await runWithConcurrency(pending, QA_JOB_CONCURRENCY, async (entry) => {
        try {
            await runTemplateTask(job, entry, { settings, provider });
        } catch (err) {
            recordFailure(job, {
                vulnerabilityId: String(entry.vulnerability._id || ''),
                title: String(entry.detail.title || '').trim(),
                message: err?.message || String(err)
            });
        }
        job.processed += 1;
        emitProgress(job);
    }, { shouldStop: () => job.cancelRequested });

    if (!job.cancelRequested) {
        job.phase = 'catalog';
        await runCatalogPhase(job, { vulnerabilities, targets, settings, provider, qaChecks });
    }
};

const startVulnerabilityQaJob = ({ locale, scope, provider, settings, io }) => {
    const normalizedLocale = String(locale || '').trim();
    const normalizedScope = normalizeQaScope(scope) || 'all';

    const existing = jobs.get(normalizedLocale);
    if (isJobActive(existing))
        return { alreadyRunning: true, job: existing };

    const job = {
        id: crypto.randomUUID(),
        locale: normalizedLocale,
        scope: normalizedScope,
        state: 'running',
        phase: 'templates',
        startedAt: new Date(),
        finishedAt: null,
        total: 0,
        processed: 0,
        reused: 0,
        catalogDone: 0,
        catalogTotal: 0,
        catalogReused: false,
        failures: [],
        revision: 0,
        cancelRequested: false,
        lastEmitAt: 0,
        io: io || null,
        promise: null
    };
    jobs.set(normalizedLocale, job);

    job.promise = runJob(job, { settings, provider })
        .then(() => {
            job.state = job.cancelRequested ? 'cancelled' : 'done';
        })
        .catch((err) => {
            job.state = 'failed';
            recordFailure(job, { message: err?.message || String(err) });
        })
        .then(() => {
            job.finishedAt = new Date();
            emitDone(job);
        });

    return { alreadyRunning: false, job };
};

const getVulnerabilityQaJob = (locale) => jobs.get(String(locale || '').trim()) || null;

const getVulnerabilityQaJobStatus = (locale) => serializeJob(getVulnerabilityQaJob(locale));

const isVulnerabilityQaJobActive = (locale) => isJobActive(getVulnerabilityQaJob(locale));

const cancelVulnerabilityQaJob = (locale) => {
    const job = getVulnerabilityQaJob(locale);
    if (!isJobActive(job))
        return null;

    job.cancelRequested = true;
    job.state = 'cancelling';
    emitProgress(job, { force: true });
    return job;
};

module.exports = {
    VULN_QA_ROOM,
    QA_JOB_CONCURRENCY,
    startVulnerabilityQaJob,
    getVulnerabilityQaJob,
    getVulnerabilityQaJobStatus,
    isVulnerabilityQaJobActive,
    cancelVulnerabilityQaJob,
    serializeJob
};
