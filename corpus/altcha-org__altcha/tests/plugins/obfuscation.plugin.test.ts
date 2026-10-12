import { describe, expect, test } from 'vitest';
import { deriveKey } from '../../src/algorithms/pbkdf2';
import { hexToBuffer } from '../../src/helpers';
import { ObfuscationPlugin } from '../../src/plugins/obfuscation.plugin';

describe('ObfuscationPlugin', () => {
	describe('obfuscate()', () => {
		test('should return obfuscated data as base64 string', async () => {
			const result = await ObfuscationPlugin.obfuscate('hello world');
			expect(result).toBeTypeOf('string');
			const decoded = JSON.parse(atob(result));
			expect(decoded.parameters.algorithm).toEqual('PBKDF2/SHA-256');
			expect(decoded.parameters.cost).toBeDefined();
			expect(decoded.parameters.salt).toBeDefined();
			expect(decoded.parameters.nonce).toBeDefined();
			expect(decoded.parameters.keyPrefix).toBeDefined();
			expect(decoded.cipher.iv).toBeDefined();
			expect(decoded.cipher.data).toBeDefined();
		});
	});

	describe('deobfuscate()', () => {
		test('should return de-obfuscated data', async () => {
			const data = await ObfuscationPlugin.obfuscate('hello world');
			const result = await ObfuscationPlugin.deobfuscate(data, {
				deriveKey
			});
			expect(result).toEqual('hello world');
		});

		test('should not expose the AES key when keyPrefixLength is overridden', async () => {
			const obfuscated = await ObfuscationPlugin.obfuscate('hello world', { keyPrefixLength: 16 });
			const { cipher, parameters } = JSON.parse(atob(obfuscated));
			expect(parameters.keyPrefix.length).toEqual(32);
			const leakedKey = await crypto.subtle.importKey(
				'raw',
				hexToBuffer(parameters.keyPrefix) as Uint8Array<ArrayBuffer>,
				{ name: 'AES-GCM' },
				false,
				['decrypt']
			);
			await expect(
				crypto.subtle.decrypt(
					{ name: 'AES-GCM', iv: hexToBuffer(cipher.iv) as Uint8Array<ArrayBuffer> },
					leakedKey,
					hexToBuffer(cipher.data) as Uint8Array<ArrayBuffer>
				)
			).rejects.toThrow();
			expect(await ObfuscationPlugin.deobfuscate(obfuscated, { deriveKey })).toEqual('hello world');
		});
	});
});
