import { useRef, useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';

import { explain, generateWorkout } from '../api/client';
import type { ExplainResponse, GenerateWorkoutResponse } from '../api/types';
import { colors } from '../components/ui';
import { WorkoutView } from '../components/WorkoutView';

type Msg =
  | { id: number; role: 'user'; text: string }
  | { id: number; role: 'assistant'; kind: 'text'; text: string }
  | { id: number; role: 'assistant'; kind: 'workout'; result: GenerateWorkoutResponse }
  | { id: number; role: 'assistant'; kind: 'explanation'; answer: ExplainResponse }
  | { id: number; role: 'assistant'; kind: 'loading' }
  | { id: number; role: 'assistant'; kind: 'error'; text: string };

const SUGGESTIONS = [
  'Build a lower-body session for this week',
  'Why did you skip barbell squats for her?',
  'What should I watch for with this member?',
];

const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);

// Route free-text: workout-building verbs => generate; question/why words => explain.
function wantsWorkout(text: string): boolean {
  if (/\b(build|generate|create|make|plan|design|program|routine)\b/i.test(text)) return true;
  if (/\b(why|watch|explain|reason|skip|exclude|constraint)\b/i.test(text)) return false;
  if (/^(what|how|when|which|who)\b/i.test(text)) return false;
  return true;
}

export function ChatPanel({ memberId }: { memberId: string }) {
  const [messages, setMessages] = useState<Msg[]>([
    {
      id: 0,
      role: 'assistant',
      kind: 'text',
      text: `Hi — I'm ${cap(memberId)}'s coaching assistant. Ask me to build a workout, or ask "why?" about any choice. Every answer is grounded in her knowledge graph.`,
    },
  ]);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const scroller = useRef<ScrollView>(null);
  const idRef = useRef(1);
  const nextId = () => idRef.current++;

  const toEnd = () => setTimeout(() => scroller.current?.scrollToEnd({ animated: true }), 60);

  async function send(text: string) {
    const q = text.trim();
    if (!q || busy) return;
    setInput('');
    setBusy(true);
    setMessages((prev) => [
      ...prev,
      { id: nextId(), role: 'user', text: q },
      { id: nextId(), role: 'assistant', kind: 'loading' },
    ]);
    toEnd();
    try {
      const reply: Msg = wantsWorkout(q)
        ? { id: nextId(), role: 'assistant', kind: 'workout', result: await generateWorkout(memberId, q) }
        : { id: nextId(), role: 'assistant', kind: 'explanation', answer: await explain(memberId, q) };
      setMessages((prev) => [...prev.slice(0, -1), reply]);
    } catch (e: any) {
      setMessages((prev) => [...prev.slice(0, -1), { id: nextId(), role: 'assistant', kind: 'error', text: String(e?.message ?? e) }]);
    } finally {
      setBusy(false);
      toEnd();
    }
  }

  return (
    <View style={styles.panel}>
      <ScrollView ref={scroller} style={styles.messages} contentContainerStyle={styles.messagesInner}>
        {messages.map((m) => (
          <MessageBubble key={m.id} m={m} />
        ))}
      </ScrollView>

      <View style={styles.suggestions}>
        {SUGGESTIONS.map((s) => (
          <Pressable key={s} onPress={() => send(s)} disabled={busy} style={styles.suggestion}>
            <Text style={styles.suggestionText} numberOfLines={1}>
              {s}
            </Text>
          </Pressable>
        ))}
      </View>

      <View style={styles.inputBar}>
        <TextInput
          value={input}
          onChangeText={setInput}
          placeholder="Ask the coach…"
          placeholderTextColor={colors.muted}
          style={styles.input}
          editable={!busy}
          onSubmitEditing={() => send(input)}
          returnKeyType="send"
        />
        <Pressable onPress={() => send(input)} disabled={busy || !input.trim()} style={[styles.send, (busy || !input.trim()) && styles.sendDisabled]}>
          <Text style={styles.sendText}>Send</Text>
        </Pressable>
      </View>
    </View>
  );
}

function MessageBubble({ m }: { m: Msg }) {
  if (m.role === 'user') {
    return (
      <View style={[styles.row, styles.rowEnd]}>
        <View style={[styles.bubble, styles.userBubble]}>
          <Text style={styles.userText}>{m.text}</Text>
        </View>
      </View>
    );
  }

  // assistant
  let body: React.ReactNode;
  if (m.kind === 'loading') {
    body = (
      <View style={styles.loadingRow}>
        <ActivityIndicator color={colors.accent} />
        <Text style={styles.loadingText}>thinking…</Text>
      </View>
    );
  } else if (m.kind === 'text') {
    body = <Text style={styles.assistantText}>{m.text}</Text>;
  } else if (m.kind === 'error') {
    body = <Text style={styles.errorText}>{m.text}</Text>;
  } else if (m.kind === 'workout') {
    body = <WorkoutView result={m.result} />;
  } else {
    // explanation
    body = (
      <View>
        <Text style={styles.assistantText}>{m.answer.answer}</Text>
        {m.answer.graph_trace.length > 0 && (
          <>
            <Text style={styles.traceHead}>Graph evidence</Text>
            {m.answer.graph_trace.map((t, i) => (
              <Text key={i} style={styles.trace}>
                {t.subject} —{t.relation}→ {t.object}
                {t.note ? `  (${t.note})` : ''}
              </Text>
            ))}
          </>
        )}
      </View>
    );
  }

  const wide = m.kind === 'workout';
  return (
    <View style={[styles.row, styles.rowStart]}>
      <View style={[styles.bubble, styles.assistantBubble, wide && styles.assistantWide]}>{body}</View>
    </View>
  );
}

const styles = StyleSheet.create({
  panel: { flex: 1, backgroundColor: colors.bg },
  messages: { flex: 1 },
  messagesInner: { padding: 16, gap: 10 },
  row: { flexDirection: 'row' },
  rowEnd: { justifyContent: 'flex-end' },
  rowStart: { justifyContent: 'flex-start' },
  bubble: { maxWidth: '88%', borderRadius: 14, paddingVertical: 10, paddingHorizontal: 13 },
  userBubble: { backgroundColor: colors.accent, borderBottomRightRadius: 4 },
  userText: { color: '#fff', fontSize: 15, lineHeight: 21 },
  assistantBubble: { backgroundColor: colors.card, borderWidth: 1, borderColor: colors.border, borderBottomLeftRadius: 4 },
  assistantWide: { maxWidth: '98%', width: '98%', padding: 0, borderWidth: 0, backgroundColor: 'transparent' },
  assistantText: { color: colors.text, fontSize: 15, lineHeight: 21 },
  errorText: { color: colors.danger, fontSize: 14 },
  loadingRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  loadingText: { color: colors.muted, fontStyle: 'italic' },
  traceHead: { fontSize: 11, fontWeight: '700', color: colors.muted, textTransform: 'uppercase', marginTop: 10, marginBottom: 5 },
  trace: { color: colors.muted, fontSize: 12, fontFamily: 'monospace', marginBottom: 2 },
  suggestions: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, paddingHorizontal: 16, paddingBottom: 8 },
  suggestion: { borderWidth: 1, borderColor: colors.border, backgroundColor: colors.card, borderRadius: 16, paddingVertical: 6, paddingHorizontal: 11, maxWidth: '100%' },
  suggestionText: { color: colors.accent, fontSize: 12, fontWeight: '600' },
  inputBar: { flexDirection: 'row', gap: 8, padding: 12, borderTopWidth: 1, borderTopColor: colors.border, backgroundColor: colors.card },
  input: { flex: 1, borderWidth: 1, borderColor: colors.border, borderRadius: 10, paddingHorizontal: 12, paddingVertical: 10, fontSize: 15, color: colors.text, backgroundColor: '#fff' },
  send: { backgroundColor: colors.accent, borderRadius: 10, paddingHorizontal: 18, justifyContent: 'center' },
  sendDisabled: { opacity: 0.5 },
  sendText: { color: '#fff', fontWeight: '700' },
});
