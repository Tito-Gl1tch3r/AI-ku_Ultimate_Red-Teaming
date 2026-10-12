const realMongoose = require('mongoose');

// index.test.js requires every backend test module into one shared Jest module registry,
// so the ai-client mock is sandboxed with isolateModules (see ai-vuln-duplicate-ai.test.js).
// mongoose is re-mocked to the outer, connected instance so the isolated job module still
// reaches the ephemeral test database and its registered models.
const loadJobModule = (llmMocks = {}) => {
    let jobModule;
    jest.isolateModules(() => {
        jest.doMock('mongoose', () => realMongoose);
        jest.doMock('../src/lib/ai-client', () => ({
            runVulnerabilityTemplateQaWithProvider: llmMocks.templateQa ||
                jest.fn().mockResolvedValue({ issues: [], summary: '', model: 'test-model' }),
            runVulnerabilityDuplicateQaWithProvider: llmMocks.duplicateQa ||
                jest.fn().mockResolvedValue({ issues: [], summary: '', model: 'test-model' }),
            runVulnerabilityUnlinkedTranslationQaWithProvider: llmMocks.translationQa ||
                jest.fn().mockResolvedValue({ issues: [], summary: '', model: 'test-model' })
        }));
        jobModule = require('../src/lib/ai-vuln-qa-job');
    });
    // The sandboxed module keeps its mocked bindings; unregister the factories so later
    // requires elsewhere (this file shares one Jest registry with every backend suite)
    // resolve the real modules again.
    jest.dontMock('mongoose');
    jest.dontMock('../src/lib/ai-client');
    return jobModule;
};

const buildSettings = (qaChecks) => ({
    ai: {
        public: {
            enabled: true,
            defaultProvider: 'openai',
            qaChecks: {
                completeness: true,
                references: false,
                imageCaptions: false,
                duplicates: false,
                aiDuplicates: false,
                aiUnlinkedTranslations: false,
                redaction: true,
                customer: false,
                instructions: false,
                ...qaChecks
            }
        },
        private: {}
    }
});

const buildFakeIo = () => {
    const emit = jest.fn();
    return { io: { to: jest.fn(() => ({ emit })) }, emit };
};

module.exports = function() {
    describe('AI vulnerability QA job', () => {
        const locale = 'en';
        const Vulnerability = realMongoose.model('Vulnerability');
        const VulnerabilityQaCatalog = realMongoose.model('VulnerabilityQaCatalog');
        const createdIds = [];

        const createVulnerabilities = async (count, { titlePrefix = 'Job QA', vulnType = 'JobType' } = {}) => {
            const docs = await Vulnerability.insertMany(Array.from({ length: count }, (_, i) => ({
                category: 'Web',
                details: [{
                    locale: locale,
                    title: `${titlePrefix} ${i} ${Date.now()}`,
                    vulnType: vulnType,
                    description: `<p>Description ${i}</p>`,
                    observation: `<p>Observation ${i}</p>`,
                    remediation: `<p>Remediation ${i}</p>`
                }]
            })));
            docs.forEach((doc) => createdIds.push(doc._id));
            return docs;
        };

        const runJobToCompletion = async (jobModule, options) => {
            const { alreadyRunning, job } = jobModule.startVulnerabilityQaJob(options);
            expect(alreadyRunning).toBe(false);
            await job.promise;
            return job;
        };

        beforeAll(() => {
            process.env.AI_QA_RETRY_DELAY_MS = '0';
        });

        afterAll(async () => {
            delete process.env.AI_QA_RETRY_DELAY_MS;
        });

        beforeEach(async () => {
            await Vulnerability.deleteMany({ _id: { $in: createdIds } });
            createdIds.length = 0;
            await VulnerabilityQaCatalog.deleteMany({ locale: locale });
        });

        it('should run the full pipeline, persist per-template reports and emit socket counters only', async () => {
            await createVulnerabilities(4);
            const templateQa = jest.fn().mockResolvedValue({
                issues: [{ severity: 'warning', category: 'redaction', title: 'Found', message: 'x', location: 'vulnerability:a' }],
                summary: 'checked',
                model: 'test-model'
            });
            const jobModule = loadJobModule({ templateQa });
            const { io, emit } = buildFakeIo();

            const job = await runJobToCompletion(jobModule, {
                locale: locale,
                scope: 'all',
                provider: 'openai',
                settings: buildSettings({ duplicates: true }),
                io: io
            });

            expect(job.state).toBe('done');
            expect(job.total).toBeGreaterThanOrEqual(4);
            expect(job.processed + job.reused).toBe(job.total);
            expect(templateQa.mock.calls.length).toBeGreaterThanOrEqual(4);

            const stored = await Vulnerability.find({ _id: { $in: createdIds } }).lean();
            stored.forEach((vulnerability) => {
                const entry = vulnerability.qaReports.find((report) => report.locale === locale);
                expect(entry).toBeDefined();
                expect(entry.fingerprint).toBeTruthy();
                expect(entry.programmaticRanAt).toBeTruthy();
                expect(entry.aiRanAt).toBeTruthy();
            });

            const catalogDoc = await VulnerabilityQaCatalog.getByLocale(locale);
            expect(catalogDoc).toBeTruthy();
            expect(catalogDoc.fingerprint).toBeTruthy();

            // Unauthenticated socket room: payloads must be counters only.
            expect(emit).toHaveBeenCalled();
            emit.mock.calls.forEach(([event, payload]) => {
                expect(['vuln-qa:progress', 'vuln-qa:done']).toContain(event);
                expect(payload).not.toHaveProperty('issues');
                expect(payload).not.toHaveProperty('report');
                expect(payload).not.toHaveProperty('summary');
            });
            const doneEvents = emit.mock.calls.filter(([event]) => event === 'vuln-qa:done');
            expect(doneEvents).toHaveLength(1);
            expect(doneEvents[0][1].state).toBe('done');
        });

        it('should bound LLM concurrency to the worker pool size', async () => {
            await createVulnerabilities(8);
            let inFlight = 0;
            let maxInFlight = 0;
            const templateQa = jest.fn().mockImplementation(async () => {
                inFlight += 1;
                maxInFlight = Math.max(maxInFlight, inFlight);
                await new Promise((resolve) => setTimeout(resolve, 20));
                inFlight -= 1;
                return { issues: [], summary: '', model: 'test-model' };
            });
            const jobModule = loadJobModule({ templateQa });

            const job = await runJobToCompletion(jobModule, {
                locale: locale,
                scope: 'ai',
                provider: 'openai',
                settings: buildSettings({}),
                io: null
            });

            expect(job.state).toBe('done');
            expect(maxInFlight).toBeGreaterThan(1);
            expect(maxInFlight).toBeLessThanOrEqual(jobModule.QA_JOB_CONCURRENCY);
        });

        it('should reuse unchanged templates on re-run and re-check only mutated ones', async () => {
            const docs = await createVulnerabilities(3);
            const templateQa = jest.fn().mockResolvedValue({ issues: [], summary: '', model: 'test-model' });
            const jobModule = loadJobModule({ templateQa });
            const settings = buildSettings({});

            const first = await runJobToCompletion(jobModule, {
                locale, scope: 'all', provider: 'openai', settings, io: null
            });
            expect(first.state).toBe('done');
            const callsAfterFirst = templateQa.mock.calls.length;
            expect(callsAfterFirst).toBeGreaterThanOrEqual(3);

            // Unchanged catalog: everything is served from the stored reports.
            const second = await runJobToCompletion(jobModule, {
                locale, scope: 'all', provider: 'openai', settings, io: null
            });
            expect(second.state).toBe('done');
            expect(second.reused).toBe(second.total);
            expect(second.processed).toBe(0);
            expect(templateQa.mock.calls.length).toBe(callsAfterFirst);

            // Mutate one template: exactly that one is re-checked.
            await Vulnerability.updateOne(
                { _id: docs[0]._id },
                { $set: { 'details.0.remediation': '<p>Changed remediation</p>' } }
            );
            const third = await runJobToCompletion(jobModule, {
                locale, scope: 'all', provider: 'openai', settings, io: null
            });
            expect(third.state).toBe('done');
            expect(third.processed).toBe(1);
            expect(third.reused).toBe(third.total - 1);
            expect(templateQa.mock.calls.length).toBe(callsAfterFirst + 1);
        });

        it('should isolate per-template AI failures, keep the programmatic half and retry them next run', async () => {
            const docs = await createVulnerabilities(2);
            const failingTitle = docs[0].details[0].title;
            let failuresLeft = 2; // initial attempt + one retry for the same template
            const templateQa = jest.fn().mockImplementation(async (args) => {
                if (args.templateSnapshot.finding.title === failingTitle && failuresLeft > 0) {
                    failuresLeft -= 1;
                    throw new Error('rate limited');
                }
                return { issues: [], summary: '', model: 'test-model' };
            });
            const jobModule = loadJobModule({ templateQa });
            const settings = buildSettings({});

            const job = await runJobToCompletion(jobModule, {
                locale, scope: 'all', provider: 'openai', settings, io: null
            });

            expect(job.state).toBe('done');
            expect(job.failures).toHaveLength(1);
            expect(job.failures[0].title).toBe(failingTitle);

            const failed = await Vulnerability.findById(docs[0]._id).lean();
            const failedEntry = failed.qaReports.find((report) => report.locale === locale);
            expect(failedEntry.programmaticRanAt).toBeTruthy();
            expect(failedEntry.aiRanAt).toBeFalsy();

            const healthy = await Vulnerability.findById(docs[1]._id).lean();
            const healthyEntry = healthy.qaReports.find((report) => report.locale === locale);
            expect(healthyEntry.aiRanAt).toBeTruthy();

            // Next run: only the failed template needs its AI pass again.
            const retryRun = await runJobToCompletion(jobModule, {
                locale, scope: 'all', provider: 'openai', settings, io: null
            });
            expect(retryRun.state).toBe('done');
            expect(retryRun.processed).toBe(1);
            expect(retryRun.failures).toHaveLength(0);
        });

        it('should guard against concurrent runs per locale and cancel cleanly', async () => {
            await createVulnerabilities(6);
            let release;
            const gate = new Promise((resolve) => { release = resolve; });
            const templateQa = jest.fn().mockImplementation(async () => {
                await gate;
                return { issues: [], summary: '', model: 'test-model' };
            });
            const jobModule = loadJobModule({ templateQa });
            const settings = buildSettings({});

            const { job } = jobModule.startVulnerabilityQaJob({
                locale, scope: 'all', provider: 'openai', settings, io: null
            });

            const duplicate = jobModule.startVulnerabilityQaJob({
                locale, scope: 'all', provider: 'openai', settings, io: null
            });
            expect(duplicate.alreadyRunning).toBe(true);
            expect(duplicate.job.id).toBe(job.id);
            expect(jobModule.isVulnerabilityQaJobActive(locale)).toBe(true);

            const cancelled = jobModule.cancelVulnerabilityQaJob(locale);
            expect(cancelled.state).toBe('cancelling');
            release();
            await job.promise;

            expect(job.state).toBe('cancelled');
            // In-flight workers finish, queued templates are skipped.
            expect(job.processed).toBeLessThan(job.total);
            expect(jobModule.cancelVulnerabilityQaJob(locale)).toBeNull();

            // A new run can start after cancellation and completes the remainder.
            const rerun = await runJobToCompletion(jobModule, {
                locale, scope: 'all', provider: 'openai', settings, io: null
            });
            expect(rerun.state).toBe('done');
            expect(rerun.processed + rerun.reused).toBe(rerun.total);
        });

        it('should record catalog failures without failing the job', async () => {
            await createVulnerabilities(3);
            const duplicateQa = jest.fn().mockRejectedValue(new Error('provider down'));
            const templateQa = jest.fn().mockResolvedValue({ issues: [], summary: '', model: 'test-model' });
            const jobModule = loadJobModule({ templateQa, duplicateQa });

            const job = await runJobToCompletion(jobModule, {
                locale, scope: 'all', provider: 'openai',
                settings: buildSettings({ duplicates: true, aiDuplicates: true }),
                io: null
            });

            expect(job.state).toBe('done');
            expect(job.failures.some((failure) => failure.title === 'aiDuplicates')).toBe(true);

            // AI catalog failure: persisted with the programmatic half only, so the AI
            // catalog pass is retried on the next run.
            const catalogDoc = await VulnerabilityQaCatalog.getByLocale(locale);
            expect(catalogDoc.programmaticRanAt).toBeTruthy();
            expect(catalogDoc.aiRanAt).toBeFalsy();
        });
    });
};
