import React, { useCallback, useMemo, useState } from "react";
import { FlatList, Pressable, RefreshControl, SafeAreaView, StyleSheet, Text, View } from "react-native";
import { useAuth } from "../auth/AuthContext";
import { api } from "../../shared/api/client";
import { API_BASE_URL } from "../../shared/config";
import { AssetPhotoGallery } from "../../shared/components/AssetPhotoGallery";
import { colors } from "../../shared/theme";
import { Asset, LegalEntity, Location } from "../../shared/types";

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

function getStatusRu(status: string) {
  const map: Record<string, string> = {
    active: "Исправен",
    damaged: "Поврежден",
    lost: "Отсутствует",
    written_off: "Списан",
  };
  return map[status] ?? status;
}

export function AssetsScreen() {
  const { user } = useAuth();
  const isAdmin = !!user?.is_admin;
  const [items, setItems] = useState<Asset[]>([]);
  const [entities, setEntities] = useState<LegalEntity[]>([]);
  const [locations, setLocations] = useState<Location[]>([]);
  const [refreshing, setRefreshing] = useState(false);
  const [selectedEntityId, setSelectedEntityId] = useState<number | null>(null);
  const [selectedLocationId, setSelectedLocationId] = useState<number | null>(null);
  const [selectedAsset, setSelectedAsset] = useState<Asset | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setRefreshing(true);
    setLoadError(null);
    try {
      const [assetsRes, entitiesRes, locationsRes] = await Promise.allSettled([
        api.get<Asset[]>("/assets/"),
        api.get<LegalEntity[]>("/legal-entities/"),
        api.get<Location[]>("/locations/"),
      ]);
      if (assetsRes.status === "fulfilled") {
        setItems(assetsRes.value.data);
      }
      if (entitiesRes.status === "fulfilled") {
        setEntities(entitiesRes.value.data);
      }
      if (locationsRes.status === "fulfilled") {
        setLocations(locationsRes.value.data);
      }
      if (
        assetsRes.status === "rejected" ||
        entitiesRes.status === "rejected" ||
        locationsRes.status === "rejected"
      ) {
        setLoadError("Часть данных не загрузилась. Проверьте соединение и обновите экран.");
      }
      if (!isAdmin && user?.legal_entity_id) {
        setSelectedEntityId(user.legal_entity_id);
      }
    } finally {
      setRefreshing(false);
    }
  }, [isAdmin, user?.legal_entity_id]);

  React.useEffect(() => {
    load();
  }, [load]);

  const entityLocations = useMemo(() => {
    if (!selectedEntityId) {
      return [];
    }
    return locations.filter((loc) => loc.legal_entity === selectedEntityId);
  }, [locations, selectedEntityId]);

  const currentAssets = useMemo(() => {
    if (!selectedEntityId || !selectedLocationId) {
      return [];
    }
    return items.filter((asset) => asset.legal_entity === selectedEntityId && asset.location === selectedLocationId);
  }, [items, selectedEntityId, selectedLocationId]);

  if (selectedAsset) {
    const photoUrl = toMediaUrl(selectedAsset.photo);
    return (
      <SafeAreaView style={styles.container}>
        <Pressable onPress={() => setSelectedAsset(null)} style={styles.breadcrumbButton}>
          <Text style={styles.breadcrumbText}>{"<"} Назад к списку</Text>
        </Pressable>
        <View style={styles.card}>
          <Text style={styles.name}>{selectedAsset.name}</Text>
          <Text style={styles.meta}>Инв. номер: {selectedAsset.inventory_number}</Text>
          <Text style={styles.meta}>Статус: {getStatusRu(selectedAsset.status)}</Text>
          <Text style={styles.meta}>Описание: {selectedAsset.description || "Нет описания"}</Text>
          <AssetPhotoGallery assetId={selectedAsset.id} basePhotoUrl={photoUrl} toMediaUrl={toMediaUrl} />
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <Text style={styles.title}>Активы</Text>
      {loadError ? <Text style={styles.error}>{loadError}</Text> : null}
      {!selectedEntityId ? (
        <FlatList
          data={entities}
          keyExtractor={(item) => String(item.id)}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={load} />}
          renderItem={({ item }) => (
            <Pressable style={styles.card} onPress={() => setSelectedEntityId(item.id)}>
              <Text style={styles.name}>{item.name}</Text>
              <Text style={styles.meta}>ИНН: {item.tax_id}</Text>
            </Pressable>
          )}
          ListEmptyComponent={<Text style={styles.empty}>Юрлица не найдены</Text>}
        />
      ) : (
        <>
          <View style={styles.row}>
            {isAdmin ? (
              <Pressable
                onPress={() => {
                  setSelectedEntityId(null);
                  setSelectedLocationId(null);
                }}
                style={styles.breadcrumbButton}
              >
                <Text style={styles.breadcrumbText}>{"<"} Юрлица</Text>
              </Pressable>
            ) : null}
            {selectedLocationId ? (
              <Pressable
                onPress={() => {
                  setSelectedLocationId(null);
                }}
                style={styles.breadcrumbButton}
              >
                <Text style={styles.breadcrumbText}>{"<"} Помещения</Text>
              </Pressable>
            ) : null}
          </View>
          {!selectedLocationId ? (
            <FlatList
              data={entityLocations}
              keyExtractor={(item) => String(item.id)}
              refreshControl={<RefreshControl refreshing={refreshing} onRefresh={load} />}
              renderItem={({ item }) => (
                <Pressable style={styles.card} onPress={() => setSelectedLocationId(item.id)}>
                  <Text style={styles.name}>{item.name}</Text>
                  <Text style={styles.meta}>Помещение</Text>
                </Pressable>
              )}
              ListEmptyComponent={<Text style={styles.empty}>Для юрлица не найдено помещений</Text>}
            />
          ) : (
            <FlatList
              data={currentAssets}
              keyExtractor={(item) => `asset-${item.id}`}
              refreshControl={<RefreshControl refreshing={refreshing} onRefresh={load} />}
              renderItem={({ item }) => (
                <Pressable style={styles.card} onPress={() => setSelectedAsset(item)}>
                  <Text style={styles.name}>{item.name}</Text>
                  <Text style={styles.meta}>Инв. номер: {item.inventory_number}</Text>
                  <Text style={styles.meta}>Статус: {getStatusRu(item.status)}</Text>
                </Pressable>
              )}
              ListEmptyComponent={<Text style={styles.empty}>В помещении пока нет активов</Text>}
            />
          )}
        </>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 12, backgroundColor: colors.background },
  title: { color: colors.textPrimary, fontSize: 20, fontWeight: "700", marginBottom: 8 },
  row: { flexDirection: "row", gap: 8, marginBottom: 8 },
  breadcrumbButton: { paddingVertical: 6, paddingHorizontal: 8, borderWidth: 1, borderColor: colors.border, borderRadius: 8 },
  breadcrumbText: { color: colors.accent, fontWeight: "600" },
  card: { backgroundColor: colors.surface, borderRadius: 10, padding: 12, marginBottom: 10, borderWidth: 1, borderColor: colors.border },
  name: { fontWeight: "700", marginBottom: 4, color: colors.textPrimary },
  meta: { color: colors.textSecondary },
  empty: { color: colors.textSecondary, marginTop: 10 },
  error: { color: colors.danger, marginBottom: 8 },
});
