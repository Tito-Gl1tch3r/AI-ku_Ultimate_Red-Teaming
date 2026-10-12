module.exports = function(request, app) {
    describe('AI provider connection test', () => {
        const Settings = require('mongoose').model('Settings');
        const { MASKED_SECRET } = require('../src/lib/settings-secrets');
        let adminToken = '';
        let userToken = '';

        beforeAll(async () => {
            let response = await request(app).post('/api/users/token').send({ username: 'admin', password: 'Admin123' });
            adminToken = response.body.datas.token;

            response = await request(app).post('/api/users/token').send({ username: 'user2', password: 'User1234' });
            userToken = response.body.datas.token;
        });

        beforeEach(async () => {
            await Settings.findOneAndUpdate({}, {
                $set: {
                    'ai.private.openaiApiKey': '',
                    'ai.private.anthropicApiKey': '',
                    'ai.private.bedrockApiKey': '',
                    'ai.private.bedrockAccessKeyId': '',
                    'ai.private.bedrockSecretAccessKey': ''
                }
            }, { upsert: true });
        });

        it('rejects an unsupported provider', async () => {
            const response = await request(app).post('/api/ai/test')
                .set('Cookie', [`token=JWT ${adminToken}`])
                .send({ provider: 'not-a-real-provider' });

            expect(response.status).toBe(422);
            expect(response.body.datas).toMatch(/Unsupported provider/);
        });

        it('reports a clear error when the provider has no API key configured', async () => {
            const response = await request(app).post('/api/ai/test')
                .set('Cookie', [`token=JWT ${adminToken}`])
                .send({ provider: 'openai' });

            expect(response.status).toBe(422);
            expect(response.body.datas).toMatch(/OpenAI provider is not configured/);
        });

        it('reports a clear error for Bedrock with neither an API key nor IAM credentials', async () => {
            const response = await request(app).post('/api/ai/test')
                .set('Cookie', [`token=JWT ${adminToken}`])
                .send({ provider: 'bedrock' });

            expect(response.status).toBe(422);
            expect(response.body.datas).toMatch(/Bedrock provider is not configured/);
        });

        it('falls back to the stored key when the client resends the masked sentinel', async () => {
            // No stored key and a masked sentinel override should still resolve to "not configured",
            // proving the masked value itself is never used as a literal API key.
            const response = await request(app).post('/api/ai/test')
                .set('Cookie', [`token=JWT ${adminToken}`])
                .send({ provider: 'openai', openaiApiKey: MASKED_SECRET });

            expect(response.status).toBe(422);
            expect(response.body.datas).toMatch(/OpenAI provider is not configured/);
        });

        it('requires settings:update permission', async () => {
            const response = await request(app).post('/api/ai/test')
                .set('Cookie', [`token=JWT ${userToken}`])
                .send({ provider: 'openai' });

            expect(response.status).toBe(403);
        });
    });
};
