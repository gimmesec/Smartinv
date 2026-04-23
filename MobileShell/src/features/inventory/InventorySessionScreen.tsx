import React, { useEffect, useState } from "react";
import { FlatList, Pressable, SafeAreaView, StyleSheet, Text, View } from "react-native";
import { api } from "../../shared/api/client";
import { colors } from "../../shared/theme";
import { InventorySession } from "../../shared/types";

type Props = {
  onSelectSession: (sessionId: number) => void;
};

export function InventorySessionScreen({ onSelectSession }: Props) {
  const [sessions, setSessions] = useState<InventorySession[]>([]);

  useEffect(() => {
    (async () => {
      const res = await api.get<InventorySession[]>("/inventory-sessions/");
      setSessions(res.data);
    })();
  }, []);

  return (
    <SafeAreaView style={styles.container}>
      <FlatList
        data={sessions}
        keyExtractor={(item) => String(item.id)}
        renderItem={({ item }) => (
          <Pressable style={styles.card} onPress={() => onSelectSession(item.id)}>
            <Text style={styles.title}>Сессия #{item.id}</Text>
            <Text style={styles.meta}>Статус: {item.status}</Text>
          </Pressable>
        )}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 12, backgroundColor: colors.background },
  card: { borderWidth: 1, borderColor: colors.border, backgroundColor: colors.surface, borderRadius: 8, padding: 12, marginBottom: 10 },
  title: { fontWeight: "700", marginBottom: 4, color: colors.textPrimary },
  meta: { color: colors.textSecondary },
});
