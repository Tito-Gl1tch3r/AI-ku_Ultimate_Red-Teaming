const {
    buildVulnerabilityCatalog,
    normalizeAiDuplicateIssues,
    buildDuplicateBatches,
    normalizeTypeKey,
    TYPE_BATCH_CEILING
} = require('../src/lib/ai-vuln-duplicate-ai');

const buildLargeCatalog = (count) => {
    return Array.from({ length: count }, (_, i) => ({
        _id: `vuln-${i}`,
        details: [{
            locale: 'en',
            title: `Template ${i}`,
            description: `<p>Description ${i}</p>`,
            observation: `<p>Observation ${i}</p>`,
            remediation: `<p>Remediation ${i}</p>`
        }]
    }));
};

// index.test.js requires every backend test module into one shared Jest module registry, so a
// top-level jest.mock('../src/lib/ai-client') here would leak into unrelated suites (e.g.
// ai-integration.test.js) that need the real provider dispatch. isolateModules sandboxes the
// mock to a fresh copy of ai-vuln-duplicate-ai.js, required and used entirely inside the callback.
const runAiDuplicateChecksWithMockedProvider = (mockFn, args) => {
    let runAiDuplicateChecks;
    jest.isolateModules(() => {
        jest.doMock('../src/lib/ai-client', () => ({
            runVulnerabilityDuplicateQaWithProvider: mockFn
        }));
        ({ runAiDuplicateChecks } = require('../src/lib/ai-vuln-duplicate-ai'));
    });
    return runAiDuplicateChecks(args);
};

module.exports = function() {
    describe('AI vulnerability duplicate detection', () => {
        const vulnerabilities = [
            {
                _id: 'vuln-1',
                details: [{
                    locale: 'en',
                    title: 'Blind SQL Injection in Authentication',
                    vulnType: 'Injection',
                    description: '<p>SQL injection in login form.</p>',
                    observation: '<p>Found during testing.</p>',
                    remediation: '<p>Use parameterized queries.</p>'
                }]
            },
            {
                _id: 'vuln-2',
                details: [{
                    locale: 'en',
                    title: 'SQLi on Login Page',
                    vulnType: 'Injection',
                    description: '<p>SQL injection in login form.</p>',
                    observation: '<p>Found during testing.</p>',
                    remediation: '<p>Use parameterized queries.</p>'
                }]
            },
            {
                _id: 'vuln-3',
                details: [{
                    locale: 'en',
                    title: 'Reflected XSS',
                    vulnType: 'XSS',
                    description: '<p>XSS in search.</p>',
                    observation: '<p>Found during testing.</p>',
                    remediation: '<p>Encode output.</p>'
                }]
            },
            {
                _id: 'vuln-4',
                details: [{
                    locale: 'en',
                    title: 'Stored XSS',
                    vulnType: 'XSS',
                    description: '<p>XSS in profile.</p>',
                    observation: '<p>Found during testing.</p>',
                    remediation: '<p>Encode output.</p>'
                }]
            },
            {
                _id: 'vuln-5',
                details: [{
                    locale: 'en',
                    title: 'Missing Header',
                    vulnType: '',
                    description: '<p>No CSP.</p>',
                    observation: '<p>Found during testing.</p>',
                    remediation: '<p>Add header.</p>'
                }]
            }
        ];

        it('should build a vulnerability catalog for a locale', () => {
            const catalog = buildVulnerabilityCatalog(vulnerabilities, 'en');
            expect(catalog).toHaveLength(5);
            expect(catalog[0].title).toBe('Blind SQL Injection in Authentication');
        });

        it('should batch the catalog by vulnerability type', () => {
            const catalog = buildVulnerabilityCatalog(vulnerabilities, 'en');
            const batches = buildDuplicateBatches(catalog);

            expect(batches).toHaveLength(2);
            expect(batches.every((batch) => batch.length >= 2)).toBe(true);

            const injectionBatch = batches.find((batch) => batch[0].vulnType === 'Injection');
            const xssBatch = batches.find((batch) => batch[0].vulnType === 'XSS');
            expect(injectionBatch).toHaveLength(2);
            expect(xssBatch).toHaveLength(2);
            expect(batches.some((batch) => normalizeTypeKey(batch[0].vulnType) === '(no type)')).toBe(false);
        });

        it('should split oversized type groups into ceiling-sized batches', () => {
            const oversized = Array.from({ length: TYPE_BATCH_CEILING + 10 }, (_, index) => ({
                vulnerabilityId: `v-${index}`,
                title: `XSS ${index}`,
                vulnType: 'XSS',
                category: 'Web',
                description: 'x',
                observation: 'y',
                remediation: 'z'
            }));

            const batches = buildDuplicateBatches(oversized);
            expect(batches.length).toBeGreaterThan(1);
            expect(batches.every((batch) => batch.length <= TYPE_BATCH_CEILING)).toBe(true);
            expect(batches.every((batch) => batch.length >= 2)).toBe(true);
        });

        it('should normalize AI duplicate issues with related templates', () => {
            const catalog = buildVulnerabilityCatalog(vulnerabilities, 'en');
            const catalogById = new Map(catalog.map((entry) => [entry.vulnerabilityId, entry]));
            const catalogByTitle = new Map(catalog.map((entry) => [entry.title.toLowerCase(), entry]));

            const issues = normalizeAiDuplicateIssues([
                {
                    severity: 'warning',
                    title: 'Likely duplicate vulnerability',
                    message: 'Both templates describe SQL injection in the login form.',
                    vulnerabilityId: 'vuln-1',
                    templateTitle: 'Blind SQL Injection in Authentication',
                    relatedTemplates: [{
                        vulnerabilityId: 'vuln-2',
                        title: 'SQLi on Login Page',
                        reason: 'Both describe SQL injection in the login form.'
                    }]
                }
            ], {
                catalogById: catalogById,
                catalogByTitle: catalogByTitle
            });

            expect(issues).toHaveLength(1);
            expect(issues[0].category).toBe('aiDuplicates');
            expect(issues[0].source).toBe('ai');
            expect(issues[0].message).toContain('SQLi on Login Page');
        });

        it('should filter AI duplicate issues to a target vulnerability', () => {
            const catalog = buildVulnerabilityCatalog(vulnerabilities, 'en');
            const catalogById = new Map(catalog.map((entry) => [entry.vulnerabilityId, entry]));
            const catalogByTitle = new Map(catalog.map((entry) => [entry.title.toLowerCase(), entry]));

            const issues = normalizeAiDuplicateIssues([
                {
                    severity: 'warning',
                    title: 'Likely duplicate vulnerability',
                    vulnerabilityId: 'vuln-1',
                    templateTitle: 'Blind SQL Injection in Authentication',
                    relatedTemplates: [{
                        vulnerabilityId: 'vuln-2',
                        title: 'SQLi on Login Page'
                    }]
                }
            ], {
                targetVulnerabilityId: 'vuln-2',
                catalogById: catalogById,
                catalogByTitle: catalogByTitle
            });

            expect(issues).toHaveLength(1);
            expect(issues[0].location).toBe('vulnerability:SQLi on Login Page');
        });

        describe('batching large catalogs', () => {
            it('should send a single request when the catalog fits in one batch', async () => {
                const mockFn = jest.fn().mockResolvedValue({ issues: [], summary: 'ok', model: 'test-model' });

                const result = await runAiDuplicateChecksWithMockedProvider(mockFn, {
                    vulnerabilities: buildLargeCatalog(10),
                    locale: 'en',
                    settings: {},
                    provider: 'anthropic'
                });

                expect(mockFn).toHaveBeenCalledTimes(1);
                expect(mockFn.mock.calls[0][0].templates).toHaveLength(10);
                expect(result.model).toBe('test-model');
            });

            it('should split a large "all templates" catalog into multiple batched requests', async () => {
                const mockFn = jest.fn().mockResolvedValue({ issues: [], summary: '', model: 'test-model' });

                await runAiDuplicateChecksWithMockedProvider(mockFn, {
                    vulnerabilities: buildLargeCatalog(90),
                    locale: 'en',
                    settings: {},
                    provider: 'anthropic'
                });

                expect(mockFn.mock.calls.length).toBeGreaterThan(1);
                mockFn.mock.calls.forEach((call) => {
                    expect(call[0].templates.length).toBeLessThanOrEqual(TYPE_BATCH_CEILING);
                    expect(call[0].mode).toBe('all');
                });
            });

            it('should merge and dedupe issues collected across batches', async () => {
                const mockFn = jest.fn()
                    .mockResolvedValueOnce({
                        issues: [{
                            severity: 'warning',
                            title: 'Likely duplicate vulnerability',
                            vulnerabilityId: 'vuln-0',
                            templateTitle: 'Template 0',
                            relatedTemplates: [{ vulnerabilityId: 'vuln-1', title: 'Template 1' }]
                        }],
                        summary: 'first batch summary',
                        model: 'test-model'
                    })
                    .mockResolvedValueOnce({ issues: [], summary: '', model: 'test-model' })
                    .mockResolvedValueOnce({ issues: [], summary: '', model: 'test-model' });

                const result = await runAiDuplicateChecksWithMockedProvider(mockFn, {
                    vulnerabilities: buildLargeCatalog(90),
                    locale: 'en',
                    settings: {},
                    provider: 'anthropic'
                });

                expect(result.issues).toHaveLength(1);
                expect(result.summary).toBe('first batch summary');
            });

            it('should batch a single-target run without overlap between candidate batches', async () => {
                const mockFn = jest.fn().mockResolvedValue({ issues: [], summary: '', model: 'test-model' });

                await runAiDuplicateChecksWithMockedProvider(mockFn, {
                    vulnerabilities: buildLargeCatalog(90),
                    locale: 'en',
                    targetVulnerabilityId: 'vuln-0',
                    settings: {},
                    provider: 'anthropic'
                });

                const totalCandidates = mockFn.mock.calls
                    .reduce((sum, call) => sum + call[0].templates.length, 0);
                expect(totalCandidates).toBe(89);
                mockFn.mock.calls.forEach((call) => {
                    expect(call[0].mode).toBe('single');
                    expect(call[0].target.vulnerabilityId).toBe('vuln-0');
                });
            });
        });
    });
};
