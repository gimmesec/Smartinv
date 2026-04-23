import React, { useEffect, useMemo, useState } from "react";
import { FlatList, Pressable, SafeAreaView, StyleSheet, Text, View } from "react-native";
import { api } from "../../shared/api/client";
import { colors } from "../../shared/theme";
import { Asset, InventoryItemResponse, InventorySession } from "../../shared/types";

type Props = {
  session: InventorySession;
  onBack: () => void;
};

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

export function InventorySessionDetailScreen({ session, onBack }: Props) {
  const [items, setItems] = useState<InventoryItemResponse[]>([]);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
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
    })();
  }, [session.id, session.legal_entity]);

  const assetsMap = useMemo(() => {
    const map = new Map<number, Asset>();
    assets.forEach((asset) => map.set(asset.id, asset));
    return map;
  }, [assets]);

  return (
    <SafeAreaView style={styles.container}>
      <Pressable onPress={onBack} style={styles.backButton}>
        <Text style={styles.backText}>{"<"} К списку сессий</Text>
      </Pressable>
      <Text style={styles.title}>Инвентаризация #{session.id}</Text>
      <Text style={styles.meta}>Статус: {statusRu(session.status)}</Text>
      <Text style={styles.meta}>Дата проведения: {session.started_at ? new Date(session.started_at).toLocaleString("ru-RU") : "не указана"}</Text>

      <Text style={styles.subtitle}>Предметы в сессии</Text>
      {loading ? (
        <Text style={styles.meta}>Загрузка...</Text>
      ) : (
        <FlatList
          data={items}
          keyExtractor={(item) => String(item.id)}
          renderItem={({ item }) => {
            const asset = assetsMap.get(item.asset);
            return (
              <View style={styles.card}>
                <Text style={styles.cardTitle}>{asset?.name || `Актив #${item.asset}`}</Text>
                <Text style={styles.meta}>Статус: {conditionRu(item.condition)}</Text>
                <Text style={styles.meta}>Инв. номер: {asset?.inventory_number || item.detected_inventory_number || "-"}</Text>
                <Text style={styles.meta}>QR: {asset?.qr_code || "-"}</Text>
                <Text style={styles.meta}>Штрихкод: {asset?.barcode || "-"}</Text>
              </View>
            );
          }}
          ListEmptyComponent={<Text style={styles.meta}>В этой сессии пока нет записей инвентаризации.</Text>}
          contentContainerStyle={{ paddingBottom: 20 }}
        />
      )}
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
  card: { borderWidth: 1, borderColor: colors.border, borderRadius: 10, padding: 10, marginBottom: 8, backgroundColor: colors.surface },
  cardTitle: { color: colors.textPrimary, fontWeight: "700", marginBottom: 4 },
});
