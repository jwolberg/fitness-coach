import { useState } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text, TextInput, View } from 'react-native';

import { explain, generateWorkout } from '../api/client';
import type { ExplainResponse, GenerateWorkoutResponse } from '../api/types';
import { Card, Chip, Section, colors } from '../components/ui';
import { WorkoutView } from '../components/WorkoutView';

const QUICK_QUESTIONS = [
  'Why did you skip barbell squats for her?',
  'What should I watch for with this member?',
  'What constraints affected this workout?',
];

function Button({ label, onPress, disabled, primary }: { label: string; onPress: () => void; disabled?: boolean; primary?: boolean }) {
  return (
    <Pressable
      onPress={onPress}
      disabled={disabled}
      style={[styles.btn, primary && styles.btnPrimary, disabled && styles.btnDisabled]}
    >
      <Text style={[styles.btnText, primary && styles.btnTextPrimary]}>{label}</Text>
    </Pressable>
  );
}

export function CoachPanel({ memberId }: { memberId: string }) {
  const [query, setQuery] = useState('Build Maya a lower-body session for this week');
  const [result, setResult] = useState<GenerateWorkoutResponse | null>(null);
  const [genLoading, setGenLoading] = useState(false);
  const [genError, setGenError] = useState('');

  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState<ExplainResponse | null>(null);
  const [expLoading, setExpLoading] = useState(false);
  const [expError, setExpError] = useState('');

  async function onGenerate() {
    setGenLoading(true);
    setGenError('');
    setResult(null);
    try {
      setResult(await generateWorkout(memberId, query));
    } catch (e: any) {
      setGenError(String(e?.message ?? e));
    } finally {
      setGenLoading(false);
    }
  }

  async function ask(q: string) {
    setQuestion(q);
    setExpLoading(true);
    setExpError('');
    setAnswer(null);
    try {
      setAnswer(await explain(memberId, q));
    } catch (e: any) {
      setExpError(String(e?.message ?? e));
    } finally {
      setExpLoading(false);
    }
  }

  return (
    <View>
      <Section title="Ask the coach">
        <TextInput
          value={query}
          onChangeText={setQuery}
          style={styles.input}
          placeholder="e.g. Build a lower-body session for this week"
          multiline
        />
        <Button label={genLoading ? 'Generating…' : 'Generate workout'} onPress={onGenerate} disabled={genLoading} primary />
        {genLoading && <ActivityIndicator style={{ marginTop: 10 }} color={colors.accent} />}
        {!!genError && <Text style={styles.error}>{genError}</Text>}
      </Section>

      {result && <WorkoutView result={result} />}

      <Section title='Ask "why?"'>
        <View style={styles.quickRow}>
          {QUICK_QUESTIONS.map((q) => (
            <Button key={q} label={q} onPress={() => ask(q)} disabled={expLoading} />
          ))}
        </View>
        <TextInput
          value={question}
          onChangeText={setQuestion}
          style={styles.input}
          placeholder="Ask a follow-up question…"
          onSubmitEditing={() => question.trim() && ask(question)}
        />
        <Button label={expLoading ? 'Thinking…' : 'Ask'} onPress={() => question.trim() && ask(question)} disabled={expLoading} />
        {expLoading && <ActivityIndicator style={{ marginTop: 10 }} color={colors.accent} />}
        {!!expError && <Text style={styles.error}>{expError}</Text>}
        {answer && (
          <Card style={{ marginTop: 12 }}>
            <Text style={styles.answer}>{answer.answer}</Text>
            {answer.graph_trace.length > 0 && (
              <>
                <Text style={styles.traceHead}>Graph evidence</Text>
                {answer.graph_trace.map((t, i) => (
                  <Text key={i} style={styles.trace}>
                    {t.subject} —{t.relation}→ {t.object}
                    {t.note ? `  (${t.note})` : ''}
                  </Text>
                ))}
              </>
            )}
          </Card>
        )}
      </Section>
    </View>
  );
}

const styles = StyleSheet.create({
  input: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 8,
    padding: 10,
    minHeight: 40,
    marginBottom: 10,
    backgroundColor: '#fff',
    color: colors.text,
  },
  btn: { borderRadius: 8, paddingVertical: 9, paddingHorizontal: 14, borderWidth: 1, borderColor: colors.border, backgroundColor: '#fff', alignSelf: 'flex-start' },
  btnPrimary: { backgroundColor: colors.accent, borderColor: colors.accent },
  btnDisabled: { opacity: 0.6 },
  btnText: { color: colors.text, fontWeight: '600' },
  btnTextPrimary: { color: '#fff' },
  quickRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginBottom: 10 },
  error: { color: colors.danger, marginTop: 10 },
  answer: { color: colors.text, fontSize: 15, lineHeight: 21 },
  traceHead: { fontSize: 12, fontWeight: '700', color: colors.muted, textTransform: 'uppercase', marginTop: 12, marginBottom: 6 },
  trace: { color: colors.muted, fontSize: 12, fontFamily: 'monospace', marginBottom: 2 },
});
