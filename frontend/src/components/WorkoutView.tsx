import { StyleSheet, Text, View } from 'react-native';

import type { GenerateWorkoutResponse } from '../api/types';
import { Card, Chip, colors } from './ui';

function SafetyBadge({ sv, status }: { sv: GenerateWorkoutResponse['safety_validation']; status?: string | null }) {
  if (status === 'insufficient_context' || sv.used_fallback) {
    return <Chip label="safety: safe fallback (insufficient options)" tone="warn" />;
  }
  if (sv.repaired) return <Chip label="safety: repaired" tone="warn" />;
  if (sv.passed) return <Chip label="safety: passed" tone="ok" />;
  return <Chip label="safety: review" tone="danger" />;
}

export function WorkoutView({ result }: { result: GenerateWorkoutResponse }) {
  const w = result.workout ?? {};
  const sv = result.safety_validation;
  return (
    <Card>
      <View style={styles.headerRow}>
        <Text style={styles.title}>{w.title ?? 'Workout'}</Text>
        <SafetyBadge sv={sv} status={result.status} />
      </View>
      {!!w.goal && <Text style={styles.goal}>{w.goal}</Text>}
      {w.insufficient_safe_options && (
        <Text style={styles.warn}>⚠ Limited safe options for the requested focus — see notes.</Text>
      )}

      {!!w.warm_up?.length && (
        <>
          <Text style={styles.subhead}>Warm-up</Text>
          {w.warm_up.map((x, i) => (
            <Text key={i} style={styles.bullet}>• {x}</Text>
          ))}
        </>
      )}

      <Text style={styles.subhead}>Exercises</Text>
      {(w.exercises ?? []).length === 0 && <Text style={styles.muted}>No exercises.</Text>}
      {(w.exercises ?? []).map((ex, i) => (
        <View key={i} style={styles.exercise}>
          <Text style={styles.exName}>{ex.name}</Text>
          <Text style={styles.exMeta}>
            {[ex.sets != null && ex.reps ? `${ex.sets} × ${ex.reps}` : null, ex.rest ? `rest ${ex.rest}` : null, ex.intensity]
              .filter(Boolean)
              .join('  ·  ')}
          </Text>
          {!!ex.notes && <Text style={styles.exNotes}>{ex.notes}</Text>}
          {!!ex.substitution && <Text style={styles.exNotes}>sub: {ex.substitution}</Text>}
        </View>
      ))}

      {!!w.intensity_guidance && <Text style={styles.guide}>Intensity: {w.intensity_guidance}</Text>}
      {!!w.rest_guidance && <Text style={styles.guide}>Rest: {w.rest_guidance}</Text>}
      {!!w.notes && <Text style={styles.notes}>{w.notes}</Text>}

      {sv.issues?.length > 0 && (
        <Text style={styles.issues}>Validator caught {sv.issues.length} issue(s) and corrected the plan.</Text>
      )}
    </Card>
  );
}

const styles = StyleSheet.create({
  headerRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 10 },
  title: { fontSize: 34, fontWeight: '700', color: colors.text },
  goal: { color: colors.muted, marginTop: 4, marginBottom: 8, fontSize: 26, lineHeight: 34 },
  warn: { color: '#9a6700', backgroundColor: colors.warnBg, padding: 12, borderRadius: 10, marginVertical: 8, fontSize: 26, lineHeight: 34 },
  subhead: { fontSize: 22, fontWeight: '700', color: colors.muted, textTransform: 'uppercase', marginTop: 18, marginBottom: 8 },
  bullet: { color: colors.text, marginBottom: 4, fontSize: 28, lineHeight: 38 },
  exercise: { borderTopWidth: 1, borderTopColor: colors.border, paddingVertical: 12 },
  exName: { color: colors.text, fontWeight: '600', fontSize: 28 },
  exMeta: { color: colors.muted, fontSize: 26, marginTop: 4 },
  exNotes: { color: colors.muted, fontSize: 24, marginTop: 4, fontStyle: 'italic' },
  muted: { color: colors.muted, fontSize: 28 },
  guide: { color: colors.text, marginTop: 12, fontSize: 26, lineHeight: 34 },
  notes: { color: colors.text, marginTop: 14, fontSize: 28, lineHeight: 38 },
  issues: { color: colors.accent, marginTop: 14, fontSize: 26 },
});
