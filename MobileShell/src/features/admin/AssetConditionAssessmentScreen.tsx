import React, { useEffect, useMemo, useState } from "react";
import { Alert, FlatList, Pressable, RefreshControl, SafeAreaView, StyleSheet, Text, View } from "react-native";
import { api } from "../../shared/api/client";
import { colors } from "../../shared/theme";
import { Asset, AssetConditionJob, LegalEntity, Location } from "../../shared/types";

function getStatusLabel(status: string) {
  const map: Record<string, string> = {
    pending: "В очереди",
    vision_running: "Анализ фото",
    vision_done: "Фото обработано",
    llm_running: "Формирование комментария",
    completed: "Готово",
    failed: "Ошибка",
  };
  return map[status] ?? status;
}

export function AssetConditionAssessmentScreen() {
  const [entities, setEntities] = useState<LegalEntity[]>([]);
  const [locations, setLocations] = useState<Location[]>([]);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [jobsByAsset, setJobsByAsset] = useState<Record<number, AssetConditionJob>>({});
  const [selectedEntity, setSelectedEntity] = useState<number | null>(null);
  const [selectedLocation, setSelectedLocation] = useState<number | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [processingAssetId, setProcessingAssetId] = useState<number | null>(null);
  const [bulkRunning, setBulkRunning] = useState(false);

  const load = async () => {
    setRefreshing(true);
    try {
      const [entitiesRes, locationsRes, assetsRes] = await Promise.all([
        api.get<LegalEntity[]>("/legal-entities/"),
        api.get<Location[]>("/locations/"),
        api.get<Asset[]>("/assets/"),
      ]);
      setEntities(entitiesRes.data);
      setLocations(locationsRes.data);
      setAssets(assetsRes.data);
    } finally {
      setRefreshing(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const locationOptions = useMemo(() => locations.filter((location) => location.legal_entity === selectedEntity), [locations, selectedEntity]);

  const filteredAssets = useMemo(
    () =>
      assets.filter((asset) => {
        if (!selectedEntity) {
          return false;
        }
        if (asset.legal_entity !== selectedEntity) {
          return false;
        }
        if (selectedLocation && asset.location !== selectedLocation) {
          return false;
        }
        return true;
      }),
    [assets, selectedEntity, selectedLocation]
  );

  const fetchInsight = async (assetId: number) => {
    try {
      const res = await api.get<AssetConditionJob>(`/assets/${assetId}/condition-insight/`);
      setJobsByAsset((prev) => ({ ...prev, [assetId]: res.data }));
    } catch {
      setJobsByAsset((prev) => {
        const next = { ...prev };
        delete next[assetId];
        return next;
      });
    }
  };

  const runAssessment = async (assetId: number) => {
    setProcessingAssetId(assetId);
    try {
      const res = await api.post<AssetConditionJob>(`/assets/${assetId}/condition-analyze/`);
      setJobsByAsset((prev) => ({ ...prev, [assetId]: res.data }));
      Alert.alert("Запущено", "Анализ состояния запущен. Нажмите 'Обновить комментарий' через несколько секунд.");
    } catch (error: any) {
      const detail = error?.response?.data?.detail || "Не удалось запустить анализ.";
      Alert.alert("Ошибка", detail);
    } finally {
      setProcessingAssetId(null);
    }
  };

  const runBulkAssessment = async () => {
    if (!selectedEntity) {
      Alert.alert("Ошибка", "Сначала выберите юрлицо.");
      return;
    }
    setBulkRunning(true);
    try {
      const res = await api.post<{
        queued_count: number;
        skipped_no_photo: number;
      }>("/assets/condition-analyze-bulk/", {
        legal_entity_id: selectedEntity,
        location_id: selectedLocation,
      });
      Alert.alert(
        "Запущено",
        `Поставлено в очередь: ${res.data.queued_count}. Пропущено без фото: ${res.data.skipped_no_photo}.`
      );
    } catch (error: any) {
      const detail = error?.response?.data?.detail || "Не удалось запустить массовый анализ.";
      Alert.alert("Ошибка", detail);
    } finally {
      setBulkRunning(false);
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <Text style={styles.title}>Состояние активов</Text>

      <Text style={styles.label}>Юрлицо</Text>
      <View style={styles.wrap}>
        {entities.map((entity) => (
          <Pressable
            key={entity.id}
            style={[styles.chip, selectedEntity === entity.id && styles.chipSelected]}
            onPress={() => {
              setSelectedEntity(entity.id);
              setSelectedLocation(null);
            }}
          >
            <Text style={styles.chipText}>{entity.name}</Text>
          </Pressable>
        ))}
      </View>

      {selectedEntity ? (
        <>
          <Text style={styles.label}>Помещение (фильтр)</Text>
          <View style={styles.wrap}>
            <Pressable style={[styles.chip, selectedLocation === null && styles.chipSelected]} onPress={() => setSelectedLocation(null)}>
              <Text style={styles.chipText}>Все помещения</Text>
            </Pressable>
            {locationOptions.map((location) => (
              <Pressable
                key={location.id}
                style={[styles.chip, selectedLocation === location.id && styles.chipSelected]}
                onPress={() => setSelectedLocation(location.id)}
              >
                <Text style={styles.chipText}>{location.name}</Text>
              </Pressable>
            ))}
          </View>
          <Pressable style={[styles.button, bulkRunning && { opacity: 0.7 }]} onPress={runBulkAssessment} disabled={bulkRunning}>
            <Text style={styles.buttonText}>{bulkRunning ? "Запускаем..." : "Запустить анализ по списку"}</Text>
          </Pressable>
        </>
      ) : null}

      <FlatList
        data={filteredAssets}
        keyExtractor={(item) => String(item.id)}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={load} />}
        ListEmptyComponent={<Text style={styles.empty}>Выберите юрлицо для просмотра активов</Text>}
        renderItem={({ item }) => {
          const job = jobsByAsset[item.id];
          return (
            <View style={styles.card}>
              <Text style={styles.name}>{item.name}</Text>
              <Text style={styles.meta}>Инв. номер: {item.inventory_number}</Text>
              <Text style={styles.meta}>Статус задачи: {job ? getStatusLabel(job.status) : "Нет данных"}</Text>
              <Text style={styles.meta}>{job?.llm_summary ? `Комментарий: ${job.llm_summary}` : "Комментарий: ещё нет ответа"}</Text>
              <View style={styles.row}>
                <Pressable
                  style={[styles.button, processingAssetId === item.id && { opacity: 0.7 }]}
                  onPress={() => runAssessment(item.id)}
                  disabled={processingAssetId === item.id}
                >
                  <Text style={styles.buttonText}>{processingAssetId === item.id ? "Запускаем..." : "Запустить анализ"}</Text>
                </Pressable>
                <Pressable style={styles.secondaryButton} onPress={() => fetchInsight(item.id)}>
                  <Text style={styles.secondaryButtonText}>Обновить комментарий</Text>
                </Pressable>
              </View>
            </View>
          );
        }}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background, padding: 12 },
  title: { color: colors.textPrimary, fontSize: 20, fontWeight: "700", marginBottom: 8 },
  label: { color: colors.textPrimary, fontWeight: "600", marginTop: 4, marginBottom: 6 },
  wrap: { flexDirection: "row", flexWrap: "wrap", gap: 8, marginBottom: 8 },
  chip: {
    paddingHorizontal: 10,
    paddingVertical: 8,
    borderRadius: 8,
    borderColor: colors.border,
    borderWidth: 1,
    backgroundColor: colors.surface,
  },
  chipSelected: { borderColor: colors.accent, backgroundColor: colors.surfaceAlt },
  chipText: { color: colors.textPrimary },
  card: { backgroundColor: colors.surface, borderRadius: 10, padding: 12, marginBottom: 10, borderWidth: 1, borderColor: colors.border },
  name: { fontWeight: "700", marginBottom: 4, color: colors.textPrimary },
  meta: { color: colors.textSecondary, marginBottom: 2 },
  empty: { color: colors.textSecondary, marginTop: 10 },
  row: { flexDirection: "row", gap: 8, marginTop: 8 },
  button: {
    backgroundColor: colors.accent,
    borderRadius: 8,
    paddingVertical: 10,
    paddingHorizontal: 10,
    alignItems: "center",
    justifyContent: "center",
  },
  buttonText: { color: "#fff", fontWeight: "700" },
  secondaryButton: {
    borderRadius: 8,
    paddingVertical: 10,
    paddingHorizontal: 10,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.surfaceAlt,
    alignItems: "center",
    justifyContent: "center",
  },
  secondaryButtonText: { color: colors.textPrimary, fontWeight: "600" },
});
