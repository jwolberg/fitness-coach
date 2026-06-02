// Shape the /api/member/:id/graph response into a renderable profile.

import type { GraphNode, MemberGraphResponse } from '../api/types';

export interface InjuryView {
  name: string;
  status?: string;
  joints: string[];
}

export interface MemberProfile {
  member: Record<string, any>;
  goals: string[];
  preferences: { kind?: string; description: string }[];
  equipment: string[];
  injuries: InjuryView[];
  signals: { text: string; date?: string }[];
  sessions: { title: string; status?: string; date?: string }[];
  excludedExerciseCount: number;
}

function byType(nodes: GraphNode[], type: string): GraphNode[] {
  return nodes.filter((n) => n.type === type);
}

export function buildProfile(graph: MemberGraphResponse): MemberProfile {
  const { nodes, edges } = graph;
  const memberNode = byType(nodes, 'Member')[0];
  const nodeById = new Map(nodes.map((n) => [n.id, n]));

  const injuries: InjuryView[] = byType(nodes, 'Injury').map((inj) => {
    const joints = edges
      .filter((e) => e.source === inj.id && e.type === 'AFFECTS_JOINT')
      .map((e) => nodeById.get(e.target)?.label ?? '')
      .filter(Boolean);
    return { name: inj.properties.name ?? inj.label ?? 'Injury', status: inj.properties.status, joints };
  });

  const sessions = byType(nodes, 'WorkoutSession')
    .map((s) => ({ title: s.properties.title ?? 'Session', status: s.properties.status, date: s.properties.date }))
    .sort((a, b) => (b.date ?? '').localeCompare(a.date ?? ''));

  return {
    member: memberNode?.properties ?? {},
    goals: byType(nodes, 'Goal').map((g) => g.properties.description ?? g.label ?? '').filter(Boolean),
    preferences: byType(nodes, 'Preference').map((p) => ({
      kind: p.properties.kind,
      description: p.properties.description ?? p.label ?? '',
    })),
    equipment: byType(nodes, 'Equipment').map((e) => e.properties.name ?? e.label ?? '').filter(Boolean),
    injuries,
    signals: byType(nodes, 'ContextSignal').map((c) => ({ text: c.properties.text ?? c.label ?? '', date: c.properties.date })),
    sessions,
    excludedExerciseCount: byType(nodes, 'Exercise').length,
  };
}
