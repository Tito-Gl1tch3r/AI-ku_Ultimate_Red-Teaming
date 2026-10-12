const {
    runStructuralChecks,
    buildAuditSnapshot,
    isEmptyContent,
    runAuditQa
} = require('../src/lib/ai-qa');

module.exports = function() {
    describe('AI audit QA', () => {
        it('should detect empty HTML content', () => {
            expect(isEmptyContent('<p></p>')).toBe(true);
            expect(isEmptyContent('<p>Hello</p>')).toBe(false);
        });

        it('should flag missing audit name and findings', () => {
            const issues = runStructuralChecks({
                findings: [],
                sections: []
            });

            expect(issues.some((issue) => issue.title === 'Missing audit name')).toBe(true);
            expect(issues.some((issue) => issue.title === 'No findings')).toBe(true);
        });

        it('should not flag optional report fields from organization settings', () => {
            const issues = runStructuralChecks({
                name: 'Web App Pentest',
                findings: [{
                    identifier: 1,
                    title: 'SQL Injection'
                }],
                sections: [{
                    name: 'Executive Summary',
                    text: ''
                }]
            });

            expect(issues.some((issue) => issue.title === 'Missing company')).toBe(false);
            expect(issues.some((issue) => issue.title === 'Missing description')).toBe(false);
            expect(issues.some((issue) => issue.title === 'Empty section')).toBe(false);
        });

        it('should flag findings missing a title', () => {
            const issues = runStructuralChecks({
                name: 'Web App Pentest',
                findings: [{
                    identifier: 1,
                    title: ''
                }],
                sections: []
            });

            expect(issues.some((issue) => issue.title === 'Missing finding title')).toBe(true);
        });

        it('should build an audit snapshot for AI review', () => {
            const snapshot = buildAuditSnapshot({
                name: 'Web App Pentest',
                company: { name: 'Acme Corp', shortName: 'Acme' },
                client: { firstname: 'Jane', lastname: 'Doe', email: 'jane@example.com' },
                findings: [{
                    identifier: 2,
                    title: 'XSS',
                    description: '<p>Reflected XSS in search.</p>'
                }],
                sections: [{
                    name: 'Executive Summary',
                    text: '<p>Overall risk is medium.</p>'
                }]
            });

            expect(snapshot.name).toBe('Web App Pentest');
            expect(snapshot.company.name).toBe('Acme Corp');
            expect(snapshot.findings[0].location).toBe('finding:XSS');
            expect(snapshot.sections[0].text).toContain('Overall risk is medium');
        });

        it('should embed the finding id in the snapshot location when the finding has one', () => {
            const snapshot = buildAuditSnapshot({
                name: 'Web App Pentest',
                findings: [{
                    _id: '507f1f77bcf86cd799439011',
                    identifier: 2,
                    title: 'XSS',
                    description: '<p>Reflected XSS in search.</p>'
                }],
                sections: []
            });

            expect(snapshot.findings[0].location).toBe('finding:507f1f77bcf86cd799439011::XSS');
        });

        it('should attach finding ids to structural issue locations from a programmatic-only run', async () => {
            const result = await runAuditQa({
                audit: {
                    name: 'Web App Pentest',
                    findings: [{
                        _id: '507f1f77bcf86cd799439011',
                        identifier: 1,
                        title: 'SQL Injection',
                        status: 1
                    }],
                    sections: []
                },
                settings: {},
                scope: 'programmatic'
            });

            const findingIssue = result.issues.find((issue) => issue.title === 'Finding still in redaction');
            expect(findingIssue).toBeDefined();
            expect(findingIssue.location).toBe('finding:507f1f77bcf86cd799439011::SQL Injection');
        });
    });
};
