import { useAuth } from '@clerk/react'
import { useQuery } from '@tanstack/react-query'
import { useCallback } from 'react'
import type { components } from './api-types'

export type Me = components['schemas']['MeOut']

export const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

/** fetch against the API: adds the Clerk token, parses JSON and turns `{detail}` into ApiError. */
export async function apiFetch<T>(path: string, token: string | null, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  if (token) headers.set('Authorization', `Bearer ${token}`)
  if (init.body && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json')

  const res = await fetch(`${API_URL}${path}`, { ...init, headers })
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    const detail = body?.detail
    // FastAPI validation errors (422) send a list of {msg}.
    const message = typeof detail === 'string' ? detail : (detail?.[0]?.msg ?? `HTTP ${res.status}`)
    throw new ApiError(res.status, message)
  }
  return res.status === 204 ? (undefined as T) : res.json()
}

/** `request(path, init)` bound to the signed-in user's token. */
export function useApi() {
  const { getToken } = useAuth()
  return useCallback(
    async <T,>(path: string, init?: RequestInit) => apiFetch<T>(path, await getToken(), init),
    [getToken],
  )
}

export function useMe() {
  const request = useApi()
  return useQuery({ queryKey: ['me'], queryFn: () => request<Me>('/me') })
}
