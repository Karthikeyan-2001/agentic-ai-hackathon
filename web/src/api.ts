import type { AnswerResponse, ClassSummary, LessonPlan, NextResponse, Student, StudentState } from './types'

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    const detail = typeof body.detail === 'string' ? body.detail : `Request failed (${response.status})`
    throw new ApiError(response.status, detail)
  }
  return response.json()
}

export const api = {
  students: () => request<Student[]>('/students'),
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
