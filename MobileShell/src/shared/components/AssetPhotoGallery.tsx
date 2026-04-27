import React, { useEffect, useMemo, useState } from "react";
import { ActivityIndicator, FlatList, Image, Modal, Pressable, StyleSheet, Text, View } from "react-native";
import { api } from "../api/client";
import { colors } from "../theme";
import { InventoryItemResponse } from "../types";

type Props = {
  assetId: number;
  basePhotoUrl?: string | null;
  toMediaUrl: (photoPath: string | null) => string;
};

export function AssetPhotoGallery({ assetId, basePhotoUrl, toMediaUrl }: Props) {
  const [inventoryItems, setInventoryItems] = useState<InventoryItemResponse[]>([]);
  const [loading, setLoading] = useState(false);
  const [activeIndex, setActiveIndex] = useState<number | null>(null);

  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        const res = await api.get<InventoryItemResponse[]>("/inventory-items/");
        setInventoryItems(res.data);
      } finally {
        setLoading(false);
      }
    })();
  }, [assetId]);

  const photos = useMemo(() => {
    const urls: string[] = [];
    const add = (url?: string | null) => {
      const normalized = (url || "").trim();
      if (!normalized) {
        return;
      }
      if (!urls.includes(normalized)) {
        urls.push(normalized);
      }
    };
    add(basePhotoUrl);
    inventoryItems
      .filter((item) => item.asset === assetId)
      .forEach((item) => add(toMediaUrl(item.photo || null)));
    return urls;
  }, [assetId, basePhotoUrl, inventoryItems, toMediaUrl]);

  if (loading) {
    return (
      <View style={styles.loading}>
        <ActivityIndicator color={colors.accent} />
        <Text style={styles.helper}>Загружаем фото...</Text>
      </View>
    );
  }

  if (photos.length === 0) {
    return <Text style={styles.helper}>Фото не загружено</Text>;
  }

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Фото актива ({photos.length})</Text>
      <FlatList
        horizontal
        data={photos}
        keyExtractor={(item, index) => `${item}-${index}`}
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.row}
        renderItem={({ item, index }) => (
          <Pressable onPress={() => setActiveIndex(index)}>
            <Image source={{ uri: item }} style={styles.thumb} resizeMode="cover" />
          </Pressable>
        )}
      />

      <Modal visible={activeIndex !== null} transparent animationType="fade" onRequestClose={() => setActiveIndex(null)}>
        <View style={styles.overlay}>
          <Pressable style={styles.close} onPress={() => setActiveIndex(null)}>
            <Text style={styles.closeText}>Закрыть</Text>
          </Pressable>
          {activeIndex !== null ? <Image source={{ uri: photos[activeIndex] }} style={styles.full} resizeMode="contain" /> : null}
          <View style={styles.controls}>
            <Pressable
              style={[styles.nav, activeIndex === 0 && styles.disabled]}
              disabled={activeIndex === 0}
              onPress={() => setActiveIndex((prev) => (prev === null ? null : prev - 1))}
            >
              <Text style={styles.navText}>Назад</Text>
            </Pressable>
            <Text style={styles.counter}>
              {(activeIndex || 0) + 1}/{photos.length}
            </Text>
            <Pressable
              style={[styles.nav, activeIndex === photos.length - 1 && styles.disabled]}
              disabled={activeIndex === photos.length - 1}
              onPress={() => setActiveIndex((prev) => (prev === null ? null : prev + 1))}
            >
              <Text style={styles.navText}>Вперёд</Text>
            </Pressable>
          </View>
        </View>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { marginTop: 8, gap: 8 },
  title: { color: colors.textPrimary, fontWeight: "700" },
  row: { gap: 8 },
  thumb: { width: 130, height: 130, borderRadius: 10, borderWidth: 1, borderColor: colors.border },
  helper: { color: colors.textSecondary },
  loading: { flexDirection: "row", alignItems: "center", gap: 8 },
  overlay: { flex: 1, backgroundColor: "rgba(0,0,0,0.95)", justifyContent: "center", alignItems: "center" },
  full: { width: "100%", height: "78%" },
  close: {
    position: "absolute",
    top: 48,
    right: 16,
    zIndex: 2,
    backgroundColor: "rgba(0,0,0,0.5)",
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 6,
  },
  closeText: { color: "#fff", fontWeight: "700" },
  controls: {
    position: "absolute",
    bottom: 28,
    left: 16,
    right: 16,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  nav: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 8,
    backgroundColor: "rgba(0,0,0,0.45)",
  },
  navText: { color: "#fff", fontWeight: "700" },
  disabled: { opacity: 0.35 },
  counter: { color: "#fff", fontWeight: "700" },
});
