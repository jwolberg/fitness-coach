// Typed contracts mirroring the backend Pydantic schemas (PRD §7.9).
// Workout/explanation content is intentionally loose (backend leaves it open).

export interface GraphTraceEntry {
  subject: string;
  relation: string;
  object: string;
  note?: string | null;
}

export interface SemanticMatch {
  id?: string | null;
  label?: string | null;
  type?: string | null;
  score: number;
}

export interface Injury {
  id?: string;
  name?: string;
  description?: string;
  status?: string;
  joint?: string;
}

export interface SafeCandidate {
  id: string;
  name: string;
  priority_tier?: number;
  score?: number;
}

export interface ExcludedExercise {
  id: string;
  name: string;
  reason: string;
  joints: string[];
}

export interface RetrievedContext {
  member: Record<string, any>;
  goals: Record<string, any>[];
  preferences: Record<string, any>[];
  equipment: string[];
  injuries: Injury[];
  recent_sessions: Record<string, any>[];
  context_signals: Record<string, any>[];
  safe_candidates: SafeCandidate[];
  excluded_exercises: ExcludedExercise[];
}

export interface RetrieveResponse {
  member_id: string;
  retrieved_context: RetrievedContext;
  graph_trace: GraphTraceEntry[];
  semantic_matches: SemanticMatch[];
}

export interface GraphNode {
  id: string;
  type?: string | null;
  label?: string | null;
  properties: Record<string, any>;
}

export interface GraphEdge {
  source: string;
  target: string;
  type: string;
}

export interface MemberGraphResponse {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface WorkoutExercise {
  exercise_id?: string;
  name?: string;
  sets?: number;
  reps?: string;
  rest?: string;
  intensity?: string;
  substitution?: string;
  notes?: string;
}

export interface Workout {
  title?: string;
  goal?: string;
  warm_up?: string[];
  exercises?: WorkoutExercise[];
  intensity_guidance?: string;
  rest_guidance?: string;
  notes?: string;
  insufficient_safe_options?: boolean;
}

export interface SafetyValidation {
  passed: boolean;
  issues: Record<string, any>[];
  repaired: boolean;
  used_fallback: boolean;
}

export interface GenerateWorkoutResponse {
  workout: Workout;
  explanation: { answer?: string; graph_trace?: GraphTraceEntry[] };
  safety_validation: SafetyValidation;
  status?: string | null;
}

export interface ExplainResponse {
  answer: string;
  graph_trace: GraphTraceEntry[];
}
