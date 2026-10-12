import type { FingerprintProfile } from '@shared/types';
import type { FingerprintProfilesRepo } from '../db/repositories';
import { generateProfile } from './profile-generator';

/**
 * ProfileStore — High-level interface for managing fingerprint profiles.
 * Handles get-or-create logic and delegates persistence to the repository.
 */
export class ProfileStore {
  constructor(private repo: FingerprintProfilesRepo) {}

  /**
   * Get the profile for a session. If none exists, auto-generate one.
   */
  getOrCreate(sessionId: string): FingerprintProfile {
    const existing = this.repo.findBySessionId(sessionId);
    if (existing) return existing;
    const profile = generateProfile(sessionId);
    this.repo.upsert(sessionId, profile);
    return profile;
  }

  /**
   * Get the profile for a session. Returns null if none exists.
   */
  get(sessionId: string): FingerprintProfile | null {
    return this.repo.findBySessionId(sessionId);
  }

  /**
   * Update (or create) a profile for a session.
   */
  update(profile: FingerprintProfile): void {
    this.repo.upsert(profile.sessionId, profile);
  }

  /**
   * Regenerate a random profile for a session, replacing any existing one.
   */
  regenerate(sessionId: string): FingerprintProfile {
    const profile = generateProfile(sessionId);
    this.repo.upsert(sessionId, profile);
    return profile;
  }

  /**
   * Delete the profile for a session.
   */
  delete(sessionId: string): void {
    this.repo.delete(sessionId);
  }
}
