import React, { useCallback, useState } from "react";
import { FlatList, RefreshControl, SafeAreaView, StyleSheet, Text, View } from "react-native";
import { api } from "../../shared/api/client";
import { colors } from "../../shared/theme";
import { Asset } from "../../shared/types";

export function AssetsScreen() {
  const [items, setItems] = useState<Asset[]>([]);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    setRefreshing(true);
    try {
      const res = await api.get<Asset[]>("/assets/");
      setItems(res.data);
    } finally {
      setRefreshing(false);
    }
  }, []);

  React.useEffect(() => {
    load();
  }, [load]);

  return (
    <SafeAreaView style={styles.container}>
      <FlatList
        data={items}
        keyExtractor={(item) => String(item.id)}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={load} />}
        renderItem={({ item }) => (
          <View style={styles.card}>
            <Text style={styles.name}>{item.name}</Text>
            <Text style={styles.meta}>Инв. номер: {item.inventory_number}</Text>
            <Text style={styles.meta}>Статус: {item.status}</Text>
          </View>
        )}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 12, backgroundColor: colors.background },
  card: { backgroundColor: colors.surface, borderRadius: 10, padding: 12, marginBottom: 10, borderWidth: 1, borderColor: colors.border },
  name: { fontWeight: "700", marginBottom: 4, color: colors.textPrimary },
  meta: { color: colors.textSecondary },
});
