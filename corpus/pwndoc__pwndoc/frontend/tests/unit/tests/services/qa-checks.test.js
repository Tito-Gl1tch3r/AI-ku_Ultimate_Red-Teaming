import { describe, expect, it } from 'vitest'
import {
    hasAnyQaCheckEnabled,
    hasAnyProgrammaticQaCheckEnabled,
    hasAnyAiQaCheckEnabled,
    canRunProgrammaticQa,
    canRunAiQa,
    canAccessQa
} from '@/services/qa-checks'

describe('qa-checks service', () => {
    it('returns true when at least one check is enabled', () => {
        expect(hasAnyQaCheckEnabled({ completeness: false, references: true })).toBe(true)
    })

    it('returns false when every check is disabled', () => {
        expect(hasAnyQaCheckEnabled({
            completeness: false,
            references: false,
            imageCaptions: false,
            duplicates: false,
            aiDuplicates: false,
            aiUnlinkedTranslations: false,
            redaction: false,
            customer: false,
            instructions: false
        })).toBe(false)
    })

    it('treats missing keys as enabled', () => {
        expect(hasAnyQaCheckEnabled({})).toBe(true)
    })

    it('detects when all built-in checks are disabled', () => {
        expect(hasAnyProgrammaticQaCheckEnabled({
            completeness: false,
            references: false,
            imageCaptions: false,
            duplicates: false,
            redaction: true
        })).toBe(false)
        expect(hasAnyAiQaCheckEnabled({
            completeness: false,
            references: false,
            imageCaptions: false,
            duplicates: false,
            redaction: true
        })).toBe(true)
    })

    describe('permission-aware gating', () => {
        const aiEnabledSettings = { ai: { public: { enabled: true, qaChecks: {} } } }
        const aiDisabledSettings = { ai: { public: { enabled: false, qaChecks: {} } } }
        // AI off AND every check off — nothing is runnable regardless of permission.
        const nothingRunnableSettings = {
            ai: {
                public: {
                    enabled: false,
                    qaChecks: {
                        completeness: false, references: false, imageCaptions: false, duplicates: false,
                        aiDuplicates: false, aiUnlinkedTranslations: false, redaction: false, customer: false, instructions: false
                    }
                }
            }
        }
        const programmaticOnlySettings = {
            ai: {
                public: {
                    enabled: true,
                    qaChecks: {
                        completeness: true, references: false, imageCaptions: false, duplicates: false,
                        aiDuplicates: false, aiUnlinkedTranslations: false, redaction: false, customer: false, instructions: false
                    }
                }
            }
        }
        const aiOnlySettings = {
            ai: {
                public: {
                    enabled: true,
                    qaChecks: {
                        completeness: false, references: false, imageCaptions: false, duplicates: false,
                        aiDuplicates: true, aiUnlinkedTranslations: false, redaction: false, customer: false, instructions: false
                    }
                }
            }
        }

        it('canRunProgrammaticQa needs the base permission and an enabled built-in check (ai-qa does NOT grant it)', () => {
            // base permission grants built-in checks
            expect(canRunProgrammaticQa(true, aiEnabledSettings)).toBe(true)
            // no base permission
            expect(canRunProgrammaticQa(false, aiEnabledSettings)).toBe(false)
            // has base permission but no built-in check enabled
            expect(canRunProgrammaticQa(true, aiOnlySettings)).toBe(false)
        })

        it('canRunAiQa needs the AI permission, AI enabled, and an enabled AI check', () => {
            expect(canRunAiQa(true, aiEnabledSettings)).toBe(true)
            expect(canRunAiQa(false, aiEnabledSettings)).toBe(false)
            expect(canRunAiQa(true, aiDisabledSettings)).toBe(false)
            expect(canRunAiQa(true, programmaticOnlySettings)).toBe(false)
        })

        it('canAccessQa is true if the user can read OR run at least one check', () => {
            // read-only user: can access even when nothing is runnable
            expect(canAccessQa(true, false, false, nothingRunnableSettings)).toBe(true)
            // base-QA user with only built-in checks on
            expect(canAccessQa(false, true, false, programmaticOnlySettings)).toBe(true)
            // AI-QA user with only AI checks on
            expect(canAccessQa(false, false, true, aiOnlySettings)).toBe(true)
            // AI-QA user, AI disabled, only built-in checks on: cannot run AI, has no base perm
            expect(canAccessQa(false, false, true, programmaticOnlySettings)).toBe(false)
            // no permissions at all
            expect(canAccessQa(false, false, false, aiEnabledSettings)).toBe(false)
        })
    })
})
