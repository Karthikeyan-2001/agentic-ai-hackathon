export type ErrorType = 'none' | 'misconception' | 'slip' | 'gap' | 'unclear'

export type Role = 'student' | 'teacher'

export interface Session {
  token: string
  username: string
  role: Role
  student_id: string | null
  display_name: string
}

export interface DemoAccount {
  username: string
  password: string
  role: Role
  student_id: string | null
  display_name: string
}

export interface PublicQuestion {
  id: string
  concept_id: string
  concept_name: string
  stem: string
  options: { id: string; text: string }[]
}

export interface NextResponse {
  status: 'question' | 'caught_up'
  question: PublicQuestion | null
  rule: number
  reason: string
  hypotheses: [string, number][]
}

export interface TraceEntry {
  step: 'check' | 'diagnose' | 'validate' | 'update' | 'decide'
  detail: string
  data: Record<string, unknown>
}

export interface AnswerResponse {
  correct: boolean
  correct_option_id: string
  diagnosis: {
    error_type: ErrorType
    misconception_id: string | null
    misconception_description: string | null
    first_wrong_step: string | null
    evidence_quote: string | null
    confidence: number
  }
  diagnosis_status: 'ok' | 'cached' | 'failed'
  mastery_changes: { id: string; name: string; before: number; after: number }[]
  misconception_changes: { id: string; description: string; before: number; after: number }[]
  trace: TraceEntry[]
  next_reason: string | null
  caught_up: boolean
}

export interface ConceptView {
  id: string
  name: string
  chapter: string
  prerequisites: string[]
  mastery: number
  displayed_mastery: number
  recall: number
  assessed: boolean
  has_questions: boolean
}

export interface StudentState {
  concepts: ConceptView[]
  misconceptions: { id: string; description: string; probability: number; status: string }[]
  due_reviews: { kind: 'concept' | 'misconception'; id: string; name: string; recall: number }[]
  offset_days: number
  answer_count: number
  diagnostic_complete: boolean
}

export interface ClassSummary {
  overview: {
    student_count: number
    average_mastery: number | null
    students_with_active_misconception: number
    reviews_due: number
  }
  concept_gaps: {
    concept_id: string
    name: string
    average_mastery: number | null
    below_40_count: number
    assessed_count: number
  }[]
  reviews_by_concept: { concept_id: string; name: string; student_count: number }[]
  heatmap: {
    concepts: { id: string; name: string }[]
    students: { id: string; name: string; mastery: Record<string, number | null> }[]
  }
  groups: { misconception_id: string; description: string; students: { id: string; name: string }[] }[]
  root_causes: { concept_id: string; name: string; student_count: number; affects: string[] }[]
  calibration_flags: {
    question_id: string
    stem: string
    predicted_elo: number
    current_elo: number
    attempts: number
    direction: 'harder' | 'easier'
  }[]
  student_count: number
  is_simulated: boolean
  offset_days: number
}

export interface LessonPlan {
  title: string
  board_demo: string
  check_question_id: string
  check_question_stem: string
  misconception_id: string
  misconception_description: string
  student_count: number
}
