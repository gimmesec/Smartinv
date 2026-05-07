import React, { useEffect, useMemo, useState } from "react";
import { ActivityIndicator, Alert, FlatList, Image, Modal, Pressable, StyleSheet, Text, View } from "react-native";
import { launchCamera } from "react-native-image-picker";
import { api } from "../api/client";
import { colors } from "../theme";
import { AssetPhoto } from "../types";

type Props = {
  assetId: number;
  sessionId?: number | null;
  basePhotoUrl?: string | null;
  toMediaUrl: (photoPath: string | null) => string;
  editable?: boolean;
};

type GalleryPhoto = {
  id: number | null;
  url: string;
};

export function AssetPhotoGallery({ assetId, sessionId, basePhotoUrl, toMediaUrl, editable = true }: Props) {
  const [assetPhotos, setAssetPhotos] = useState<AssetPhoto[]>([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [activeIndex, setActiveIndex] = useState<number | null>(null);

  const loadPhotos = React.useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get<AssetPhoto[]>("/asset-photos/", {
        params: sessionId == null ? { asset: assetId } : { asset: assetId, session: sessionId },
      });
      setAssetPhotos(res.data);
    } finally {
      setLoading(false);
    }
  }, [assetId, sessionId]);

  useEffect(() => {
    void loadPhotos();
  }, [loadPhotos]);

  const photos = useMemo(() => {
    const items: GalleryPhoto[] = [];
    const add = (url?: string | null, id: number | null = null) => {
      const normalized = (url || "").trim();
      if (!normalized) {
        return;
      }
      if (!items.some((item) => item.url === normalized)) {
        items.push({ id, url: normalized });
      }
    };
    add(basePhotoUrl);
    assetPhotos.forEach((item) => add(toMediaUrl(item.photo_url || item.photo || null), item.id));
    return items;
  }, [basePhotoUrl, assetPhotos, toMediaUrl]);

  const uploadPhoto = async () => {
    const result = await launchCamera({
      mediaType: "photo",
      cameraType: "back",
      saveToPhotos: false,
      quality: 0.7,
    });
    const picked = result.assets?.[0];
    if (!picked?.uri) {
      return;
    }
    const uri = picked.uri;
    try {
      setUploading(true);
      const formData = new FormData();
      formData.append("asset", String(assetId));
      if (sessionId != null) {
        formData.append("session", String(sessionId));
      }
      formData.append("photo", {
        uri,
        type: picked.type || "image/jpeg",
        name: picked.fileName || `asset-${assetId}-${Date.now()}.jpg`,
      } as any);
      await api.post("/asset-photos/", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      await loadPhotos();
    } catch {
      Alert.alert("Ошибка", "Не удалось загрузить фото.");
    } finally {
      setUploading(false);
    }
  };

  const deleteActivePhoto = async () => {
    if (activeIndex === null) {
      return;
    }
    const photo = photos[activeIndex];
    if (!photo?.id) {
      Alert.alert("Нельзя удалить", "Это старое фото без записи AssetPhoto. После миграции оно станет обычной записью фото.");
      return;
    }
    Alert.alert("Удалить фото?", "Фото будет удалено из коллекции актива.", [
      { text: "Отмена", style: "cancel" },
      {
        text: "Удалить",
        style: "destructive",
        onPress: async () => {
          try {
            setDeleting(true);
            await api.delete(`/asset-photos/${photo.id}/`);
            setActiveIndex(null);
            await loadPhotos();
          } catch {
            Alert.alert("Ошибка", "Не удалось удалить фото.");
          } finally {
            setDeleting(false);
          }
        },
      },
    ]);
  };

  if (loading) {
    return (
      <View style={styles.loading}>
        <ActivityIndicator color={colors.accent} />
        <Text style={styles.helper}>Загружаем фото...</Text>
      </View>
    );
  }

  if (photos.length === 0) {
    return (
      <View style={styles.container}>
        <Text style={styles.helper}>Фото не загружено</Text>
        {editable ? (
          <Pressable style={[styles.addButton, uploading && styles.disabled]} onPress={uploadPhoto} disabled={uploading}>
            <Text style={styles.addButtonText}>{uploading ? "Загрузка..." : "Добавить фото"}</Text>
          </Pressable>
        ) : null}
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Фото актива ({photos.length})</Text>
        {editable ? (
          <Pressable style={[styles.addButton, uploading && styles.disabled]} onPress={uploadPhoto} disabled={uploading}>
            <Text style={styles.addButtonText}>{uploading ? "Загрузка..." : "Добавить"}</Text>
          </Pressable>
        ) : null}
      </View>
      <FlatList
        horizontal
        data={photos}
        keyExtractor={(item, index) => `${item.id || item.url}-${index}`}
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.row}
        renderItem={({ item, index }) => (
          <Pressable onPress={() => setActiveIndex(index)}>
            <Image source={{ uri: item.url }} style={styles.thumb} resizeMode="cover" />
          </Pressable>
        )}
      />

      <Modal visible={activeIndex !== null} transparent animationType="fade" onRequestClose={() => setActiveIndex(null)}>
        <View style={styles.overlay}>
          <Pressable style={styles.close} onPress={() => setActiveIndex(null)}>
            <Text style={styles.closeText}>Закрыть</Text>
          </Pressable>
          {editable && activeIndex !== null ? (
            <Pressable
              style={[styles.deleteButton, deleting && styles.disabled]}
              onPress={deleteActivePhoto}
              disabled={deleting}
            >
              <Text style={styles.deleteText}>{deleting ? "Удаляем..." : "Удалить"}</Text>
            </Pressable>
          ) : null}
          {activeIndex !== null ? <Image source={{ uri: photos[activeIndex].url }} style={styles.full} resizeMode="contain" /> : null}
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
  header: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 8 },
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
  deleteButton: {
    position: "absolute",
    top: 48,
    left: 16,
    zIndex: 2,
    backgroundColor: "rgba(220,53,69,0.75)",
    borderWidth: 1,
    borderColor: colors.danger,
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 6,
  },
  deleteText: { color: "#fff", fontWeight: "700" },
  addButton: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 8,
    paddingHorizontal: 10,
    paddingVertical: 7,
    backgroundColor: colors.surfaceAlt,
  },
  addButtonText: { color: colors.textPrimary, fontWeight: "700", fontSize: 12 },
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
