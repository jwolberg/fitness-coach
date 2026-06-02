// Typed API client for the coaching backend.
// Base URL is configurable via EXPO_PUBLIC_API_URL (defaults to localhost:8000).

import type {
  ExplainResponse,
  GenerateWorkoutResponse,
  MemberGraphResponse,
  RetrieveResponse,
} from './types';

export const API_URL =
  (process.env.EXPO_PUBLIC_API_URL as string | undefined) ?? 'http://localhost:8000';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => '');
    throw new Error(`API ${res.status} ${path}: ${detail.slice(0, 200)}`);
  }
  return (await res.json()) as T;
}

export function getHealth(): Promise<{ status: string }> {
  return request('/health');
}

export function getMemberGraph(memberId: string): Promise<MemberGraphResponse> {
  return request(`/api/member/${encodeURIComponent(memberId)}/graph`);
}

export function retrieve(memberId: string, query: string): Promise<RetrieveResponse> {
  return request('/api/retrieve', {
    method: 'POST',
    body: JSON.stringify({ member_id: memberId, query }),
  });
}

export function generateWorkout(
  memberId: string,
  query: string,
): Promise<GenerateWorkoutResponse> {
  return request('/api/generate/workout', {
    method: 'POST',
    body: JSON.stringify({ member_id: memberId, query }),
  });
}

export function explain(
  memberId: string,
  question: string,
  recommendationId?: string,
): Promise<ExplainResponse> {
  return request('/api/explain', {
    method: 'POST',
    body: JSON.stringify({
      member_id: memberId,
      question,
      recommendation_id: recommendationId,
    }),
  });
}
