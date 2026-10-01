import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError, apiFetch } from './api'

function mockFetch(status: number, body: string, contentType = 'application/json') {
  const fn = vi.fn(async () => new Response(status === 204 ? null : body, { status, headers: { 'Content-Type': contentType } }))
  vi.stubGlobal('fetch', fn)
  return fn
}

afterEach(() => vi.unstubAllGlobals())

describe('apiFetch', () => {
  it('sends the bearer token and parses JSON', async () => {
    const fetch = mockFetch(200, '{"ok":true}')
    expect(await apiFetch('/health', 'tok')).toEqual({ ok: true })
    const [url, init] = fetch.mock.calls[0] as unknown as [string, RequestInit]
    expect(url).toBe('http://localhost:8000/health')
    expect(new Headers(init.headers).get('Authorization')).toBe('Bearer tok')
  })

  it('omits Authorization when there is no token', async () => {
    const fetch = mockFetch(200, '{}')
    await apiFetch('/voices', null)
    const [, init] = fetch.mock.calls[0] as unknown as [string, RequestInit]
    expect(new Headers(init.headers).has('Authorization')).toBe(false)
  })

  it('turns {detail} errors into ApiError', async () => {
    mockFetch(409, '{"detail":"An episode is already being generated"}')
    const err = await apiFetch('/episodes', 'tok', { method: 'POST' }).catch((e: unknown) => e)
    expect(err).toBeInstanceOf(ApiError)
    expect(err).toMatchObject({ status: 409, message: 'An episode is already being generated' })
  })

  it('falls back to the status text for non-JSON errors', async () => {
    mockFetch(502, '<html>Bad gateway</html>', 'text/html')
    await expect(apiFetch('/me', 'tok')).rejects.toMatchObject({ status: 502, message: 'HTTP 502' })
  })

  it('returns undefined for 204', async () => {
    mockFetch(204, '')
    expect(await apiFetch('/x', 'tok', { method: 'DELETE' })).toBeUndefined()
  })
})
