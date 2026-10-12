import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

const { mockUserStore } = vi.hoisted(() => ({
  mockUserStore: {
    clearUser: vi.fn()
  }
}))
vi.mock('src/stores/user', () => ({
  useUserStore: vi.fn(() => mockUserStore)
}))

import bootAxios, { api } from '@/boot/axios'

describe('boot/axios error interceptor', () => {
  let router

  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    router = { push: vi.fn() }
    bootAxios({ app: { config: { globalProperties: {} } }, router })
  })

  const getRejectedHandler = () => {
    const handlers = api.interceptors.response.handlers
    return handlers[handlers.length - 1].rejected
  }

  it('rejects a response-less error (e.g. a cancelled request) without throwing', async () => {
    const rejected = getRejectedHandler()
    const abortError = { message: 'canceled', code: 'ERR_CANCELED', config: { url: '/ai/generate' } }

    await expect(rejected(abortError)).rejects.toBe(abortError)
    expect(router.push).not.toHaveBeenCalled()
    expect(mockUserStore.clearUser).not.toHaveBeenCalled()
  })

  it('rejects a network error with no response without throwing', async () => {
    const rejected = getRejectedHandler()
    const networkError = { message: 'Network Error', config: { url: '/ai/generate' } }

    await expect(rejected(networkError)).rejects.toBe(networkError)
  })

  it('still clears the user on a 401 from the refresh-token endpoint', async () => {
    const rejected = getRejectedHandler()
    const error = {
      response: { status: 401 },
      config: { url: '/api/users/refreshtoken' }
    }

    await expect(rejected(error)).rejects.toBe(error)
    expect(mockUserStore.clearUser).toHaveBeenCalled()
  })

  it('propagates non-401 errors with a response unchanged', async () => {
    const rejected = getRejectedHandler()
    const error = {
      response: { status: 500 },
      config: { url: '/ai/generate' }
    }

    await expect(rejected(error)).rejects.toBe(error)
  })
})
