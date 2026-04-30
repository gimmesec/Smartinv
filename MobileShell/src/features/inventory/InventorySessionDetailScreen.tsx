import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Alert, FlatList, Modal, Pressable, SafeAreaView, ScrollView, StyleSheet, Text, View } from "react-native";
import { api } from "../../shared/api/client";
import { API_BASE_URL } from "../../shared/config";
import { AssetPhotoGallery } from "../../shared/components/AssetPhotoGallery";
import { colors } from "../../shared/theme";
import { Asset, InventoryItemResponse, InventorySession } from "../../shared/types";

type Props = {
  session: InventorySession;
  onBack: () => void;
};

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

function statusRu(status: string) {
  const map: Record<string, string> = {
    draft: "Черновик",
    in_progress: "В процессе",
    completed: "Завершена",
  };
  return map[status] ?? status;
}

function conditionRu(condition: string) {
  const map: Record<string, string> = {
    ok: "Исправен",
    damaged: "Поврежден",
    absent: "Отсутствует",
  };
  return map[condition] ?? condition;
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

export function InventorySessionDetailScreen({ session, onBack }: Props) {
  const [items, setItems] = useState<InventoryItemResponse[]>([]);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [loading, setLoading] = useState(true);
  const [detailAsset, setDetailAsset] = useState<Asset | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [itemsRes, assetsRes] = await Promise.all([
        api.get<InventoryItemResponse[]>("/inventory-items/", { params: { session: session.id } }),
        api.get<Asset[]>("/assets/", { params: { legal_entity: session.legal_entity } }),
      ]);
      setItems(itemsRes.data);
      setAssets(assetsRes.data);
    } finally {
      setLoading(false);
    }
  }, [session.id, session.legal_entity]);

  useEffect(() => {
    load();
  }, [load]);

  const assetsMap = useMemo(() => {
    const map = new Map<number, Asset>();
    assets.forEach((asset) => map.set(asset.id, asset));
    return map;
  }, [assets]);

  const resolveAsset = (item: InventoryItemResponse) => item.asset_detail ?? assetsMap.get(item.asset) ?? null;

  return (
    <SafeAreaView style={styles.container}>
      <Pressable onPress={onBack} style={styles.backButton}>
        <Text style={styles.backText}>{"<"} К списку сессий</Text>
      </Pressable>
      <Text style={styles.title}>Инвентаризация #{session.id}</Text>
      <Text style={styles.meta}>Статус: {statusRu(session.status)}</Text>
      <Text style={styles.meta}>Дата проведения: {session.started_at ? new Date(session.started_at).toLocaleString("ru-RU") : "не указана"}</Text>
      {session.status === "in_progress" ? (
        <Text style={styles.hint}>Чтобы перевести сессию в «Завершена», откройте сканирование и нажмите «Завершить инвентаризацию».</Text>
      ) : null}

      <Text style={styles.subtitle}>Предметы в сессии</Text>
      {loading ? (
        <Text style={styles.meta}>Загрузка...</Text>
      ) : (
        <FlatList
          data={items}
          keyExtractor={(item) => String(item.id)}
          renderItem={({ item }) => {
            const asset = resolveAsset(item);
            const title =
              asset?.name ||
              (item.detected_inventory_number ? `По коду: ${item.detected_inventory_number}` : `Запись #${item.id}`);
            const inv = asset?.inventory_number || item.detected_inventory_number || "—";
            return (
              <Pressable
                style={styles.card}
                onPress={() => {
                  if (asset) {
                    setDetailAsset(asset);
                  } else {
                    Alert.alert(
                      "Нет данных об активе",
                      "Карточка не загрузилась. Обновите экран или проверьте, что актив существует в справочнике."
                    );
                  }
                }}
              >
                <Text style={styles.cardTitle}>{title}</Text>
                <Text style={styles.meta}>Статус по факту: {conditionRu(item.condition)}</Text>
                <Text style={styles.meta}>Инв. номер: {inv}</Text>
                <Text style={styles.tapHint}>{asset ? "Нажмите, чтобы открыть карточку актива" : "Нажмите для подсказки"}</Text>
              </Pressable>
            );
          }}
          ListEmptyComponent={<Text style={styles.meta}>В этой сессии пока нет записей инвентаризации.</Text>}
          contentContainerStyle={{ paddingBottom: 20 }}
        />
      )}

      <Modal visible={detailAsset !== null} animationType="slide" onRequestClose={() => setDetailAsset(null)}>
        <SafeAreaView style={styles.modalRoot}>
          <View style={styles.modalHeader}>
            <Pressable onPress={() => setDetailAsset(null)} style={styles.modalBack}>
              <Text style={styles.modalBackText}>Закрыть</Text>
            </Pressable>
            <Text style={styles.modalTitle} numberOfLines={1}>
              {detailAsset?.name}
            </Text>
          </View>
          {detailAsset ? (
            <ScrollView contentContainerStyle={styles.modalBody}>
              <Text style={styles.modalMeta}>Инв. номер: {detailAsset.inventory_number}</Text>
              <Text style={styles.modalMeta}>Статус в учёте: {getStatusRu(detailAsset.status)}</Text>
              <Text style={styles.modalMeta}>Описание: {detailAsset.description || "—"}</Text>
              <AssetPhotoGallery
                assetId={detailAsset.id}
                sessionId={session.id}
                basePhotoUrl={toMediaUrl(detailAsset.photo)}
                toMediaUrl={toMediaUrl}
              />
            </ScrollView>
          ) : null}
        </SafeAreaView>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background, padding: 12 },
  backButton: { alignSelf: "flex-start", borderWidth: 1, borderColor: colors.border, borderRadius: 8, paddingHorizontal: 8, paddingVertical: 6, marginBottom: 8 },
  backText: { color: colors.accent, fontWeight: "600" },
  title: { color: colors.textPrimary, fontWeight: "700", fontSize: 20 },
  subtitle: { color: colors.textPrimary, fontWeight: "700", marginTop: 12, marginBottom: 8 },
  meta: { color: colors.textSecondary, marginTop: 2 },
  hint: { color: colors.textSecondary, marginTop: 8, fontSize: 13, lineHeight: 18 },
  card: { borderWidth: 1, borderColor: colors.border, borderRadius: 10, padding: 10, marginBottom: 8, backgroundColor: colors.surface },
  cardTitle: { color: colors.textPrimary, fontWeight: "700", marginBottom: 4 },
  tapHint: { color: colors.accent, fontSize: 12, marginTop: 6, fontWeight: "600" },
  modalRoot: { flex: 1, backgroundColor: colors.background },
  modalHeader: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    paddingHorizontal: 12,
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
    backgroundColor: colors.surface,
  },
  modalBack: { paddingVertical: 6, paddingHorizontal: 8 },
  modalBackText: { color: colors.accent, fontWeight: "700" },
  modalTitle: { flex: 1, color: colors.textPrimary, fontWeight: "700", fontSize: 16 },
  modalBody: { padding: 12, gap: 8, paddingBottom: 32 },
  modalMeta: { color: colors.textSecondary },
});
