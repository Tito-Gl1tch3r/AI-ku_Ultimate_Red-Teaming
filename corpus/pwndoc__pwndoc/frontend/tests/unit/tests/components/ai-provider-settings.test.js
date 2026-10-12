import { describe, it, expect, vi } from 'vitest'
import { createTestWrapper } from '../../test-utils'
import AiProviderSettings from '@/components/ai-provider-settings.vue'

vi.mock('@/services/ai', () => ({
  default: {
    testProvider: vi.fn()
  }
}))

import AiService from '@/services/ai'

function buildSettings() {
  return {
    ai: {
      public: {
        defaultProvider: 'openai',
        allowedProviders: []
      },
      private: {
        openaiApiKey: '',
        openaiApiKeyConfigured: false,
        openaiBaseUrl: 'https://api.openai.com/v1',
        openaiModel: 'gpt-5.4-mini',
        anthropicApiKey: '',
        anthropicApiKeyConfigured: false,
        anthropicBaseUrl: 'https://api.anthropic.com/v1',
        anthropicModel: 'claude-opus-4-8',
        anthropicVersion: '2023-06-01',
        deepseekApiKey: '',
        deepseekApiKeyConfigured: false,
        deepseekBaseUrl: 'https://api.deepseek.com/v1',
        deepseekModel: 'deepseek-v4-flash',
        ollamaApiKey: '',
        ollamaApiKeyConfigured: false,
        ollamaBaseUrl: 'http://localhost:11434/v1',
        ollamaModel: 'llama3.1',
        bedrockApiKey: '',
        bedrockApiKeyConfigured: false,
        bedrockAccessKeyId: '',
        bedrockAccessKeyIdConfigured: false,
        bedrockSecretAccessKey: '',
        bedrockSecretAccessKeyConfigured: false,
        bedrockSessionToken: '',
        bedrockSessionTokenConfigured: false,
        bedrockRegion: 'us-east-1',
        bedrockModel: 'global.anthropic.claude-opus-4-8'
      }
    }
  }
}

const messages = {
  'en-US': {
    aiIntegration: {
      provider: {
        defaultBadge: 'Default',
        setDefaultLabel: 'Set as default provider',
        setDefaultHint: 'Used when a request does not specify a provider.',
        configuredHint: 'This provider is configured',
        allowUsersLabel: 'Allow users to select this provider',
        allowUsersHint: 'When enabled, users can pick this provider.',
        openaiBaseUrl: 'OpenAI Base URL',
        openaiModel: 'OpenAI Model',
        openaiApiKey: 'OpenAI API Key',
        testConnection: 'Test connection',
        testSuccess: 'Connection successful',
        testSuccessWithModel: 'Connection successful (model: {model})',
        testFailed: 'Connection failed'
      }
    }
  }
}

function createWrapper(settings = buildSettings()) {
  return createTestWrapper(AiProviderSettings, {
    messages,
    props: {
      settings,
      canEdit: true
    }
  })
}

describe('AiProviderSettings test connection', () => {
  it('sends the current form values (including an unsaved API key) to the test endpoint', async () => {
    AiService.testProvider.mockResolvedValue({ data: { datas: { ok: true, provider: 'openai', model: 'gpt-5.4-mini' } } })
    const wrapper = createWrapper()
    wrapper.vm.openaiApiKeyInput = 'sk-newly-typed-key'

    await wrapper.vm.testConnection('openai')

    expect(AiService.testProvider).toHaveBeenCalledWith(expect.objectContaining({
      provider: 'openai',
      openaiApiKey: 'sk-newly-typed-key',
      openaiBaseUrl: 'https://api.openai.com/v1',
      openaiModel: 'gpt-5.4-mini'
    }))
    expect(wrapper.vm.testResults.openai.ok).toBe(true)
    expect(wrapper.vm.testResults.openai.message).toContain('gpt-5.4-mini')
  })

  it('shows a clear inline error when the test fails', async () => {
    AiService.testProvider.mockRejectedValue({
      response: { data: { datas: 'OpenAI provider is not configured. Set API key.' } }
    })
    const wrapper = createWrapper()

    await wrapper.vm.testConnection('openai')

    expect(wrapper.vm.testResults.openai.ok).toBe(false)
    expect(wrapper.vm.testResults.openai.message).toBe('OpenAI provider is not configured. Set API key.')
  })

  it('clears the loading state after the test completes', async () => {
    AiService.testProvider.mockResolvedValue({ data: { datas: { ok: true, model: 'gpt-5.4-mini' } } })
    const wrapper = createWrapper()

    const promise = wrapper.vm.testConnection('openai')
    expect(wrapper.vm.testingProvider).toBe('openai')
    await promise

    expect(wrapper.vm.testingProvider).toBeNull()
  })
})

describe('AiProviderSettings masked secret sentinel', () => {
  // Pinned to the literal value, not just re-derived, so a drift from the backend's
  // independent copy in settings-secrets.js is caught here (see the comment on
  // MASKED_SECRET in ai-provider-settings.vue).
  it('masks a configured secret with the sentinel the backend expects back on save', () => {
    const wrapper = createWrapper()

    expect(wrapper.vm.maskedValue(true)).toBe('••••••••••••••••')
    expect(wrapper.vm.maskedValue(false)).toBe('')
  })

  it('pre-fills each configured secret field with the masked sentinel on mount', () => {
    const settings = buildSettings()
    settings.ai.private.openaiApiKeyConfigured = true

    const wrapper = createWrapper(settings)

    expect(wrapper.vm.openaiApiKeyInput).toBe('••••••••••••••••')
  })
})

describe('AiProviderSettings configured badge', () => {
  it('reports a provider as configured once its API key is stored', () => {
    const settings = buildSettings()
    settings.ai.private.anthropicApiKeyConfigured = true
    const wrapper = createWrapper(settings)

    expect(wrapper.vm.isProviderConfigured('anthropic')).toBe(true)
    expect(wrapper.vm.isProviderConfigured('openai')).toBe(false)
  })

  it('reports bedrock configured via IAM credentials without an API key', () => {
    const settings = buildSettings()
    settings.ai.private.bedrockAccessKeyIdConfigured = true
    settings.ai.private.bedrockSecretAccessKeyConfigured = true
    const wrapper = createWrapper(settings)

    expect(wrapper.vm.isProviderConfigured('bedrock')).toBe(true)
  })
})

describe('AiProviderSettings default provider', () => {
  it('reports which provider is the current default', () => {
    const wrapper = createWrapper()

    expect(wrapper.vm.isDefaultProvider('openai')).toBe(true)
    expect(wrapper.vm.isDefaultProvider('anthropic')).toBe(false)
  })

  it('switches the default and drops the new default from allowedProviders', () => {
    const settings = buildSettings()
    settings.ai.public.allowedProviders = ['anthropic']
    const wrapper = createWrapper(settings)

    wrapper.vm.setDefaultProvider('anthropic')

    expect(settings.ai.public.defaultProvider).toBe('anthropic')
    // The new default is implicitly allowed, so it is removed from the explicit list.
    expect(settings.ai.public.allowedProviders).not.toContain('anthropic')
    // It is still reported as allowed (implicitly, as the default).
    expect(wrapper.vm.isProviderAllowed('anthropic')).toBe(true)
  })
})

describe('AiProviderSettings allow-list', () => {
  it('always reports the default provider as allowed and locks its toggle', () => {
    const wrapper = createWrapper()

    expect(wrapper.vm.isProviderAllowed('openai')).toBe(true)
    expect(wrapper.vm.allowToggleDisabled('openai')).toBe(true)
  })

  it('disables the allow toggle for a provider that is not configured', () => {
    const wrapper = createWrapper()

    expect(wrapper.vm.allowToggleDisabled('anthropic')).toBe(true)
  })

  it('adds and removes a configured provider from allowedProviders', () => {
    const settings = buildSettings()
    settings.ai.private.anthropicApiKeyConfigured = true
    const wrapper = createWrapper(settings)

    wrapper.vm.setProviderAllowed('anthropic', true)
    expect(settings.ai.public.allowedProviders).toContain('anthropic')
    expect(wrapper.vm.isProviderAllowed('anthropic')).toBe(true)

    wrapper.vm.setProviderAllowed('anthropic', false)
    expect(settings.ai.public.allowedProviders).not.toContain('anthropic')
    expect(wrapper.vm.isProviderAllowed('anthropic')).toBe(false)
  })
})
