import React, { useCallback, useMemo, useState } from "react";
import { FlatList, Image, Pressable, RefreshControl, SafeAreaView, StyleSheet, Text, View } from "react-native";
import { useAuth } from "../auth/AuthContext";
import { api } from "../../shared/api/client";
import { API_BASE_URL } from "../../shared/config";
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

function getLocationTypeRu(type: string) {
  const map: Record<string, string> = {
    office: "Офис",
    building: "Здание",
    floor: "Этаж",
    room: "Помещение",
  };
  return map[type] ?? type;
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

  const load = useCallback(async () => {
    setRefreshing(true);
    try {
      const [assetsRes, entitiesRes, locationsRes] = await Promise.all([
        api.get<Asset[]>("/assets/"),
        api.get<LegalEntity[]>("/legal-entities/"),
        api.get<Location[]>("/locations/"),
      ]);
      setItems(assetsRes.data);
      setEntities(entitiesRes.data);
      setLocations(locationsRes.data);
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

  const rootLocations = useMemo(() => {
    if (!selectedEntityId) {
      return [];
    }
    return locations.filter((loc) => loc.legal_entity === selectedEntityId && loc.parent === null);
  }, [locations, selectedEntityId]);

  const currentChildren = useMemo(() => {
    if (!selectedEntityId) {
      return [];
    }
    if (!selectedLocationId) {
      return rootLocations;
    }
    return locations.filter((loc) => loc.legal_entity === selectedEntityId && loc.parent === selectedLocationId);
  }, [locations, rootLocations, selectedEntityId, selectedLocationId]);

  const currentAssets = useMemo(() => {
    if (!selectedEntityId) {
      return [];
    }
    if (!selectedLocationId) {
      return items.filter((asset) => asset.legal_entity === selectedEntityId);
    }
    const queue = [selectedLocationId];
    const subtree = new Set<number>();
    while (queue.length) {
      const id = queue.shift() as number;
      if (subtree.has(id)) {
        continue;
      }
      subtree.add(id);
      locations
        .filter((loc) => loc.parent === id)
        .forEach((loc) => {
          queue.push(loc.id);
        });
    }
    return items.filter((asset) => asset.legal_entity === selectedEntityId && asset.location !== null && subtree.has(asset.location));
  }, [items, locations, selectedEntityId, selectedLocationId]);

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
          {photoUrl ? <Image source={{ uri: photoUrl }} style={styles.photo} resizeMode="cover" /> : <Text style={styles.meta}>Фото не загружено</Text>}
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <Text style={styles.title}>Активы</Text>
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
                  const current = locations.find((loc) => loc.id === selectedLocationId);
                  setSelectedLocationId(current?.parent ?? null);
                }}
                style={styles.breadcrumbButton}
              >
                <Text style={styles.breadcrumbText}>{"<"} Уровень выше</Text>
              </Pressable>
            ) : null}
          </View>
          <FlatList
            data={[...currentChildren.map((loc) => ({ type: "loc" as const, loc })), ...currentAssets.map((asset) => ({ type: "asset" as const, asset }))]}
            keyExtractor={(item) => (item.type === "loc" ? `loc-${item.loc.id}` : `asset-${item.asset.id}`)}
            refreshControl={<RefreshControl refreshing={refreshing} onRefresh={load} />}
            renderItem={({ item }) => {
              if (item.type === "loc") {
                return (
                  <Pressable style={styles.card} onPress={() => setSelectedLocationId(item.loc.id)}>
                    <Text style={styles.name}>{item.loc.name}</Text>
                    <Text style={styles.meta}>{getLocationTypeRu(item.loc.type)}</Text>
                  </Pressable>
                );
              }
              return (
                <Pressable style={styles.card} onPress={() => setSelectedAsset(item.asset)}>
                  <Text style={styles.name}>{item.asset.name}</Text>
                  <Text style={styles.meta}>Инв. номер: {item.asset.inventory_number}</Text>
                  <Text style={styles.meta}>Статус: {getStatusRu(item.asset.status)}</Text>
                </Pressable>
              );
            }}
            ListEmptyComponent={<Text style={styles.empty}>Нет локаций или активов на этом уровне</Text>}
          />
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
  photo: { width: "100%", height: 220, borderRadius: 10, marginTop: 10, borderWidth: 1, borderColor: colors.border },
});
