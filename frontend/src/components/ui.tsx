import { ReactNode } from 'react';
import { StyleSheet, Text, View } from 'react-native';

export const colors = {
  bg: '#f5f6f8',
  card: '#ffffff',
  border: '#e3e6ea',
  text: '#1a1d21',
  muted: '#5f6671',
  accent: '#2563eb',
  danger: '#c5221f',
  ok: '#137333',
  warnBg: '#fef7e0',
  dangerBg: '#fce8e6',
};

export function Card({ children, style }: { children: ReactNode; style?: any }) {
  return <View style={[styles.card, style]}>{children}</View>;
}

export function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <Card>
      <Text style={styles.sectionTitle}>{title}</Text>
      {children}
    </Card>
  );
}

export function Chip({ label, tone = 'default' }: { label: string; tone?: 'default' | 'danger' | 'ok' | 'warn' }) {
  const toneStyle =
    tone === 'danger' ? styles.chipDanger : tone === 'ok' ? styles.chipOk : tone === 'warn' ? styles.chipWarn : styles.chipDefault;
  const textTone = tone === 'danger' ? { color: colors.danger } : tone === 'ok' ? { color: colors.ok } : null;
  return (
    <View style={[styles.chip, toneStyle]}>
      <Text style={[styles.chipText, textTone]}>{label}</Text>
    </View>
  );
}

export function ChipRow({ children }: { children: ReactNode }) {
  return <View style={styles.chipRow}>{children}</View>;
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.card,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.border,
    padding: 16,
    marginBottom: 14,
  },
  sectionTitle: { fontSize: 13, fontWeight: '700', color: colors.muted, textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 10 },
  chipRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  chip: { borderRadius: 16, paddingVertical: 5, paddingHorizontal: 11, borderWidth: 1 },
  chipDefault: { backgroundColor: '#eef1f5', borderColor: colors.border },
  chipDanger: { backgroundColor: colors.dangerBg, borderColor: '#f3c0bd' },
  chipOk: { backgroundColor: '#e6f4ea', borderColor: '#b7dfc3' },
  chipWarn: { backgroundColor: colors.warnBg, borderColor: '#f5e2a8' },
  chipText: { fontSize: 13, color: colors.text },
});
