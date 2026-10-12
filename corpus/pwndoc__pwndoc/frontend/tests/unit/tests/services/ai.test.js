import { describe, it, expect, beforeEach, vi } from 'vitest'

vi.mock('boot/axios', () => ({
  api: {
    get: vi.fn(),
    defaults: { baseURL: 'https://example.test/api' }
  }
}))

import AiService from '@/services/ai'

const encoder = new TextEncoder()

// Fakes a fetch() Response whose body streams the given raw text chunks one at a time,
// matching the ReadableStreamDefaultReader contract streamGenerateFieldDraft consumes.
function buildStreamResponse(chunks, { ok = true, status = 200, json } = {}) {
  let index = 0
  return {
    ok,
    status,
    body: {
      getReader: () => ({
        read: async () => {
          if (index >= chunks.length)
            return { done: true, value: undefined }
          const value = encoder.encode(chunks[index])
          index += 1
          return { done: false, value }
        }
      })
    },
    json: json || (async () => ({}))
  }
}

describe('AiService.streamGenerateFieldDraft', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    global.fetch = vi.fn()
  })

  it('posts JSON to ai/generate with same-origin credentials and the abort signal', async () => {
    global.fetch.mockResolvedValue(buildStreamResponse([]))
    const signal = new AbortController().signal

    await AiService.streamGenerateFieldDraft({ userPrompt: 'hi' }, { signal })

    expect(global.fetch).toHaveBeenCalledWith('https://example.test/api/ai/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify({ userPrompt: 'hi' }),
      signal
    })
  })

  it('parses SSE events and invokes onEvent for each one in order', async () => {
    const chunks = [
      'event: heartbeat\ndata: {}\n\n',
      'event: done\ndata: {"draft":"<p>ok</p>","reply":""}\n\n'
    ]
    global.fetch.mockResolvedValue(buildStreamResponse(chunks))
    const events = []

    await AiService.streamGenerateFieldDraft({ userPrompt: 'hi' }, { onEvent: (event) => events.push(event) })

    expect(events).toEqual([
      { event: 'heartbeat', data: {} },
      { event: 'done', data: { draft: '<p>ok</p>', reply: '' } }
    ])
  })

  it('reassembles an SSE event split across multiple stream chunks', async () => {
    const chunks = ['event: don', 'e\ndata: {"draft":"ok"}\n\n']
    global.fetch.mockResolvedValue(buildStreamResponse(chunks))
    const events = []

    await AiService.streamGenerateFieldDraft({}, { onEvent: (event) => events.push(event) })

    expect(events).toEqual([{ event: 'done', data: { draft: 'ok' } }])
  })

  it('skips a malformed SSE block instead of throwing', async () => {
    const chunks = ['event: done\ndata: {not json}\n\n', 'event: done\ndata: {"draft":"ok"}\n\n']
    global.fetch.mockResolvedValue(buildStreamResponse(chunks))
    const events = []

    await AiService.streamGenerateFieldDraft({}, { onEvent: (event) => events.push(event) })

    expect(events).toEqual([{ event: 'done', data: { draft: 'ok' } }])
  })

  it('flags a 502/504 response as a timeout instead of surfacing a raw HTTP status', async () => {
    global.fetch.mockResolvedValue({
      ok: false,
      status: 504,
      json: async () => { throw new Error('no body to parse') }
    })

    await expect(AiService.streamGenerateFieldDraft({})).rejects.toMatchObject({ isTimeout: true })
  })

  it('surfaces the server-provided message for a non-timeout error response', async () => {
    global.fetch.mockResolvedValue({
      ok: false,
      status: 422,
      json: async () => ({ datas: 'Missing required parameter: field' })
    })

    await expect(AiService.streamGenerateFieldDraft({})).rejects.toThrow('Missing required parameter: field')
  })

  it('rejects when the environment has no streaming body support', async () => {
    global.fetch.mockResolvedValue({ ok: true, status: 200, body: null })

    await expect(AiService.streamGenerateFieldDraft({})).rejects.toThrow(/streaming/i)
  })
})
