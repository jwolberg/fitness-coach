import { ReactNode } from 'react';
import { Platform, StyleSheet, Text, View } from 'react-native';

// Consumer-friendly typeface, loaded once on web and applied globally (overrides the
// react-native-web default font on every element via a high-priority rule).
export const FONT =
  'Poppins, system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif';

if (Platform.OS === 'web' && typeof document !== 'undefined' && !document.getElementById('app-fonts')) {
  const link = document.createElement('link');
  link.id = 'app-fonts';
  link.rel = 'stylesheet';
  link.href = 'https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800&display=swap';
  document.head.appendChild(link);

  const style = document.createElement('style');
  // `* !important` beats react-native-web's atomic font-family classes.
  style.textContent = `* { font-family: ${FONT} !important; }`;
  document.head.appendChild(style);
}

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
  // iMessage-style chat
  imessageBlue: '#007aff',
  imessageGray: '#e9e9eb',
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
    borderRadius: 16,
    borderWidth: 1,
    borderColor: colors.border,
    padding: 22,
    marginBottom: 18,
  },
  sectionTitle: { fontSize: 24, fontWeight: '700', color: colors.muted, textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 14 },
  chipRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 10 },
  chip: { borderRadius: 22, paddingVertical: 8, paddingHorizontal: 16, borderWidth: 1 },
  chipDefault: { backgroundColor: '#eef1f5', borderColor: colors.border },
  chipDanger: { backgroundColor: colors.dangerBg, borderColor: '#f3c0bd' },
  chipOk: { backgroundColor: '#e6f4ea', borderColor: '#b7dfc3' },
  chipWarn: { backgroundColor: colors.warnBg, borderColor: '#f5e2a8' },
  chipText: { fontSize: 26, color: colors.text },
});
