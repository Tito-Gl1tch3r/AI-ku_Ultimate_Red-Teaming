import type { FingerprintProfile } from '@shared/types';
import {
  ALL_PRESETS,
  CHROME_VERSIONS,
  TIMEZONE_LANGUAGES,
  TIMEZONE_OFFSETS,
  type DevicePreset,
} from './presets';

/** Pick a random element from an array */
function pick<T>(arr: readonly T[]): T {
  return arr[Math.floor(Math.random() * arr.length)];
}

/** Generate a random 32-bit unsigned integer */
function randomSeed(): number {
  return Math.floor(Math.random() * 0xFFFFFFFF);
}

/** Detect the system timezone */
function getSystemTimezone(): string {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone;
  } catch {
    return 'Asia/Shanghai';
  }
}

/** Build a full Chrome user-agent string */
function buildUserAgent(preset: DevicePreset, chromeVersion: string): string {
  if (preset.platform === 'MacIntel') {
    return `Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/${chromeVersion} Safari/537.36`;
  }
  if (preset.platform === 'Linux x86_64') {
    return `Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/${chromeVersion} Safari/537.36`;
  }
  // Windows
  return `Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/${chromeVersion} Safari/537.36`;
}

/** Build the appVersion string (UA without "Mozilla/") */
function buildAppVersion(ua: string): string {
  return ua.replace('Mozilla/', '');
}

/**
 * Generate a complete, logically consistent FingerprintProfile.
 */
export function generateProfile(sessionId: string): FingerprintProfile {
  const preset = pick(ALL_PRESETS);
  const chromeVersion = pick(CHROME_VERSIONS);
  const screen = pick(preset.screens);
  const dpr = pick(preset.dprs);
  const concurrency = pick(preset.hardwareConcurrencies);
  // deviceMemory should be positively correlated with concurrency
  const memoryOptions = preset.deviceMemories.filter(m => m >= concurrency);
  const memory = memoryOptions.length > 0 ? pick(memoryOptions) : pick(preset.deviceMemories);

  const timezone = getSystemTimezone();
  const languages = TIMEZONE_LANGUAGES[timezone] || ['en-US', 'en'];
  const timezoneOffset = TIMEZONE_OFFSETS[timezone] ?? -new Date().getTimezoneOffset();

  const ua = buildUserAgent(preset, chromeVersion);

  return {
    sessionId,
    userAgent: ua,
    platform: preset.platform,
    oscpu: preset.oscpu,
    appVersion: buildAppVersion(ua),
    screenWidth: screen[0],
    screenHeight: screen[1],
    colorDepth: preset.colorDepth,
    devicePixelRatio: dpr,
    hardwareConcurrency: concurrency,
    deviceMemory: memory,
    webglVendor: pick(preset.webglVendors),
    webglRenderer: pick(preset.webglRenderers),
    canvasNoise: randomSeed(),
    audioNoise: randomSeed(),
    languages,
    timezone,
    timezoneOffset,
    webrtcPolicy: 'block',
  };
}

/**
 * Validate a FingerprintProfile for internal consistency.
 * Returns an array of error messages (empty = valid).
 */
export function validateProfile(profile: FingerprintProfile): string[] {
  const errors: string[] = [];

  // Platform consistency
  if (profile.platform === 'MacIntel' && profile.oscpu.includes('Windows')) {
    errors.push('macOS platform has Windows oscpu');
  }
  if (profile.platform === 'Win32' && profile.oscpu.includes('Mac')) {
    errors.push('Windows platform has macOS oscpu');
  }
  // UA consistency
  if (profile.platform === 'Win32' && !profile.userAgent.includes('Windows')) {
    errors.push('Windows platform but UA does not contain Windows');
  }
  if (profile.platform === 'MacIntel' && !profile.userAgent.includes('Macintosh')) {
    errors.push('macOS platform but UA does not contain Macintosh');
  }
  // Memory vs concurrency
  if (profile.deviceMemory > profile.hardwareConcurrency * 4) {
    errors.push(`deviceMemory (${profile.deviceMemory}) exceeds hardwareConcurrency*4 (${profile.hardwareConcurrency * 4})`);
  }

  return errors;
}
