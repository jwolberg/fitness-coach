import { StatusBar } from 'expo-status-bar';
import { useEffect, useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { API_URL, getHealth } from './src/api/client';

// P4-T1: minimal screen proving the web build can reach the backend.
// P4-T2/T3 replace this with the member/context view and the query→workout→why flow.
export default function App() {
  const [status, setStatus] = useState<'checking' | 'ok' | 'error'>('checking');
  const [detail, setDetail] = useState('');

  useEffect(() => {
    getHealth()
      .then((r) => {
        setStatus('ok');
        setDetail(JSON.stringify(r));
      })
      .catch((e) => {
        setStatus('error');
        setDetail(String(e?.message ?? e));
      });
  }, []);

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Knowledge Graph Coaching</Text>
      <Text style={styles.api}>API: {API_URL}</Text>
      <Text
        style={[
          styles.status,
          status === 'ok' ? styles.ok : status === 'error' ? styles.err : null,
        ]}
      >
        backend: {status}
      </Text>
      {!!detail && <Text style={styles.detail}>{detail}</Text>}
      <StatusBar style="auto" />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fff', alignItems: 'center', justifyContent: 'center', padding: 24 },
  title: { fontSize: 22, fontWeight: '700', marginBottom: 12 },
  api: { color: '#555', marginBottom: 8 },
  status: { fontSize: 16, fontWeight: '600' },
  ok: { color: '#137333' },
  err: { color: '#c5221f' },
  detail: { marginTop: 12, color: '#666', fontSize: 12 },
});
