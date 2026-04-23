import React, { useEffect, useState } from "react";
import { FlatList, Image, Pressable, RefreshControl, SafeAreaView, StyleSheet, Text, View } from "react-native";
import { api } from "../../shared/api/client";
import { API_BASE_URL } from "../../shared/config";
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

function toMediaUrl(photoPath: string | null) {
  if (!photoPath) {
    return "";
  }
  if (photoPath.startsWith("http://") || photoPath.startsWith("https://")) {
    return photoPath;
  }
  const origin = API_BASE_URL.replace(/\/api\/v1\/?$/, "");
  return `${origin}${photoPath.startsWith("/") ? "" : "/"}${photoPath}`;
}

export function MyResponsibleAssetsScreen() {
  const [items, setItems] = useState<Asset[]>([]);
  const [refreshing, setRefreshing] = useState(false);
  const [selectedAsset, setSelectedAsset] = useState<Asset | null>(null);

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

  if (selectedAsset) {
    const photoUrl = toMediaUrl(selectedAsset.photo);
    return (
      <SafeAreaView style={styles.container}>
        <Pressable onPress={() => setSelectedAsset(null)} style={styles.backButton}>
          <Text style={styles.backText}>{"<"} Назад к списку</Text>
        </Pressable>
        <View style={styles.card}>
          <Text style={styles.name}>{selectedAsset.name}</Text>
          <Text style={styles.meta}>Инв. номер: {selectedAsset.inventory_number}</Text>
          <Text style={styles.meta}>Статус: {getStatusRu(selectedAsset.status)}</Text>
          <Text style={styles.meta}>Описание: {selectedAsset.description || "Нет описания"}</Text>
          {photoUrl ? <Image source={{ uri: photoUrl }} style={styles.photo} resizeMode="cover" /> : <Text style={styles.meta}>Фото не загружено</Text>}
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <Text style={styles.title}>Вы ответственны за</Text>
      <FlatList
        data={items}
        keyExtractor={(item) => String(item.id)}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={load} />}
        renderItem={({ item }) => (
          <Pressable style={styles.card} onPress={() => setSelectedAsset(item)}>
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
  backButton: { paddingVertical: 6, paddingHorizontal: 8, borderWidth: 1, borderColor: colors.border, borderRadius: 8, marginBottom: 10, alignSelf: "flex-start" },
  backText: { color: colors.accent, fontWeight: "600" },
  card: { borderWidth: 1, borderColor: colors.border, borderRadius: 10, padding: 12, marginBottom: 10, backgroundColor: colors.surface },
  name: { fontWeight: "700", marginBottom: 4, color: colors.textPrimary },
  meta: { color: colors.textSecondary },
  photo: { width: "100%", height: 220, borderRadius: 10, marginTop: 10, borderWidth: 1, borderColor: colors.border },
});
