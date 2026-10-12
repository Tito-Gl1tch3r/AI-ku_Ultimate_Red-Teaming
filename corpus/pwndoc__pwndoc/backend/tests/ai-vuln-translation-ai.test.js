const {
    buildUnlinkedTranslationCatalog,
    normalizeAiUnlinkedTranslationIssues
} = require('../src/lib/ai-vuln-translation-ai');

const buildLargeSingleLocaleCatalog = (count) => {
    return Array.from({ length: count }, (_, i) => ({
        _id: `vuln-${i}`,
        details: [{
            locale: i % 2 === 0 ? 'en' : 'fr',
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
// mock to a fresh copy of ai-vuln-translation-ai.js, required and used entirely inside the callback.
const runAiUnlinkedTranslationChecksWithMockedProvider = (mockFn, args) => {
    let runAiUnlinkedTranslationChecks;
    jest.isolateModules(() => {
        jest.doMock('../src/lib/ai-client', () => ({
            runVulnerabilityUnlinkedTranslationQaWithProvider: mockFn
        }));
        ({ runAiUnlinkedTranslationChecks } = require('../src/lib/ai-vuln-translation-ai'));
    });
    return runAiUnlinkedTranslationChecks(args);
};

module.exports = function() {
    describe('AI vulnerability unlinked translation detection', () => {
        const vulnerabilities = [
            {
                _id: 'vuln-en',
                details: [{
                    locale: 'en',
                    title: 'Missing HTTPOnly Cookie Flag',
                    vulnType: 'Web Application',
                    description: '<p>Cookie without HTTPOnly.</p>',
                    observation: '<p>Observed on login.</p>',
                    remediation: '<p>Set HTTPOnly flag.</p>'
                }]
            },
            {
                _id: 'vuln-fr',
                details: [{
                    locale: 'fr',
                    title: 'Cookie sans attribut HTTPOnly',
                    vulnType: 'Application Web',
                    description: '<p>Cookie sans HTTPOnly.</p>',
                    observation: '<p>Observe sur la connexion.</p>',
                    remediation: '<p>Definir le flag HTTPOnly.</p>'
                }]
            },
            {
                _id: 'vuln-both',
                details: [
                    {
                        locale: 'en',
                        title: 'Already linked template',
                        description: '<p>English</p>'
                    },
                    {
                        locale: 'fr',
                        title: 'Modele deja lie',
                        description: '<p>Francais</p>'
                    }
                ]
            }
        ];

        it('should only include single-locale templates in the catalog', () => {
            const catalog = buildUnlinkedTranslationCatalog(vulnerabilities);
            expect(catalog).toHaveLength(2);
            expect(catalog.map((entry) => entry.vulnerabilityId).sort()).toEqual(['vuln-en', 'vuln-fr']);
        });

        it('should normalize AI unlinked translation issues with related templates', () => {
            const catalog = buildUnlinkedTranslationCatalog(vulnerabilities);
            const catalogById = new Map(catalog.map((entry) => [entry.vulnerabilityId, entry]));

            const issues = normalizeAiUnlinkedTranslationIssues([
                {
                    severity: 'warning',
                    title: 'Unlinked translation',
                    vulnerabilityId: 'vuln-en',
                    templateTitle: 'Missing HTTPOnly Cookie Flag',
                    locale: 'en',
                    relatedTemplates: [{
                        vulnerabilityId: 'vuln-fr',
                        title: 'Cookie sans attribut HTTPOnly',
                        locale: 'fr',
                        reason: 'Both describe the same cookie hardening issue.'
                    }]
                }
            ], {
                catalogById: catalogById
            });

            expect(issues).toHaveLength(1);
            expect(issues[0].category).toBe('aiUnlinkedTranslations');
            expect(issues[0].message).toContain('Cookie sans attribut HTTPOnly');
            expect(issues[0].message).toContain('separate records');
        });

        it('should filter AI unlinked translation issues to a target vulnerability', () => {
            const catalog = buildUnlinkedTranslationCatalog(vulnerabilities);
            const catalogById = new Map(catalog.map((entry) => [entry.vulnerabilityId, entry]));

            const issues = normalizeAiUnlinkedTranslationIssues([
                {
                    severity: 'warning',
                    title: 'Unlinked translation',
                    vulnerabilityId: 'vuln-en',
                    templateTitle: 'Missing HTTPOnly Cookie Flag',
                    relatedTemplates: [{
                        vulnerabilityId: 'vuln-fr',
                        title: 'Cookie sans attribut HTTPOnly'
                    }]
                }
            ], {
                targetVulnerabilityId: 'vuln-fr',
                catalogById: catalogById
            });

            expect(issues).toHaveLength(1);
            expect(issues[0].location).toContain('Cookie sans attribut HTTPOnly');
        });

        describe('batching large catalogs', () => {
            it('should skip a large "all templates" catalog instead of making multiple provider requests', async () => {
                const mockFn = jest.fn().mockResolvedValue({ issues: [], summary: '', model: 'test-model' });

                await expect(runAiUnlinkedTranslationChecksWithMockedProvider(mockFn, {
                    vulnerabilities: buildLargeSingleLocaleCatalog(90),
                    settings: {},
                    provider: 'anthropic'
                })).rejects.toThrow('skipped above 75');

                expect(mockFn).not.toHaveBeenCalled();
            });

            it('should send a catalog within the pulled ceiling in one provider request', async () => {
                const mockFn = jest.fn().mockResolvedValue({
                    issues: [],
                    summary: 'catalog summary',
                    model: 'test-model'
                });

                const result = await runAiUnlinkedTranslationChecksWithMockedProvider(mockFn, {
                    vulnerabilities: buildLargeSingleLocaleCatalog(70),
                    settings: {},
                    provider: 'anthropic'
                });

                expect(mockFn).toHaveBeenCalledTimes(1);
                expect(mockFn.mock.calls[0][0].templates).toHaveLength(70);
                expect(mockFn.mock.calls[0][0].mode).toBe('all');
                expect(result.summary).toBe('catalog summary');
            });
        });
    });
};
