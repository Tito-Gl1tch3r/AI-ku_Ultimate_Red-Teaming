const {
    runDuplicateChecks,
    runVulnerabilityStructuralChecks,
    getVulnerabilityDetail,
    formatVulnerabilityLocation,
    normalizeVulnerabilityAiIssueLocation,
    buildVulnerabilitySnapshot,
    buildQaTargets
} = require('../src/lib/ai-vuln-qa');
const mongoose = require('mongoose');

module.exports = function() {
    describe('AI vulnerability QA', () => {
        const sampleVulnerabilities = [
            {
                _id: 'vuln-1',
                status: 0,
                category: 'Web',
                details: [{
                    locale: 'en',
                    title: 'SQL Injection',
                    description: '<p>SQLi in login form.</p>',
                    observation: '<p>Observed during testing.</p>',
                    remediation: '<p>Use parameterized queries.</p>',
                    references: ['https://example.com/a', 'https://example.com/shared']
                }]
            },
            {
                _id: 'vuln-2',
                status: 1,
                details: [{
                    locale: 'en',
                    title: 'sql injection',
                    description: '<p>Different content.</p>',
                    observation: '<p>Other observation.</p>',
                    remediation: '<p>Other remediation.</p>',
                    references: ['https://example.com/shared']
                }]
            },
            {
                _id: 'vuln-3',
                status: 0,
                details: [{
                    locale: 'en',
                    title: 'Stored XSS',
                    description: '<p>SQLi in login form.</p>',
                    observation: '<p>Observed during testing.</p>',
                    remediation: '<p>Use parameterized queries.</p>',
                    references: ['https://example.com/b']
                }]
            }
        ];

        it('should format vulnerability locations', () => {
            expect(formatVulnerabilityLocation('SQL Injection')).toBe('vulnerability:SQL Injection');
            expect(formatVulnerabilityLocation('SQL Injection', 'description'))
                .toBe('vulnerability:SQL Injection/description');
        });

        it('should resolve a generic custom-field issue location to the field label', () => {
            const location = normalizeVulnerabilityAiIssueLocation({
                title: 'Placeholder content in custom field',
                message: "The 'Aggravating Factors' custom field contains placeholder content.",
                location: 'vulnerability:Missing HSTS/customFields'
            }, {
                title: 'Missing HSTS'
            }, {
                finding: {
                    customFields: [
                        { label: 'Exploitation Info', fieldType: 'text', content: 'Details' },
                        { label: 'Aggravating Factors', fieldType: 'text', content: 'N/A' }
                    ]
                }
            });

            expect(location).toBe('vulnerability:Missing HSTS/custom-field:Aggravating Factors');
        });

        it('should resolve vulnerability detail for locale', () => {
            const detail = getVulnerabilityDetail(sampleVulnerabilities[0], 'en');
            expect(detail.title).toBe('SQL Injection');
        });

        it('should omit workflow status from template QA snapshots', () => {
            const snapshot = buildVulnerabilitySnapshot({
                status: 0,
                details: [{
                    locale: 'en',
                    title: 'Template Title',
                    description: '<p>Description</p>'
                }]
            }, {
                locale: 'en',
                title: 'Template Title',
                description: '<p>Description</p>'
            });

            expect(snapshot.type).toBe('vulnerability_template');
            expect(snapshot.status).toBeUndefined();
        });

        it('should flag duplicate titles and identical content', () => {
            const issues = runDuplicateChecks({
                vulnerabilities: sampleVulnerabilities,
                locale: 'en'
            });

            expect(issues.some((issue) => issue.title === 'Duplicate vulnerability title')).toBe(true);
            expect(issues.some((issue) => issue.title === 'Duplicate vulnerability content')).toBe(true);
            expect(issues.some((issue) => issue.category === 'aiDuplicates')).toBe(false);
        });

        it('should limit duplicate issues to a target vulnerability', () => {
            const issues = runDuplicateChecks({
                vulnerabilities: sampleVulnerabilities,
                locale: 'en',
                targetVulnerabilityId: 'vuln-1'
            });

            expect(issues.length).toBeGreaterThan(0);
            expect(issues.every((issue) => issue.location.includes('SQL Injection'))).toBe(true);
        });

        it('should flag missing core vulnerability fields', () => {
            const issues = runVulnerabilityStructuralChecks({
                details: [{ locale: 'en', title: 'Incomplete' }]
            }, {
                locale: 'en',
                title: 'Incomplete',
                description: '',
                observation: '',
                remediation: ''
            });

            expect(issues.some((issue) => /description/i.test(issue.title))).toBe(true);
            expect(issues.some((issue) => /remediation/i.test(issue.title))).toBe(true);
        });

        it('should attach the involved template ids to duplicate issues', () => {
            const issues = runDuplicateChecks({
                vulnerabilities: sampleVulnerabilities,
                locale: 'en'
            });

            expect(issues.length).toBeGreaterThan(0);
            issues.forEach((issue) => {
                expect(Array.isArray(issue.vulnerabilityIds)).toBe(true);
                expect(issue.vulnerabilityIds.length).toBe(2);
            });
        });

        it('should build QA targets only for templates with content in the locale', () => {
            const targets = buildQaTargets([
                ...sampleVulnerabilities,
                { _id: 'vuln-fr', details: [{ locale: 'fr', title: 'Injection SQL' }] },
                { _id: 'vuln-empty', details: [] }
            ], 'en');

            expect(targets).toHaveLength(3);
            targets.forEach((target) => {
                expect(target.detail.locale).toBe('en');
            });
        });

        it('should populate custom-field labels for single and catalog QA snapshots', async () => {
            const Vulnerability = mongoose.model('Vulnerability');
            const CustomField = mongoose.model('CustomField');
            const suffix = `${Date.now()}-${Math.random()}`;
            let customField;
            let vulnerability;

            try {
                customField = await CustomField.create({
                    fieldType: 'text',
                    label: `Aggravating Factors ${suffix}`,
                    display: 'vulnerability'
                });
                vulnerability = await new Vulnerability({
                    category: 'Web',
                    details: [{
                        locale: 'en',
                        title: `QA custom-field population ${suffix}`,
                        customFields: [{
                            customField: customField._id,
                            text: '<p>Requires additional review.</p>'
                        }]
                    }]
                }).save();

                const single = await Vulnerability.getByIdForQa(vulnerability._id);
                const catalog = await Vulnerability.getAllForQa();
                const catalogEntry = catalog.find((entry) => String(entry._id) === String(vulnerability._id));
                const singleSnapshot = buildVulnerabilitySnapshot(single, single.details[0]);
                const catalogSnapshot = buildVulnerabilitySnapshot(catalogEntry, catalogEntry.details[0]);

                expect(singleSnapshot.finding.customFields[0]).toMatchObject({
                    label: customField.label,
                    fieldType: 'text'
                });
                expect(catalogSnapshot.finding.customFields[0]).toMatchObject({
                    label: customField.label,
                    fieldType: 'text'
                });
            } finally {
                if (vulnerability)
                    await Vulnerability.deleteOne({ _id: vulnerability._id });
                if (customField)
                    await CustomField.deleteOne({ _id: customField._id });
            }
        });
    });
};
