const {
    chunkWithOverlap,
    compactLlmValue,
    stringifyLlmPayload,
    stripHtml
} = require('../src/lib/ai-qa-shared');

module.exports = function() {
    it('strips HTML without backtracking over repeated tag openers', () => {
        const input = '<'.repeat(100000);
        expect(stripHtml(input)).toBe(input);
    });

    describe('LLM payload compaction', () => {
        it('should omit empty fields and nested empty sections', () => {
            const compacted = compactLlmValue({
                task: 'duplicate',
                locale: 'en',
                mode: 'all',
                target: null,
                enabledChecks: {
                    completeness: true,
                    redaction: false
                },
                templates: [
                    {
                        vulnerabilityId: '1',
                        title: 'SQLi',
                        vulnType: 'Injection',
                        category: '',
                        description: 'Login form.',
                        observation: '   ',
                        remediation: '',
                        references: [],
                        meta: {}
                    },
                    {
                        vulnerabilityId: '2',
                        title: '',
                        description: ''
                    }
                ]
            });

            expect(compacted).toEqual({
                task: 'duplicate',
                locale: 'en',
                mode: 'all',
                enabledChecks: {
                    completeness: true
                },
                templates: [
                    {
                        vulnerabilityId: '1',
                        title: 'SQLi',
                        vulnType: 'Injection',
                        description: 'Login form.'
                    }
                ]
            });
        });

        it('should stringify without whitespace padding', () => {
            const payload = stringifyLlmPayload({
                task: 'qa',
                notes: '',
                items: [{ id: 1, empty: null }]
            });

            expect(payload).toBe('{"task":"qa","items":[{"id":1}]}');
        });
    });

    describe('chunkWithOverlap', () => {
        it('should return a single batch when items fit within the batch size', () => {
            const items = [1, 2, 3];
            expect(chunkWithOverlap(items, 40, 5)).toEqual([[1, 2, 3]]);
        });

        it('should return no batches for an empty array', () => {
            expect(chunkWithOverlap([], 40, 5)).toEqual([]);
        });

        it('should split items exceeding the batch size into multiple batches', () => {
            const items = Array.from({ length: 90 }, (_, i) => i);
            const batches = chunkWithOverlap(items, 40, 0);

            expect(batches).toHaveLength(3);
            expect(batches[0]).toHaveLength(40);
            expect(batches[1]).toHaveLength(40);
            expect(batches[2]).toHaveLength(10);
        });

        it('should overlap consecutive batches so boundary items appear twice', () => {
            const items = Array.from({ length: 90 }, (_, i) => i);
            const batches = chunkWithOverlap(items, 40, 5);

            expect(batches).toHaveLength(3);
            // last 5 of batch 0 reappear as the first 5 of batch 1
            expect(batches[0].slice(-5)).toEqual(batches[1].slice(0, 5));
            expect(batches[1].slice(-5)).toEqual(batches[2].slice(0, 5));

            const covered = new Set(batches.flat());
            expect(covered.size).toBe(items.length);
        });
    });
};
