module.exports = function(request, app) {
    describe('AI integration API', () => {
        const Settings = require('mongoose').model('Settings');
        const Vulnerability = require('mongoose').model('Vulnerability');
        let adminToken = '';
        let userToken = '';
        let noAiToken = '';
        // Base QA (built-in checks) but no AI-QA and no AI-assist.
        let baseQaToken = '';
        // AI-QA only, no base QA permission (the two are disjoint).
        let aiQaOnlyToken = '';
        // QA read only (view reports) with neither generate permission.
        let qaReadOnlyToken = '';
        // Only the catalog built-in generate permission (no single-vuln qa).
        let catalogOnlyToken = '';
        // Reads the AI-integration config (redaction guidelines) but nothing else AI.
        let redactionReaderToken = '';

        const login = async (username, password) => {
            const response = await request(app).post('/api/users/token').send({ username, password });
            expect(response.status).toBe(200);
            expect(response.body.datas.token).toBeDefined();
            return response.body.datas.token;
        };

        const createRoleUser = async (role, user) => {
            let response = await request(app).post('/api/data/roles')
                .set('Cookie', [`token=JWT ${adminToken}`])
                .send(role);
            expect([201, 422]).toContain(response.status);

            response = await request(app).post('/api/users')
                .set('Cookie', [`token=JWT ${adminToken}`])
                .send({ ...user, roles: [role.name] });
            expect([201, 422]).toContain(response.status);

            return login(user.username, user.password);
        };

        beforeAll(async () => {
            adminToken = await login('admin', 'Admin123');
            userToken = await login('user2', 'User1234');

            let response = await request(app).post('/api/data/roles')
                .set('Cookie', [`token=JWT ${adminToken}`])
                .send({
                    name: 'no-ai-integration',
                    displayName: 'No AI Integration',
                    allows: ['clients:read']
                });
            expect([201, 422]).toContain(response.status);

            response = await request(app).post('/api/users')
                .set('Cookie', [`token=JWT ${adminToken}`])
                .send({
                    username: 'noaiuser',
                    password: 'Noai1234',
                    firstname: 'No',
                    lastname: 'Ai',
                    roles: ['no-ai-integration']
                });
            expect([201, 422]).toContain(response.status);

            noAiToken = await login('noaiuser', 'Noai1234');

            baseQaToken = await createRoleUser(
                {
                    name: 'base-qa-only',
                    displayName: 'Base QA Only',
                    allows: ['audits:read', 'audits:qa', 'vulnerabilities:read', 'vulnerabilities:qa', 'vulnerabilities:qa-catalog']
                },
                { username: 'baseqauser', password: 'Baseqa1234', firstname: 'Base', lastname: 'Qa' }
            );

            aiQaOnlyToken = await createRoleUser(
                {
                    name: 'ai-qa-only',
                    displayName: 'AI QA Only',
                    allows: ['audits:read', 'audits:ai-qa', 'vulnerabilities:read', 'vulnerabilities:ai-qa', 'vulnerabilities:ai-qa-catalog']
                },
                { username: 'aiqauser', password: 'Aiqa1234', firstname: 'Ai', lastname: 'Qa' }
            );

            qaReadOnlyToken = await createRoleUser(
                {
                    name: 'qa-read-only',
                    displayName: 'QA Read Only',
                    allows: ['audits:read', 'audits:qa-read', 'vulnerabilities:read', 'vulnerabilities:qa-read', 'vulnerabilities:qa-read-catalog']
                },
                { username: 'qareaduser', password: 'Qaread1234', firstname: 'Qa', lastname: 'Read' }
            );

            catalogOnlyToken = await createRoleUser(
                {
                    name: 'qa-catalog-only',
                    displayName: 'QA Catalog Only',
                    allows: ['vulnerabilities:read', 'vulnerabilities:qa-catalog']
                },
                { username: 'qacatuser', password: 'Qacat1234', firstname: 'Qa', lastname: 'Cat' }
            );

            redactionReaderToken = await createRoleUser(
                {
                    name: 'redaction-reader',
                    displayName: 'Redaction Reader',
                    allows: ['audits:read', 'audits:ai-assist', 'ai:redaction-guidelines:read']
                },
                { username: 'redactionreader', password: 'Redact1234', firstname: 'Redaction', lastname: 'Reader' }
            );

            await Settings.findOneAndUpdate({}, {
                $set: {
                    'ai.public.enabled': true,
                    'ai.public.redactionGuidelines.content': 'Secret redaction policy',
                    'ai.public.qaInstructions.content': 'Secret QA checklist',
                    'ai.public.qaChecks.redaction': false
                }
            }, { upsert: true });
        });

        beforeEach(async () => {
            await Settings.findOneAndUpdate({}, {
                $set: {
                    'ai.public.enabled': true,
                    'ai.public.redactionGuidelines.content': 'Secret redaction policy',
                    'ai.public.qaInstructions.content': 'Secret QA checklist',
                    'ai.public.qaChecks.redaction': false
                }
            }, { upsert: true });
        });

        it('should omit admin-only AI config from public settings', async () => {
            const response = await request(app).get('/api/settings/public')
                .set('Cookie', [`token=JWT ${userToken}`]);

            expect(response.status).toBe(200);
            // Provider names (defaultProvider/allowedProviders) are public so the chat/QA
            // selector can be populated; admin-only config and secrets stay hidden.
            expect(response.body.datas.ai.public).toEqual({
                enabled: true,
                defaultProvider: 'openai',
                allowedProviders: [],
                providerModels: expect.objectContaining({
                    openai: expect.any(String),
                    anthropic: expect.any(String)
                }),
                qaChecks: expect.objectContaining({
                    redaction: false,
                    aiDuplicates: true,
                    aiUnlinkedTranslations: true
                }),
                globalPrompts: []
            });
            expect(response.body.datas.ai.public).not.toHaveProperty('redactionGuidelines');
            expect(response.body.datas.ai.public).not.toHaveProperty('qaInstructions');
            expect(response.body.datas.ai).not.toHaveProperty('private');
        });

        it('should deny AI integration config to users without ai read permissions', async () => {
            const response = await request(app).get('/api/data/ai-integration')
                .set('Cookie', [`token=JWT ${noAiToken}`]);

            expect(response.status).toBe(403);
        });

        it('should deny AI integration config to a standard user without any ai:* read permission', async () => {
            // AI permissions are non-core, so the plain user role has no ai:*:read grant.
            const response = await request(app).get('/api/data/ai-integration')
                .set('Cookie', [`token=JWT ${userToken}`]);

            expect(response.status).toBe(403);
        });

        it('should return redaction guidelines to users with the redaction-guidelines read permission', async () => {
            const response = await request(app).get('/api/data/ai-integration')
                .set('Cookie', [`token=JWT ${redactionReaderToken}`]);

            expect(response.status).toBe(200);
            expect(response.body.datas.redactionGuidelines.content).toBe('Secret redaction policy');
            expect(response.body.datas.promptMappings).toBeUndefined();
            expect(response.body.datas.qaInstructions).toBeUndefined();
            expect(response.body.datas.qaChecks).toBeUndefined();
        });

        it('should return enabled field prompts for users with ai-assist permission', async () => {
            const response = await request(app).get('/api/ai/enabled-fields?entityType=finding')
                .set('Cookie', [`token=JWT ${redactionReaderToken}`]);

            expect(response.status).toBe(200);
            expect(Array.isArray(response.body.datas.fields)).toBe(true);
            expect(response.body.datas.fields.some((field) => field.fieldKey === 'description')).toBe(true);
            expect(response.body.datas.fields[0]).toHaveProperty('prompt');
            expect(response.body.datas.redactionGuidelines).toBeUndefined();
            expect(response.body.datas.promptMappings).toBeUndefined();
        });

        it('should deny the AI generation endpoints without an ai-assist permission', async () => {
            let response = await request(app).get('/api/ai/enabled-fields?entityType=finding')
                .set('Cookie', [`token=JWT ${noAiToken}`]);
            expect(response.status).toBe(403);

            response = await request(app).post('/api/ai/generate')
                .set('Cookie', [`token=JWT ${noAiToken}`])
                .send({ entityType: 'finding', fieldKey: 'description', context: {} });
            expect(response.status).toBe(403);

            // Base QA must not imply AI-assist.
            response = await request(app).post('/api/ai/generate')
                .set('Cookie', [`token=JWT ${baseQaToken}`])
                .send({ entityType: 'finding', fieldKey: 'description', context: {} });
            expect(response.status).toBe(403);
        });

        it('should enforce the three update scopes on the AI integration config independently', async () => {
            // redactionReaderToken has a read scope but no update scope: every branch must reject.
            const rejected = [
                { globalPrompts: [] },
                { promptMappings: [] },
                { redactionGuidelines: { content: 'attacker policy' } },
                { qaInstructions: { content: 'attacker checklist' } },
                { qaChecks: { completeness: false } }
            ];

            for (const payload of rejected) {
                const response = await request(app).put('/api/data/ai-integration')
                    .set('Cookie', [`token=JWT ${redactionReaderToken}`])
                    .send(payload);
                expect(response.status).toBe(403);
            }

            const check = await request(app).get('/api/data/ai-integration')
                .set('Cookie', [`token=JWT ${adminToken}`]);
            expect(check.body.datas.redactionGuidelines.content).toBe('Secret redaction policy');
            expect(check.body.datas.qaInstructions.content).toBe('Secret QA checklist');
        });

        it('should reject an AI integration update with no recognised payload', async () => {
            const response = await request(app).put('/api/data/ai-integration')
                .set('Cookie', [`token=JWT ${adminToken}`])
                .send({ unrelated: true });

            expect(response.status).toBe(422);
        });

        it('should return full AI integration config for settings admins', async () => {
            const response = await request(app).get('/api/data/ai-integration')
                .set('Cookie', [`token=JWT ${adminToken}`]);

            expect(response.status).toBe(200);
            expect(response.body.datas.redactionGuidelines.content).toBe('Secret redaction policy');
            expect(response.body.datas.qaInstructions.content).toBe('Secret QA checklist');
            expect(response.body.datas.qaChecks.redaction).toBe(false);
            expect(Array.isArray(response.body.datas.globalPrompts)).toBe(true);
        });

        it('should save and return global prompts for prompt admins', async () => {
            const globalPrompts = [{
                id: 'spellcheck',
                label: 'Spellcheck my document',
                prompt: 'Review the content for spelling and grammar issues.',
                enabled: true
            }, {
                id: 'translate-fr',
                label: 'Translate to french',
                prompt: 'Translate the content to French while preserving technical terms.',
                enabled: false
            }];

            let response = await request(app).put('/api/data/ai-integration')
                .set('Cookie', [`token=JWT ${adminToken}`])
                .send({ globalPrompts });

            expect(response.status).toBe(200);
            expect(response.body.datas.globalPrompts).toEqual(globalPrompts);

            response = await request(app).get('/api/data/ai-integration')
                .set('Cookie', [`token=JWT ${adminToken}`]);

            expect(response.status).toBe(200);
            expect(response.body.datas.globalPrompts).toEqual(globalPrompts);
        });

        it('should run QA on a draft vulnerability template', async () => {
            await Settings.findOneAndUpdate({}, {
                $set: {
                    'ai.public.enabled': true,
                    'ai.public.qaChecks': {
                        completeness: true,
                        references: false,
                        imageCaptions: false,
                        duplicates: false,
                        aiDuplicates: false,
                        redaction: false,
                        customer: false,
                        instructions: false
                    }
                }
            }, { upsert: true });

            const response = await request(app).post('/api/ai/vulnerabilities/qa')
                .set('Cookie', [`token=JWT ${adminToken}`])
                .send({
                    locale: 'en',
                    scope: 'all',
                    vulnerability: {
                        category: 'Web',
                        details: [{
                            locale: 'en',
                            title: 'Draft Template',
                            description: '',
                            observation: '',
                            remediation: ''
                        }]
                    }
                });

            expect(response.status).toBe(200);
            expect(response.body.datas.mode).toBe('single');
            expect(response.body.datas.cached).toBe(false);
            expect(Array.isArray(response.body.datas.issues)).toBe(true);
            expect(response.body.datas.issues.length).toBeGreaterThan(0);
        });

        it('should reject catalog-wide runs on the single-vulnerability endpoint', async () => {
            // The old chunked contract (scope without vulnerabilityId/draft) is gone;
            // catalog-wide runs go through the background job endpoints.
            const response = await request(app).post('/api/ai/vulnerabilities/qa')
                .set('Cookie', [`token=JWT ${adminToken}`])
                .send({
                    locale: 'en',
                    scope: 'all'
                });

            expect(response.status).toBe(422);
        });

        it('should still run programmatic-only QA checks when AI integration is disabled', async () => {
            await Settings.findOneAndUpdate({}, {
                $set: {
                    'ai.public.enabled': false,
                    'ai.public.qaChecks': {
                        completeness: true,
                        references: false,
                        imageCaptions: false,
                        duplicates: false,
                        aiDuplicates: false,
                        aiUnlinkedTranslations: false,
                        redaction: false,
                        customer: false,
                        instructions: false
                    }
                }
            }, { upsert: true });

            const draftVulnerability = {
                category: 'Web',
                details: [{
                    locale: 'en',
                    title: 'AI Disabled Draft Template',
                    description: '',
                    observation: '',
                    remediation: ''
                }]
            };

            const loadResponse = await request(app).post('/api/ai/vulnerabilities/qa')
                .set('Cookie', [`token=JWT ${adminToken}`])
                .send({ locale: 'en', loadOnly: true, vulnerability: draftVulnerability });
            expect(loadResponse.status).toBe(200);

            const programmaticResponse = await request(app).post('/api/ai/vulnerabilities/qa')
                .set('Cookie', [`token=JWT ${adminToken}`])
                .send({ locale: 'en', scope: 'programmatic', vulnerability: draftVulnerability });
            expect(programmaticResponse.status).toBe(200);
            expect(programmaticResponse.body.datas.mode).toBe('single');
            expect(Array.isArray(programmaticResponse.body.datas.issues)).toBe(true);
            expect(programmaticResponse.body.datas.issues.length).toBeGreaterThan(0);

            const aiResponse = await request(app).post('/api/ai/vulnerabilities/qa')
                .set('Cookie', [`token=JWT ${adminToken}`])
                .send({ locale: 'en', scope: 'ai', vulnerability: draftVulnerability });
            expect(aiResponse.status).toBe(403);

            const allResponse = await request(app).post('/api/ai/vulnerabilities/qa')
                .set('Cookie', [`token=JWT ${adminToken}`])
                .send({ locale: 'en', scope: 'all', vulnerability: draftVulnerability });
            expect(allResponse.status).toBe(403);
        });

        const setProgrammaticOnlyChecks = () => Settings.findOneAndUpdate({}, {
            $set: {
                'ai.public.enabled': true,
                'ai.public.qaChecks': {
                    completeness: true,
                    references: false,
                    imageCaptions: false,
                    duplicates: true,
                    aiDuplicates: false,
                    aiUnlinkedTranslations: false,
                    redaction: false,
                    customer: false,
                    instructions: false
                }
            }
        }, { upsert: true });

        const waitForQaJob = async (locale) => {
            for (let attempt = 0; attempt < 100; attempt++) {
                const response = await request(app).get(`/api/ai/vulnerabilities/qa/status?locale=${locale}`)
                    .set('Cookie', [`token=JWT ${adminToken}`]);
                expect(response.status).toBe(200);
                const job = response.body.datas.job;
                if (job && ['done', 'failed', 'cancelled'].includes(job.state))
                    return response.body.datas;
                await new Promise((resolve) => setTimeout(resolve, 100));
            }
            throw new Error('QA job did not finish in time');
        };

        it('should run catalog-wide QA as a background job and assemble the report from per-template results', async () => {
            await setProgrammaticOnlyChecks();

            await request(app).post('/api/vulnerabilities')
                .set('Cookie', [`token=JWT ${adminToken}`])
                .send([{
                    category: 'Web',
                    details: [{
                        locale: 'en',
                        title: 'Job Endpoint Target',
                        vulnType: 'Web',
                        description: '<p>content</p>',
                        observation: '',
                        remediation: ''
                    }]
                }]);

            const runResponse = await request(app).post('/api/ai/vulnerabilities/qa/run')
                .set('Cookie', [`token=JWT ${adminToken}`])
                .send({ locale: 'en', scope: 'programmatic' });

            expect(runResponse.status).toBe(200);
            expect(runResponse.body.datas.alreadyRunning).toBe(false);
            expect(runResponse.body.datas.job).toEqual(expect.objectContaining({
                locale: 'en',
                scope: 'programmatic',
                state: expect.any(String)
            }));

            const status = await waitForQaJob('en');
            expect(status.job.state).toBe('done');
            expect(status.report.hasReport).toBe(true);
            expect(status.report.mode).toBe('all');
            expect(status.report.vulnerabilityCount).toBeGreaterThan(0);
            expect(status.report.checkedCount).toBe(status.report.vulnerabilityCount);
            expect(Array.isArray(status.report.templates)).toBe(true);
            expect(status.report.templates.length).toBe(status.report.vulnerabilityCount);
            expect(status.report.templates.every((row) => row.vulnerabilityId)).toBe(true);

            // Second run over the unchanged catalog reuses every stored result.
            const rerunResponse = await request(app).post('/api/ai/vulnerabilities/qa/run')
                .set('Cookie', [`token=JWT ${adminToken}`])
                .send({ locale: 'en', scope: 'programmatic' });
            expect(rerunResponse.status).toBe(200);

            const rerunStatus = await waitForQaJob('en');
            expect(rerunStatus.job.state).toBe('done');
            expect(rerunStatus.job.reused).toBe(rerunStatus.job.total);
            expect(rerunStatus.job.processed).toBe(0);
        });

        it('should still allow a programmatic-only catalog job and status polling when AI integration is disabled', async () => {
            await setProgrammaticOnlyChecks();
            await Settings.findOneAndUpdate({}, { $set: { 'ai.public.enabled': false } });

            const statusBefore = await request(app).get('/api/ai/vulnerabilities/qa/status?locale=en')
                .set('Cookie', [`token=JWT ${adminToken}`]);
            expect(statusBefore.status).toBe(200);

            const aiRunResponse = await request(app).post('/api/ai/vulnerabilities/qa/run')
                .set('Cookie', [`token=JWT ${adminToken}`])
                .send({ locale: 'en', scope: 'all' });
            expect(aiRunResponse.status).toBe(403);

            const runResponse = await request(app).post('/api/ai/vulnerabilities/qa/run')
                .set('Cookie', [`token=JWT ${adminToken}`])
                .send({ locale: 'en', scope: 'programmatic' });
            expect(runResponse.status).toBe(200);

            const status = await waitForQaJob('en');
            expect(status.job.state).toBe('done');
            expect(status.report.hasReport).toBe(true);
        });

        it('should deny the QA job endpoints without any catalog QA permission', async () => {
            let response = await request(app).post('/api/ai/vulnerabilities/qa/run')
                .set('Cookie', [`token=JWT ${noAiToken}`])
                .send({ locale: 'en', scope: 'programmatic' });
            expect(response.status).toBe(403);

            response = await request(app).get('/api/ai/vulnerabilities/qa/status?locale=en')
                .set('Cookie', [`token=JWT ${noAiToken}`]);
            expect(response.status).toBe(403);

            response = await request(app).post('/api/ai/vulnerabilities/qa/cancel')
                .set('Cookie', [`token=JWT ${noAiToken}`])
                .send({ locale: 'en' });
            expect(response.status).toBe(403);
        });

        describe('QA permission scoping (base QA vs AI-QA)', () => {
            const draftVulnerability = () => ({
                category: 'Web',
                details: [{
                    locale: 'en',
                    title: 'Perm Matrix Draft',
                    description: '',
                    observation: '',
                    remediation: ''
                }]
            });

            it('lets a base-QA-only user run programmatic vulnerability QA but forbids AI scopes', async () => {
                const loadResponse = await request(app).post('/api/ai/vulnerabilities/qa')
                    .set('Cookie', [`token=JWT ${baseQaToken}`])
                    .send({ locale: 'en', loadOnly: true, vulnerability: draftVulnerability() });
                expect(loadResponse.status).toBe(200);

                const programmatic = await request(app).post('/api/ai/vulnerabilities/qa')
                    .set('Cookie', [`token=JWT ${baseQaToken}`])
                    .send({ locale: 'en', scope: 'programmatic', vulnerability: draftVulnerability() });
                expect(programmatic.status).toBe(200);

                const ai = await request(app).post('/api/ai/vulnerabilities/qa')
                    .set('Cookie', [`token=JWT ${baseQaToken}`])
                    .send({ locale: 'en', scope: 'ai', vulnerability: draftVulnerability() });
                expect(ai.status).toBe(403);

                const all = await request(app).post('/api/ai/vulnerabilities/qa')
                    .set('Cookie', [`token=JWT ${baseQaToken}`])
                    .send({ locale: 'en', scope: 'all', vulnerability: draftVulnerability() });
                expect(all.status).toBe(403);
            });

            it('forbids an AI-QA-only user from running the programmatic scope (disjoint from qa)', async () => {
                // ai-qa does NOT imply qa: running built-in checks requires the base permission.
                const programmatic = await request(app).post('/api/ai/vulnerabilities/qa')
                    .set('Cookie', [`token=JWT ${aiQaOnlyToken}`])
                    .send({ locale: 'en', scope: 'programmatic', vulnerability: draftVulnerability() });
                expect(programmatic.status).toBe(403);

                // But reading a cached report (loadOnly) is allowed for any QA-permission holder,
                // so a panel that opened never 403s on its initial load.
                const loadOnly = await request(app).post('/api/ai/vulnerabilities/qa')
                    .set('Cookie', [`token=JWT ${aiQaOnlyToken}`])
                    .send({ locale: 'en', loadOnly: true, vulnerability: draftVulnerability() });
                expect(loadOnly.status).toBe(200);

                // Disable the AI checks (keeping AI integration enabled) so the AI scope passes
                // the permission + provider gate without making a real provider call.
                await Settings.findOneAndUpdate({}, {
                    $set: {
                        'ai.public.enabled': true,
                        'ai.public.qaChecks': {
                            completeness: true,
                            references: false,
                            imageCaptions: false,
                            duplicates: false,
                            aiDuplicates: false,
                            aiUnlinkedTranslations: false,
                            redaction: false,
                            customer: false,
                            instructions: false
                        }
                    }
                }, { upsert: true });

                const ai = await request(app).post('/api/ai/vulnerabilities/qa')
                    .set('Cookie', [`token=JWT ${aiQaOnlyToken}`])
                    .send({ locale: 'en', scope: 'ai', vulnerability: draftVulnerability() });
                // Passes the permission gate (never 403); no AI check enabled means no LLM call.
                expect(ai.status).not.toBe(403);
            });

            it('scopes the audit QA endpoint: base runs built-in only, ai-qa runs AI only', async () => {
                // Middleware rejects before the handler touches the audit, so a non-existent
                // auditId still exercises the permission gate.
                const baseAiScope = await request(app).post('/api/ai/qa')
                    .set('Cookie', [`token=JWT ${baseQaToken}`])
                    .send({ auditId: 'deadbeefdeadbeefdeadbeef', scope: 'ai' });
                expect(baseAiScope.status).toBe(403);

                // ai-qa does not imply qa, so the programmatic scope is forbidden.
                const aiOnlyProgrammatic = await request(app).post('/api/ai/qa')
                    .set('Cookie', [`token=JWT ${aiQaOnlyToken}`])
                    .send({ auditId: 'deadbeefdeadbeefdeadbeef', scope: 'programmatic' });
                expect(aiOnlyProgrammatic.status).toBe(403);

                // Reading a cached audit report is allowed for either QA permission holder.
                const baseLoad = await request(app).post('/api/ai/qa')
                    .set('Cookie', [`token=JWT ${aiQaOnlyToken}`])
                    .send({ auditId: 'deadbeefdeadbeefdeadbeef', loadOnly: true });
                expect(baseLoad.status).not.toBe(403);
            });

            it('scopes the catalog-wide QA job endpoint on the catalog QA permissions', async () => {
                // qa-catalog can start a programmatic job but not an AI one.
                const aiJob = await request(app).post('/api/ai/vulnerabilities/qa/run')
                    .set('Cookie', [`token=JWT ${baseQaToken}`])
                    .send({ locale: 'en', scope: 'ai' });
                expect(aiJob.status).toBe(403);

                // ai-qa-catalog does NOT imply qa-catalog, so it cannot start a programmatic-only job.
                const programmaticJob = await request(app).post('/api/ai/vulnerabilities/qa/run')
                    .set('Cookie', [`token=JWT ${aiQaOnlyToken}`])
                    .send({ locale: 'en', scope: 'programmatic' });
                expect(programmaticJob.status).toBe(403);

                // Managing the stored catalog report (status) needs any catalog QA permission.
                const status = await request(app).get('/api/ai/vulnerabilities/qa/status?locale=en')
                    .set('Cookie', [`token=JWT ${baseQaToken}`]);
                expect(status.status).toBe(200);

                // ai-qa-catalog also grants read access to the stored report.
                const statusAi = await request(app).get('/api/ai/vulnerabilities/qa/status?locale=en')
                    .set('Cookie', [`token=JWT ${aiQaOnlyToken}`]);
                expect(statusAi.status).toBe(200);

                // A user with no catalog QA permission at all is denied.
                const statusDenied = await request(app).get('/api/ai/vulnerabilities/qa/status?locale=en')
                    .set('Cookie', [`token=JWT ${noAiToken}`]);
                expect(statusDenied.status).toBe(403);
            });

            it('does NOT let the catalog QA permission run single-vulnerability QA', async () => {
                // Regression: catalog permissions must unlock only the catalog feature. The
                // ACL treats `X-all` as a superset of `X`, so catalog perms deliberately use a
                // `-catalog` suffix (not `-all`) to stay independent of the single-vuln perms.
                const single = await request(app).post('/api/ai/vulnerabilities/qa')
                    .set('Cookie', [`token=JWT ${catalogOnlyToken}`])
                    .send({ locale: 'en', scope: 'programmatic', vulnerability: draftVulnerability() });
                expect(single.status).toBe(403);

                // ...but it can start the catalog-wide job.
                const catalogJob = await request(app).post('/api/ai/vulnerabilities/qa/run')
                    .set('Cookie', [`token=JWT ${catalogOnlyToken}`])
                    .send({ locale: 'en', scope: 'programmatic' });
                expect(catalogJob.status).not.toBe(403);
            });

            it('lets a QA-read-only user view reports but not run or mutate them', async () => {
                // Reading a cached single-vuln report is allowed.
                const loadOnly = await request(app).post('/api/ai/vulnerabilities/qa')
                    .set('Cookie', [`token=JWT ${qaReadOnlyToken}`])
                    .send({ locale: 'en', loadOnly: true, vulnerability: draftVulnerability() });
                expect(loadOnly.status).toBe(200);

                // Reading the catalog status is allowed.
                const status = await request(app).get('/api/ai/vulnerabilities/qa/status?locale=en')
                    .set('Cookie', [`token=JWT ${qaReadOnlyToken}`]);
                expect(status.status).toBe(200);

                // Running any scope is forbidden (read is not a generate permission).
                for (const scope of ['programmatic', 'ai', 'all']) {
                    const run = await request(app).post('/api/ai/vulnerabilities/qa')
                        .set('Cookie', [`token=JWT ${qaReadOnlyToken}`])
                        .send({ locale: 'en', scope, vulnerability: draftVulnerability() });
                    expect(run.status).toBe(403);
                }

                // Starting a catalog job is forbidden.
                const job = await request(app).post('/api/ai/vulnerabilities/qa/run')
                    .set('Cookie', [`token=JWT ${qaReadOnlyToken}`])
                    .send({ locale: 'en', scope: 'programmatic' });
                expect(job.status).toBe(403);

                // Mutating the report (cancel/dismiss/resolve) is forbidden — read is view-only.
                const cancel = await request(app).post('/api/ai/vulnerabilities/qa/cancel')
                    .set('Cookie', [`token=JWT ${qaReadOnlyToken}`])
                    .send({ locale: 'en' });
                expect(cancel.status).toBe(403);

                const dismiss = await request(app).post('/api/ai/vulnerabilities/qa/dismiss')
                    .set('Cookie', [`token=JWT ${qaReadOnlyToken}`])
                    .send({ locale: 'en', key: 'whatever', dismissed: true });
                expect(dismiss.status).toBe(403);

                const resolve = await request(app).post('/api/ai/vulnerabilities/qa/resolve')
                    .set('Cookie', [`token=JWT ${qaReadOnlyToken}`])
                    .send({ locale: 'en', vulnerabilityId: 'deadbeefdeadbeefdeadbeef', resolved: true });
                expect(resolve.status).toBe(403);
            });

            it('lets a QA-read-only user view the audit QA report but not run it', async () => {
                const loadOnly = await request(app).post('/api/ai/qa')
                    .set('Cookie', [`token=JWT ${qaReadOnlyToken}`])
                    .send({ auditId: 'deadbeefdeadbeefdeadbeef', loadOnly: true });
                expect(loadOnly.status).not.toBe(403);

                const run = await request(app).post('/api/ai/qa')
                    .set('Cookie', [`token=JWT ${qaReadOnlyToken}`])
                    .send({ auditId: 'deadbeefdeadbeefdeadbeef', scope: 'programmatic' });
                expect(run.status).toBe(403);
            });
        });

        it('should dismiss and restore QA issues from the assembled report', async () => {
            await setProgrammaticOnlyChecks();

            await request(app).post('/api/vulnerabilities')
                .set('Cookie', [`token=JWT ${adminToken}`])
                .send([{
                    category: 'Web',
                    details: [{
                        locale: 'en',
                        title: 'Dismiss Endpoint Target',
                        vulnType: 'Web',
                        description: '<p>content</p>',
                        observation: '',
                        remediation: ''
                    }]
                }]);

            const runResponse = await request(app).post('/api/ai/vulnerabilities/qa/run')
                .set('Cookie', [`token=JWT ${adminToken}`])
                .send({ locale: 'en', scope: 'programmatic' });
            expect(runResponse.status).toBe(200);

            const status = await waitForQaJob('en');
            const row = status.report.templates.find((entry) => entry.title === 'Dismiss Endpoint Target');
            expect(row).toBeDefined();
            expect(row.issues.length).toBeGreaterThan(0);
            const issue = row.issues[0];
            expect(issue.key).toBeDefined();
            expect(issue.dismissed).toBe(false);
            const totalBefore = status.report.counts.total;

            let response = await request(app).post('/api/ai/vulnerabilities/qa/dismiss')
                .set('Cookie', [`token=JWT ${adminToken}`])
                .send({ locale: 'en', vulnerabilityId: row.vulnerabilityId, key: issue.key, dismissed: true });
            expect(response.status).toBe(200);

            let refreshed = await request(app).get('/api/ai/vulnerabilities/qa/status?locale=en')
                .set('Cookie', [`token=JWT ${adminToken}`]);
            expect(refreshed.status).toBe(200);
            let refreshedRow = refreshed.body.datas.report.templates
                .find((entry) => entry.vulnerabilityId === row.vulnerabilityId);
            expect(refreshedRow.issues.find((entry) => entry.key === issue.key).dismissed).toBe(true);
            expect(refreshed.body.datas.report.counts.total).toBe(totalBefore - 1);
            expect(refreshed.body.datas.report.dismissedCount).toBeGreaterThanOrEqual(1);

            response = await request(app).post('/api/ai/vulnerabilities/qa/dismiss')
                .set('Cookie', [`token=JWT ${adminToken}`])
                .send({ locale: 'en', vulnerabilityId: row.vulnerabilityId, key: issue.key, dismissed: false });
            expect(response.status).toBe(200);

            refreshed = await request(app).get('/api/ai/vulnerabilities/qa/status?locale=en')
                .set('Cookie', [`token=JWT ${adminToken}`]);
            refreshedRow = refreshed.body.datas.report.templates
                .find((entry) => entry.vulnerabilityId === row.vulnerabilityId);
            expect(refreshedRow.issues.find((entry) => entry.key === issue.key).dismissed).toBe(false);

            // Catalog-level dismissals persist on the catalog document (no vulnerabilityId).
            response = await request(app).post('/api/ai/vulnerabilities/qa/dismiss')
                .set('Cookie', [`token=JWT ${adminToken}`])
                .send({ locale: 'en', key: 'duplicates|Dup|vulnerability:A|a,b' });
            expect(response.status).toBe(200);

            response = await request(app).post('/api/ai/vulnerabilities/qa/dismiss')
                .set('Cookie', [`token=JWT ${adminToken}`])
                .send({ locale: 'en' });
            expect(response.status).toBe(422);

            response = await request(app).post('/api/ai/vulnerabilities/qa/dismiss')
                .set('Cookie', [`token=JWT ${noAiToken}`])
                .send({ locale: 'en', vulnerabilityId: row.vulnerabilityId, key: issue.key });
            expect(response.status).toBe(403);
        });

        it('should resolve and unresolve a whole vulnerability from the assembled report', async () => {
            await setProgrammaticOnlyChecks();

            await request(app).post('/api/vulnerabilities')
                .set('Cookie', [`token=JWT ${adminToken}`])
                .send([{
                    category: 'Web',
                    details: [{
                        locale: 'en',
                        title: 'Resolve Endpoint Target',
                        vulnType: 'Web',
                        description: '<p>content</p>',
                        observation: '',
                        remediation: ''
                    }]
                }]);

            const runResponse = await request(app).post('/api/ai/vulnerabilities/qa/run')
                .set('Cookie', [`token=JWT ${adminToken}`])
                .send({ locale: 'en', scope: 'programmatic' });
            expect(runResponse.status).toBe(200);

            const status = await waitForQaJob('en');
            const row = status.report.templates.find((entry) => entry.title === 'Resolve Endpoint Target');
            expect(row).toBeDefined();
            expect(row.issues.length).toBeGreaterThan(0);
            expect(row.resolved).toBe(false);
            const activeBefore = status.report.counts.total;

            let response = await request(app).post('/api/ai/vulnerabilities/qa/resolve')
                .set('Cookie', [`token=JWT ${adminToken}`])
                .send({ locale: 'en', vulnerabilityId: row.vulnerabilityId, resolved: true });
            expect(response.status).toBe(200);

            let refreshed = await request(app).get('/api/ai/vulnerabilities/qa/status?locale=en')
                .set('Cookie', [`token=JWT ${adminToken}`]);
            let refreshedRow = refreshed.body.datas.report.templates
                .find((entry) => entry.vulnerabilityId === row.vulnerabilityId);
            expect(refreshedRow.resolved).toBe(true);
            // Every issue on the vuln hides, so the active total drops by the row's count.
            expect(refreshed.body.datas.report.counts.total).toBe(activeBefore - row.issues.length);
            expect(refreshed.body.datas.report.dismissedCount).toBeGreaterThanOrEqual(row.issues.length);

            response = await request(app).post('/api/ai/vulnerabilities/qa/resolve')
                .set('Cookie', [`token=JWT ${adminToken}`])
                .send({ locale: 'en', vulnerabilityId: row.vulnerabilityId, resolved: false });
            expect(response.status).toBe(200);

            refreshed = await request(app).get('/api/ai/vulnerabilities/qa/status?locale=en')
                .set('Cookie', [`token=JWT ${adminToken}`]);
            refreshedRow = refreshed.body.datas.report.templates
                .find((entry) => entry.vulnerabilityId === row.vulnerabilityId);
            expect(refreshedRow.resolved).toBe(false);
            expect(refreshed.body.datas.report.counts.total).toBe(activeBefore);

            response = await request(app).post('/api/ai/vulnerabilities/qa/resolve')
                .set('Cookie', [`token=JWT ${adminToken}`])
                .send({ locale: 'en' });
            expect(response.status).toBe(422);

            response = await request(app).post('/api/ai/vulnerabilities/qa/resolve')
                .set('Cookie', [`token=JWT ${noAiToken}`])
                .send({ locale: 'en', vulnerabilityId: row.vulnerabilityId, resolved: true });
            expect(response.status).toBe(403);
        });

        it('should reject cancelling when no QA job is running', async () => {
            const response = await request(app).post('/api/ai/vulnerabilities/qa/cancel')
                .set('Cookie', [`token=JWT ${adminToken}`])
                .send({ locale: 'zz' });

            expect(response.status).toBe(422);
        });

        it('should load the all-templates cached report when loadOnly is requested with no vulnerabilityId or draft', async () => {
            const response = await request(app).post('/api/ai/vulnerabilities/qa')
                .set('Cookie', [`token=JWT ${adminToken}`])
                .send({
                    locale: 'en',
                    loadOnly: true
                });

            expect(response.status).toBe(200);
            expect(response.body.datas.mode).toBe('all');
        });

        it('should load a single vulnerability QA report without fetching the entire vulnerability database', async () => {
            await request(app).post('/api/vulnerabilities')
                .set('Cookie', [`token=JWT ${adminToken}`])
                .send([{
                    category: 'Web',
                    details: [{
                        locale: 'en',
                        title: 'Single Load Target',
                        vulnType: 'Web',
                        description: '',
                        observation: '',
                        remediation: ''
                    }]
                }]);

            const listResponse = await request(app).get('/api/vulnerabilities')
                .set('Cookie', [`token=JWT ${adminToken}`]);
            const created = listResponse.body.datas.find((entry) => entry.details[0]?.title === 'Single Load Target');
            expect(created).toBeDefined();

            const getAllSpy = jest.spyOn(Vulnerability, 'getAll');

            const response = await request(app).post('/api/ai/vulnerabilities/qa')
                .set('Cookie', [`token=JWT ${adminToken}`])
                .send({
                    locale: 'en',
                    loadOnly: true,
                    vulnerabilityId: created._id
                });

            expect(response.status).toBe(200);
            expect(response.body.datas.mode).toBe('single');
            expect(getAllSpy).not.toHaveBeenCalled();

            getAllSpy.mockRestore();
        });

        it('should not query the database at all for a draft vulnerability loadOnly request', async () => {
            const getAllSpy = jest.spyOn(Vulnerability, 'getAll');

            const response = await request(app).post('/api/ai/vulnerabilities/qa')
                .set('Cookie', [`token=JWT ${adminToken}`])
                .send({
                    locale: 'en',
                    loadOnly: true,
                    vulnerability: {
                        category: 'Web',
                        details: [{ locale: 'en', title: 'Unsaved Draft' }]
                    }
                });

            expect(response.status).toBe(200);
            expect(response.body.datas.hasReport).toBe(false);
            expect(getAllSpy).not.toHaveBeenCalled();

            getAllSpy.mockRestore();
        });

    // Audit and single-vuln QA run their LLM call as a detached background job
    // (ai-qa-single-job.js), so a slow provider can't hold the connection to a proxy
    // timeout. The start response returns the job; the report is read back via loadOnly.
    describe('AI QA background jobs (single-call)', () => {
        const waitForSingleJobDone = async (poll) => {
            for (let attempt = 0; attempt < 100; attempt++) {
                const response = await poll();
                expect(response.status).toBe(200);
                const job = response.body.datas.job;
                if (job && ['done', 'failed'].includes(job.state))
                    return response.body.datas;
                await new Promise((resolve) => setTimeout(resolve, 100));
            }
            throw new Error('QA job did not finish in time');
        };

        it('should start audit QA as a background job for AI scope and persist the report once done', async () => {
            const auditResponse = await request(app).post('/api/audits')
                .set('Cookie', [`token=JWT ${adminToken}`])
                .send({ name: 'AI QA Job Audit', language: 'en', auditType: 'Web' });
            expect(auditResponse.status).toBe(201);
            const auditId = auditResponse.body.datas.audit._id;

            const startResponse = await request(app).post('/api/ai/qa')
                .set('Cookie', [`token=JWT ${adminToken}`])
                .send({ auditId, scope: 'all' });

            expect(startResponse.status).toBe(200);
            expect(startResponse.body.datas.auditId).toBe(auditId);
            expect(startResponse.body.datas.job).toEqual(expect.objectContaining({
                auditId,
                scope: 'all',
                state: 'running'
            }));
            expect(startResponse.body.datas.hasReport).toBeUndefined();
            // The double-run guard is covered deterministically in ai-qa-single-job.test.js;
            // over real HTTP the job resolves too fast (synchronous missing-key error) to
            // still be "running" when a second request lands.

            const finalStatus = await waitForSingleJobDone(() => request(app).post('/api/ai/qa')
                .set('Cookie', [`token=JWT ${adminToken}`])
                .send({ auditId, loadOnly: true }));

            expect(finalStatus.job.state).toBe('done');
            expect(finalStatus.hasReport).toBe(true);
            expect(Array.isArray(finalStatus.issues)).toBe(true);
        });

        it('should resolve audit QA inline (no job) for the programmatic-only scope', async () => {
            const auditResponse = await request(app).post('/api/audits')
                .set('Cookie', [`token=JWT ${adminToken}`])
                .send({ name: 'Programmatic QA Audit', language: 'en', auditType: 'Web' });
            expect(auditResponse.status).toBe(201);
            const auditId = auditResponse.body.datas.audit._id;

            const response = await request(app).post('/api/ai/qa')
                .set('Cookie', [`token=JWT ${adminToken}`])
                .send({ auditId, scope: 'programmatic' });

            expect(response.status).toBe(200);
            expect(response.body.datas.hasReport).toBe(true);
            expect(response.body.datas.job).toBeUndefined();
        });

        it('should start single-vulnerability QA as a background job for AI scope and persist the report once done', async () => {
            await request(app).post('/api/vulnerabilities')
                .set('Cookie', [`token=JWT ${adminToken}`])
                .send([{
                    category: 'Web',
                    details: [{
                        locale: 'en',
                        title: 'Single Job Target',
                        vulnType: 'Web',
                        description: '<p>content</p>',
                        observation: '',
                        remediation: ''
                    }]
                }]);

            const listResponse = await request(app).get('/api/vulnerabilities')
                .set('Cookie', [`token=JWT ${adminToken}`]);
            const created = listResponse.body.datas.find((entry) => entry.details[0]?.title === 'Single Job Target');
            expect(created).toBeDefined();

            const startResponse = await request(app).post('/api/ai/vulnerabilities/qa')
                .set('Cookie', [`token=JWT ${adminToken}`])
                .send({ locale: 'en', scope: 'all', vulnerabilityId: created._id });

            expect(startResponse.status).toBe(200);
            expect(startResponse.body.datas.vulnerabilityId).toBe(created._id);
            expect(startResponse.body.datas.job).toEqual(expect.objectContaining({
                vulnerabilityId: created._id,
                locale: 'en',
                state: 'running'
            }));
            expect(startResponse.body.datas.hasReport).toBeUndefined();
            // See the audit QA test above - the double-run guard is covered deterministically
            // at the module level in ai-qa-single-job.test.js instead of here.

            const finalStatus = await waitForSingleJobDone(() => request(app).post('/api/ai/vulnerabilities/qa')
                .set('Cookie', [`token=JWT ${adminToken}`])
                .send({ locale: 'en', loadOnly: true, vulnerabilityId: created._id }));

            expect(finalStatus.job.state).toBe('done');
            expect(finalStatus.hasReport).toBe(true);
            expect(finalStatus.mode).toBe('single');
        });

        it('should resolve single-vulnerability QA inline (no job) for the programmatic-only scope', async () => {
            await request(app).post('/api/vulnerabilities')
                .set('Cookie', [`token=JWT ${adminToken}`])
                .send([{
                    category: 'Web',
                    details: [{
                        locale: 'en',
                        title: 'Single Programmatic Target',
                        vulnType: 'Web',
                        description: '<p>content</p>',
                        observation: '',
                        remediation: ''
                    }]
                }]);

            const listResponse = await request(app).get('/api/vulnerabilities')
                .set('Cookie', [`token=JWT ${adminToken}`]);
            const created = listResponse.body.datas.find((entry) => entry.details[0]?.title === 'Single Programmatic Target');
            expect(created).toBeDefined();

            const response = await request(app).post('/api/ai/vulnerabilities/qa')
                .set('Cookie', [`token=JWT ${adminToken}`])
                .send({ locale: 'en', scope: 'programmatic', vulnerabilityId: created._id });

            expect(response.status).toBe(200);
            expect(response.body.datas.hasReport).toBe(true);
            expect(response.body.datas.job).toBeUndefined();
        });
    });

    // /api/ai/generate streams over SSE (a heartbeat per LLM chunk) so nginx's idle timeout
    // can't fire mid-generation; the draft/reply contract is unchanged, only the transport.
    describe('AI generate streaming', () => {
        const parseSseEvents = (text) => String(text || '')
            .split('\n\n')
            .filter((block) => block.trim())
            .map((block) => {
                let event = 'message';
                const dataLines = [];
                block.split('\n').forEach((line) => {
                    if (line.startsWith('event:'))
                        event = line.slice(6).trim();
                    else if (line.startsWith('data:'))
                        dataLines.push(line.slice(5).trim());
                });
                return { event, data: dataLines.length ? JSON.parse(dataLines.join('\n')) : null };
            });

        it('should respond with an SSE error event when no provider is configured', async () => {
            const response = await request(app).post('/api/ai/generate')
                .set('Cookie', [`token=JWT ${adminToken}`])
                .send({
                    entityType: 'finding',
                    field: 'description',
                    userPrompt: 'Write something',
                    context: {}
                });

            // Headers commit to the stream before the provider is contacted, so even a
            // configuration error comes back as a 200 SSE error event, not a 4xx/5xx JSON body.
            expect(response.status).toBe(200);
            expect(response.headers['content-type']).toMatch(/text\/event-stream/);

            const events = parseSseEvents(response.text);
            const errorEvent = events.find((event) => event.event === 'error');
            expect(errorEvent).toBeDefined();
            expect(errorEvent.data.message).toMatch(/not configured/i);
        });

        it('should still reject validation errors as plain JSON before streaming starts', async () => {
            const response = await request(app).post('/api/ai/generate')
                .set('Cookie', [`token=JWT ${adminToken}`])
                .send({ entityType: 'finding', field: 'not-a-real-field' });

            expect(response.status).toBe(422);
            expect(response.headers['content-type']).toMatch(/json/);
        });
    });

    // The default provider is always implicitly allowed; allowedProviders extends that set.
    // A request for a provider outside that set is rejected server-side (403 JSON) before any
    // streaming starts, regardless of what the UI offered.
    describe('AI provider allow-list enforcement', () => {
        afterEach(async () => {
            await Settings.findOneAndUpdate({}, {
                $set: {
                    'ai.public.defaultProvider': 'openai',
                    'ai.public.allowedProviders': []
                }
            }, { upsert: true });
        });

        it('should reject a provider that is not permitted with a 403 JSON response', async () => {
            await Settings.findOneAndUpdate({}, {
                $set: {
                    'ai.public.defaultProvider': 'openai',
                    'ai.public.allowedProviders': []
                }
            }, { upsert: true });

            const response = await request(app).post('/api/ai/generate')
                .set('Cookie', [`token=JWT ${adminToken}`])
                .send({
                    entityType: 'finding',
                    field: 'description',
                    provider: 'anthropic',
                    userPrompt: 'Write something',
                    context: {}
                });

            expect(response.status).toBe(403);
            expect(response.headers['content-type']).toMatch(/json/);
            expect(response.body.datas).toMatch(/not permitted/i);
        });

        it('should allow a provider that the admin added to allowedProviders', async () => {
            await Settings.findOneAndUpdate({}, {
                $set: {
                    'ai.public.defaultProvider': 'openai',
                    'ai.public.allowedProviders': ['anthropic']
                }
            }, { upsert: true });

            const response = await request(app).post('/api/ai/generate')
                .set('Cookie', [`token=JWT ${adminToken}`])
                .send({
                    entityType: 'finding',
                    field: 'description',
                    provider: 'anthropic',
                    userPrompt: 'Write something',
                    context: {}
                });

            // Permitted: passes provider resolution and reaches the SSE stream, where the
            // unconfigured provider surfaces as an SSE error event (200), not a 403.
            expect(response.status).toBe(200);
            expect(response.headers['content-type']).toMatch(/text\/event-stream/);
        });

        it('should always allow the default provider even when allowedProviders is empty', async () => {
            await Settings.findOneAndUpdate({}, {
                $set: {
                    'ai.public.defaultProvider': 'anthropic',
                    'ai.public.allowedProviders': []
                }
            }, { upsert: true });

            const response = await request(app).post('/api/ai/generate')
                .set('Cookie', [`token=JWT ${adminToken}`])
                .send({
                    entityType: 'finding',
                    field: 'description',
                    provider: 'anthropic',
                    userPrompt: 'Write something',
                    context: {}
                });

            expect(response.status).toBe(200);
            expect(response.headers['content-type']).toMatch(/text\/event-stream/);
        });

        it('should reject an unknown provider id with a 422 JSON response', async () => {
            const response = await request(app).post('/api/ai/generate')
                .set('Cookie', [`token=JWT ${adminToken}`])
                .send({
                    entityType: 'finding',
                    field: 'description',
                    provider: 'not-a-provider',
                    userPrompt: 'Write something',
                    context: {}
                });

            expect(response.status).toBe(422);
            expect(response.headers['content-type']).toMatch(/json/);
            expect(response.body.datas).toMatch(/unsupported provider/i);
        });
    });
    });
};
