import { StatusBar } from 'expo-status-bar';
import { useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, useWindowDimensions, View } from 'react-native';

import { colors } from './src/components/ui';
import { ChatPanel } from './src/screens/ChatPanel';
import { MemberScreen } from './src/screens/MemberScreen';

// One strong synthetic member (PRD §16, depth over breadth). Selector takes more later.
const MEMBERS = [{ id: 'maya', name: 'Maya' }];

export default function App() {
  const [memberId, setMemberId] = useState(MEMBERS[0].id);
  const { width } = useWindowDimensions();
  const twoCol = width >= 900;

  const context = (
    <ScrollView style={styles.colScroll} contentContainerStyle={styles.colContent}>
      <Text style={styles.colHeading}>Member context</Text>
      <MemberScreen memberId={memberId} />
    </ScrollView>
  );

  // Chat is keyed by member so switching members resets the conversation.
  const chat = <ChatPanel key={memberId} memberId={memberId} />;

  return (
    <View style={styles.app}>
      <View style={styles.header}>
        <Text style={styles.brand}>Knowledge Graph Coaching</Text>
        <View style={styles.selector}>
          {MEMBERS.map((m) => {
            const active = m.id === memberId;
            return (
              <Pressable key={m.id} onPress={() => setMemberId(m.id)} style={[styles.tab, active && styles.tabActive]}>
                <Text style={[styles.tabText, active && styles.tabTextActive]}>{m.name}</Text>
              </Pressable>
            );
          })}
        </View>
      </View>

      <View style={[styles.body, { flexDirection: twoCol ? 'row' : 'column' }]}>
        <View style={[styles.col, styles.chatCol, twoCol ? styles.dividerRight : styles.dividerBottom]}>{chat}</View>
        <View style={[styles.col, styles.ctxCol]}>{context}</View>
      </View>
      <StatusBar style="auto" />
    </View>
  );
}

const styles = StyleSheet.create({
  app: { flex: 1, backgroundColor: colors.bg },
  header: {
    backgroundColor: colors.card,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
    paddingHorizontal: 20,
    paddingTop: 16,
    paddingBottom: 14,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    flexWrap: 'wrap',
    gap: 12,
  },
  brand: { fontSize: 18, fontWeight: '800', color: colors.text },
  selector: { flexDirection: 'row', gap: 8 },
  tab: { paddingVertical: 6, paddingHorizontal: 14, borderRadius: 18, borderWidth: 1, borderColor: colors.border },
  tabActive: { backgroundColor: colors.accent, borderColor: colors.accent },
  tabText: { color: colors.text, fontWeight: '600' },
  tabTextActive: { color: '#fff' },

  body: { flex: 1, minHeight: 0 },
  col: { flex: 1, minHeight: 0 },
  chatCol: { flex: 1.2 },
  ctxCol: { backgroundColor: colors.bg },
  dividerRight: { borderRightWidth: 1, borderRightColor: colors.border },
  dividerBottom: { borderBottomWidth: 1, borderBottomColor: colors.border },
  colScroll: { flex: 1 },
  colContent: { padding: 20, maxWidth: 640, width: '100%', alignSelf: 'center' },
  colHeading: { fontSize: 13, fontWeight: '700', color: colors.muted, textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 12 },
});
