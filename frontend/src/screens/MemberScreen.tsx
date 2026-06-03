import { useEffect, useState } from 'react';
import { ActivityIndicator, StyleSheet, Text, View } from 'react-native';

import { getMemberGraph } from '../api/client';
import { Card, Chip, ChipRow, Section, colors } from '../components/ui';
import { buildProfile, MemberProfile } from '../lib/memberProfile';

function pct(rate: any): string | null {
  if (rate == null) return null;
  const n = Number(rate);
  if (Number.isNaN(n)) return String(rate);
  return n <= 1 ? `${Math.round(n * 100)}%` : `${n}%`;
}

export function MemberScreen({ memberId }: { memberId: string }) {
  const [profile, setProfile] = useState<MemberProfile | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    setError('');
    getMemberGraph(memberId)
      .then((g) => setProfile(buildProfile(g)))
      .catch((e) => setError(String(e?.message ?? e)))
      .finally(() => setLoading(false));
  }, [memberId]);

  if (loading) return <ActivityIndicator style={{ marginTop: 24 }} color={colors.accent} />;
  if (error) return <Text style={styles.error}>{error}</Text>;
  if (!profile) return null;

  const m = profile.member;
  const adherence = pct(m.adherence_rate);

  return (
    <View>
      <Card>
        <Text style={styles.name}>{m.name ?? memberId}</Text>
        {!!m.training_age && <Text style={styles.sub}>{m.training_age} · returning to training</Text>}
        {!!m.notes && <Text style={styles.notes}>{m.notes}</Text>}
        {adherence && (
          <View style={styles.adherenceRow}>
            <Chip label={`adherence ${adherence}`} tone={Number(m.adherence_rate) < 0.7 ? 'warn' : 'ok'} />
            {m.adherence_missed_last_week != null && (
              <Chip label={`missed ${m.adherence_missed_last_week} last week`} tone="warn" />
            )}
          </View>
        )}
      </Card>

      {profile.injuries.length > 0 && (
        <Section title="Injuries">
          {profile.injuries.map((inj, i) => (
            <View key={i} style={styles.injury}>
              <Chip label={`${inj.name}${inj.status ? ` · ${inj.status}` : ''}`} tone="danger" />
              {inj.joints.length > 0 && <Text style={styles.affects}>affects: {inj.joints.join(', ')}</Text>}
            </View>
          ))}
          <Text style={styles.excluded}>{profile.excludedExerciseCount} exercises excluded as contraindicated</Text>
        </Section>
      )}

      {profile.goals.length > 0 && (
        <Section title="Goals">
          <ChipRow>{profile.goals.map((g, i) => <Chip key={i} label={g} />)}</ChipRow>
        </Section>
      )}

      {profile.preferences.length > 0 && (
        <Section title="Preferences">
          <ChipRow>
            {profile.preferences.map((p, i) => (
              <Chip key={i} label={p.description} tone={p.kind === 'dislike' ? 'warn' : 'ok'} />
            ))}
          </ChipRow>
        </Section>
      )}

      {profile.equipment.length > 0 && (
        <Section title="Equipment">
          <ChipRow>{profile.equipment.map((e, i) => <Chip key={i} label={e} />)}</ChipRow>
        </Section>
      )}

      {profile.sessions.length > 0 && (
        <Section title="Recent sessions">
          {profile.sessions.map((s, i) => (
            <View key={i} style={styles.sessionRow}>
              <Text style={styles.sessionTitle}>{s.title}</Text>
              <Chip label={s.status ?? ''} tone={s.status === 'completed' ? 'ok' : 'warn'} />
              {!!s.date && <Text style={styles.date}>{s.date}</Text>}
            </View>
          ))}
        </Section>
      )}

      {profile.signals.length > 0 && (
        <Section title="Recent signals">
          {profile.signals.map((s, i) => (
            <View key={i} style={styles.signal}>
              <Text style={styles.signalText}>“{s.text}”</Text>
              {!!s.date && <Text style={styles.date}>{s.date}</Text>}
            </View>
          ))}
        </Section>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  name: { fontSize: 44, fontWeight: '700', color: colors.text },
  sub: { color: colors.muted, marginTop: 4, fontSize: 26 },
  notes: { color: colors.text, marginTop: 12, fontSize: 28, lineHeight: 38 },
  adherenceRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 10, marginTop: 16 },
  injury: { marginBottom: 10 },
  affects: { color: colors.muted, fontSize: 26, marginTop: 6, marginLeft: 2 },
  excluded: { color: colors.danger, fontSize: 26, marginTop: 10 },
  sessionRow: { flexDirection: 'row', alignItems: 'center', gap: 12, marginBottom: 10 },
  sessionTitle: { color: colors.text, fontWeight: '600', minWidth: 240, fontSize: 28 },
  date: { color: colors.muted, fontSize: 24 },
  signal: { marginBottom: 14 },
  signalText: { color: colors.text, fontStyle: 'italic', fontSize: 28, lineHeight: 38 },
  error: { color: colors.danger, marginTop: 24, fontSize: 28 },
});
