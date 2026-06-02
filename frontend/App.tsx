import { StatusBar } from 'expo-status-bar';
import { useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { colors } from './src/components/ui';
import { MemberScreen } from './src/screens/MemberScreen';

// One strong synthetic member (PRD §16, depth over breadth). The selector is built
// to take more members later.
const MEMBERS = [{ id: 'maya', name: 'Maya' }];

export default function App() {
  const [memberId, setMemberId] = useState(MEMBERS[0].id);

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

      <ScrollView style={styles.scroll} contentContainerStyle={styles.content}>
        <MemberScreen memberId={memberId} />
      </ScrollView>
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
    paddingTop: 18,
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
  scroll: { flex: 1 },
  content: { padding: 20, maxWidth: 760, width: '100%', alignSelf: 'center' },
});
