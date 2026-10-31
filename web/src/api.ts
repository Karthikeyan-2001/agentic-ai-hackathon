import type {
  AnswerResponse,
  ClassSummary,
  DemoAccount,
  LessonPlan,
  NextResponse,
  Session,
  StudentState,
} from './types'

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

let token: string | null = null
let onSignedOut: () => void = () => {}

export function setAuthToken(value: string | null) {
  token = value
}

export function setSignedOutHandler(handler: () => void) {
  onSignedOut = handler
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  })
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    const detail = typeof body.detail === 'string' ? body.detail : `Request failed (${response.status})`
    if (response.status === 401 && token) onSignedOut()
    throw new ApiError(response.status, detail)
  }
  return response.json()
}

export const api = {
  demoAccounts: () => request<DemoAccount[]>('/auth/demo-accounts'),
  login: (username: string, password: string) =>
    request<Session>('/auth/login', { method: 'POST', body: JSON.stringify({ username, password }) }),
  logout: () => request<{ status: string }>('/auth/logout', { method: 'POST' }),
  next: (id: string) => request<NextResponse>(`/students/${id}/next`),
  state: (id: string) => request<StudentState>(`/students/${id}/state`),
  answer: (
    id: string,
    body: { question_id: string; option_id: string; reasoning: string; confidence_tap: 'sure' | 'not_sure' },
  ) => request<AnswerResponse>(`/students/${id}/answers`, { method: 'POST', body: JSON.stringify(body) }),
  advanceClock: (days: number) =>
    request<{ offset_days: number }>('/clock/advance', { method: 'POST', body: JSON.stringify({ days }) }),
  resetDemo: () => request<{ status: string }>('/demo/reset', { method: 'POST' }),
  classSummary: () => request<ClassSummary>('/class/summary'),
  classPlan: () => request<LessonPlan>('/class/plan', { method: 'POST' }),
}

export const percent = (value: number) => `${Math.round(value * 100)}%`
