import type { Session as ElectronSession } from 'electron';
import type { FingerprintProfile } from '@shared/types';

/**
 * Apply HTTP-level fingerprint spoofing to an Electron session.
 * - Sets the User-Agent globally
 * - Intercepts outgoing requests to rewrite Client Hints and Accept-Language headers
 */
export function applyHttpSpoofing(
  electronSession: ElectronSession,
  profile: FingerprintProfile,
): void {
  // Set global User-Agent
  electronSession.setUserAgent(profile.userAgent);

  // Build Client Hints values from profile
  const majorVersion = profile.userAgent.match(/Chrome\/(\d+)/)?.[1] ?? '131';
  const brandList = `"Chromium";v="${majorVersion}", "Google Chrome";v="${majorVersion}", "Not-A.Brand";v="8"`;
  const platformMap: Record<string, string> = {
    'Win32': '"Windows"',
    'MacIntel': '"macOS"',
    'Linux x86_64': '"Linux"',
  };
  const secPlatform = platformMap[profile.platform] ?? '"Windows"';
  const acceptLanguage = profile.languages
    .map((lang, i) => i === 0 ? lang : `${lang};q=${(1 - i * 0.1).toFixed(1)}`)
    .join(',');

  // Intercept and rewrite headers
  electronSession.webRequest.onBeforeSendHeaders((details, callback) => {
    const headers = { ...details.requestHeaders };

    headers['Accept-Language'] = acceptLanguage;
    headers['Sec-CH-UA'] = brandList;
    headers['Sec-CH-UA-Platform'] = secPlatform;
    headers['Sec-CH-UA-Mobile'] = '?0';

    callback({ requestHeaders: headers });
  });
}

/**
 * Remove HTTP spoofing from an Electron session.
 * Restores default behavior by passing through all headers unchanged.
 */
export function removeHttpSpoofing(electronSession: ElectronSession): void {
  electronSession.webRequest.onBeforeSendHeaders(null);
}
