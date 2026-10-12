const dns = require('dns').promises;
const https = require('https');
const {
    extractUrlsFromReferences,
    isBlockedReferenceUrl,
    isAllowedReferenceUrl,
    validateReferenceUrl,
    runReferenceLinkChecks
} = require('../src/lib/ai-qa-link-checker');

module.exports = function() {
    describe('AI QA reference link checker', () => {
        let lookupSpy = null;

        // Build a fake ClientRequest whose callback yields the given response (or emits the
        // given error). `onOptions` lets a test capture the options passed to request(),
        // notably the pinned `lookup`.
        const fakeRequestImpl = ({ status, headers = {}, error = null, onOptions } = {}) =>
            (url, options, callback) => {
                if (onOptions)
                    onOptions(options);

                const request = {
                    setTimeout: jest.fn(),
                    on: jest.fn((event, handler) => {
                        if (event === 'error' && error)
                            setImmediate(() => handler(error));
                        return request;
                    }),
                    destroy: jest.fn(),
                    end: jest.fn(() => {
                        if (!error)
                            setImmediate(() => callback({ statusCode: status, headers: headers, resume: jest.fn() }));
                    })
                };

                return request;
            };

        const mockHttps = (config) => jest.spyOn(https, 'request').mockImplementation(fakeRequestImpl(config));

        beforeEach(() => {
            lookupSpy = jest.spyOn(dns, 'lookup').mockImplementation(async (hostname, options = {}) => {
                if (hostname === 'example.com') {
                    const entries = [{ address: '93.184.216.34', family: 4 }];
                    return options.all ? entries : entries[0];
                }
                throw new Error(`Unexpected DNS lookup for ${hostname}`);
            });
        });

        afterEach(() => {
            jest.restoreAllMocks();
        });

        it('should extract HTTP(S) URLs from reference strings', () => {
            const urls = extractUrlsFromReferences([
                'CWE-79: https://cwe.mitre.org/data/definitions/79.html',
                'OWASP https://owasp.org/www-project-top-ten/'
            ]);

            expect(urls).toEqual([
                'https://cwe.mitre.org/data/definitions/79.html',
                'https://owasp.org/www-project-top-ten/'
            ]);
        });

        it('should keep balanced parentheses but strip trailing prose punctuation', () => {
            expect(extractUrlsFromReferences([
                'OWASP https://www.owasp.org/index.php/Testing_(OTG-AUTHZ-004)'
            ])).toEqual(['https://www.owasp.org/index.php/Testing_(OTG-AUTHZ-004)']);

            expect(extractUrlsFromReferences([
                'wiki https://en.wikipedia.org/wiki/Foo_(disambiguation) here'
            ])).toEqual(['https://en.wikipedia.org/wiki/Foo_(disambiguation)']);

            // An unbalanced trailing ')' from surrounding prose must be dropped.
            expect(extractUrlsFromReferences([
                'see (https://example.com/page).'
            ])).toEqual(['https://example.com/page']);
        });

        it('should block private, local and CGNAT URLs', () => {
            expect(isBlockedReferenceUrl('http://localhost/test')).toBe(true);
            expect(isBlockedReferenceUrl('http://127.0.0.1/test')).toBe(true);
            expect(isBlockedReferenceUrl('http://192.168.1.10/test')).toBe(true);
            expect(isBlockedReferenceUrl('http://100.64.0.1/test')).toBe(true);
            expect(isBlockedReferenceUrl('http://100.127.255.255/test')).toBe(true);
            expect(isBlockedReferenceUrl('ftp://example.com/test')).toBe(true);
            expect(isBlockedReferenceUrl('https://example.com/test')).toBe(false);
            // 100.128.0.0 is just outside the CGNAT range and must stay allowed.
            expect(isBlockedReferenceUrl('http://100.128.0.1/test')).toBe(false);
        });

        it('should block hostnames that resolve to private addresses', async () => {
            lookupSpy.mockResolvedValueOnce([{ address: '127.0.0.1', family: 4 }]);

            expect(await isAllowedReferenceUrl('https://evil.example/test')).toBe(false);
        });

        it('should block hostnames that resolve to CGNAT addresses', async () => {
            lookupSpy.mockResolvedValueOnce([{ address: '100.64.5.5', family: 4 }]);

            expect(await isAllowedReferenceUrl('https://evil.example/test')).toBe(false);
        });

        it('should allow hostnames that resolve to public addresses', async () => {
            expect(await isAllowedReferenceUrl('https://example.com/test')).toBe(true);
        });

        it('should pin the outbound request to the validated address (defeats DNS rebinding)', async () => {
            let capturedOptions = null;
            mockHttps({ status: 200, onOptions: (options) => { capturedOptions = options; } });

            const result = await validateReferenceUrl('https://example.com/ok');
            expect(result.valid).toBe(true);

            // The request must carry a lookup pinned to the address we validated, not re-resolve.
            expect(typeof capturedOptions.lookup).toBe('function');
            const pinned = await new Promise((resolve) => {
                capturedOptions.lookup('example.com', {}, (err, address) => resolve(address));
            });
            expect(pinned).toBe('93.184.216.34');
        });

        it('should flag unreachable reference URLs', async () => {
            mockHttps({ error: new Error('network down') });

            const result = await validateReferenceUrl('https://example.com/missing');
            expect(result.valid).toBe(false);
            expect(result.severity).toBe('error');
            expect(result.message).toContain('could not be reached');
        });

        it('should treat HTTP 404 as an invalid reference', async () => {
            mockHttps({ status: 404 });

            const result = await validateReferenceUrl('https://example.com/missing');
            expect(result.valid).toBe(false);
            expect(result.severity).toBe('error');
            expect(result.message).toContain('404');
        });

        it('should treat HTTP 400 with the same severity as 404', async () => {
            mockHttps({ status: 400 });

            const result = await validateReferenceUrl('https://example.com/bad-request');
            expect(result.valid).toBe(false);
            expect(result.severity).toBe('error');
            expect(result.message).toContain('400');
            expect(result.message).toContain('unavailable');
        });

        it('should accept healthy reference URLs', async () => {
            mockHttps({ status: 200 });

            const result = await validateReferenceUrl('https://example.com/ok');
            expect(result.valid).toBe(true);
        });

        it('should retry with GET when HEAD is rejected but the resource is reachable', async () => {
            // Many servers/CDNs bot-block or don't implement HEAD, answering 404/403 while a
            // browser's GET succeeds. Return a bad status only for HEAD, 200 for GET.
            const methods = [];
            jest.spyOn(https, 'request').mockImplementation((url, options, callback) => {
                methods.push(options.method);
                const status = options.method === 'HEAD' ? 404 : 200;
                const request = {
                    setTimeout: jest.fn(),
                    on: jest.fn(() => request),
                    destroy: jest.fn(),
                    end: jest.fn(() => setImmediate(() =>
                        callback({ statusCode: status, headers: {}, resume: jest.fn() })))
                };
                return request;
            });

            const result = await validateReferenceUrl('https://example.com/head-hostile');
            expect(result.valid).toBe(true);
            expect(methods).toEqual(['HEAD', 'GET']);
        });

        it('should block redirects to private URLs', async () => {
            const httpsSpy = mockHttps({
                status: 302,
                headers: { location: 'http://127.0.0.1/internal' }
            });

            const result = await validateReferenceUrl('https://example.com/redirect');
            expect(result.valid).toBe(false);
            expect(result.message).toContain('private or local address');
            // The private redirect target is rejected at validation, before any second request.
            expect(httpsSpy).toHaveBeenCalledTimes(1);
        });

        it('should report unresolved hostnames clearly', async () => {
            const result = await validateReferenceUrl('https://developpper.mozilla.org/docs');
            expect(result.valid).toBe(false);
            expect(result.severity).toBe('warning');
            expect(result.message).toBe('Reference URL hostname could not be resolved.');
        });

        it('should create issues for invalid finding reference links', async () => {
            mockHttps({ status: 404 });

            const issues = await runReferenceLinkChecks({
                findings: [{
                    identifier: 3,
                    title: 'XSS',
                    references: ['https://example.com/broken-link']
                }]
            });

            expect(issues).toHaveLength(1);
            expect(issues[0].category).toBe('references');
            expect(issues[0].location).toBe('finding:XSS/references');
            expect(issues[0].message).toContain('https://example.com/broken-link');
        });
    });
};
