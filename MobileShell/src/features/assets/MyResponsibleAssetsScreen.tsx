import React, { useEffect, useState } from "react";
import { FlatList, Pressable, RefreshControl, SafeAreaView, StyleSheet, Text, View } from "react-native";
import { api } from "../../shared/api/client";
import { colors } from "../../shared/theme";
import { Asset } from "../../shared/types";

function getStatusRu(status: string) {
  const map: Record<string, string> = {
    active: "Исправен",
    damaged: "Поврежден",
    lost: "Отсутствует",
    written_off: "Списан",
  };
  return map[status] ?? status;
}

export function MyResponsibleAssetsScreen() {
  const [items, setItems] = useState<Asset[]>([]);
  const [refreshing, setRefreshing] = useState(false);

  const load = async () => {
    setRefreshing(true);
    try {
      const res = await api.get<Asset[]>("/assets/my-responsible/");
      setItems(res.data);
    } finally {
      setRefreshing(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  return (
    <SafeAreaView style={styles.container}>
      <Text style={styles.title}>Вы ответственны за</Text>
      <FlatList
        data={items}
        keyExtractor={(item) => String(item.id)}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={load} />}
        renderItem={({ item }) => (
          <Pressable style={styles.card}>
            <Text style={styles.name}>{item.name}</Text>
            <Text style={styles.meta}>Инв. номер: {item.inventory_number}</Text>
            <Text style={styles.meta}>Статус: {getStatusRu(item.status)}</Text>
          </Pressable>
        )}
        ListEmptyComponent={
          <View style={styles.card}>
            <Text style={styles.meta}>На вас пока не закреплено материальных активов.</Text>
          </View>
        }
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 12, backgroundColor: colors.background },
  title: { color: colors.textPrimary, fontSize: 20, fontWeight: "700", marginBottom: 10 },
  card: { borderWidth: 1, borderColor: colors.border, borderRadius: 10, padding: 12, marginBottom: 10, backgroundColor: colors.surface },
  name: { fontWeight: "700", marginBottom: 4, color: colors.textPrimary },
  meta: { color: colors.textSecondary },
});
