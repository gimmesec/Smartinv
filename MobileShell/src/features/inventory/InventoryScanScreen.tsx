import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  Alert,
  FlatList,
  Image,
  Modal,
  Pressable,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { Camera } from "react-native-camera-kit";
import { launchCamera } from "react-native-image-picker";
import { api } from "../../shared/api/client";
import { API_BASE_URL } from "../../shared/config";
import { colors } from "../../shared/theme";
import { Asset, InventoryItemResponse, InventorySession, Location } from "../../shared/types";

type Props = {
  sessionId: number;
  /** После успешного «Завершить инвентаризацию» */
  onFinish: () => void;
  /** Выйти из экрана сканирования (сессия остаётся «В процессе», если не завершена) */
  onExit: () => void;
};

const CONDITION_OPTIONS = [
  { value: "ok", label: "Исправен" },
  { value: "damaged", label: "Поврежден" },
];

function toMediaUrl(photoPath: string | null | undefined) {
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

export function InventoryScanScreen({ sessionId, onFinish, onExit }: Props) {
  const [hasPermission, setHasPermission] = useState<boolean | null>(null);
  const [session, setSession] = useState<InventorySession | null>(null);
  const [items, setItems] = useState<InventoryItemResponse[]>([]);
  const [locations, setLocations] = useState<Location[]>([]);
  const [assetsPool, setAssetsPool] = useState<Asset[]>([]);
  const [resolvedAsset, setResolvedAsset] = useState<Asset | null>(null);
  const [conditionPickerVisible, setConditionPickerVisible] = useState(false);
  const [missingModalVisible, setMissingModalVisible] = useState(false);
  const [scannedCode, setScannedCode] = useState("");
  const [condition, setCondition] = useState("ok");
  const [comment, setComment] = useState("");
  const [saving, setSaving] = useState(false);
  const [uploadingPhoto, setUploadingPhoto] = useState(false);

  const loadData = useCallback(async () => {
    const sessionRes = await api.get<InventorySession>(`/inventory-sessions/${sessionId}/`);
    const legalEntityId = sessionRes.data.legal_entity;
    const [itemsRes, locationsRes, assetsRes] = await Promise.all([
      api.get<InventoryItemResponse[]>("/inventory-items/", { params: { session: sessionId } }),
      api.get<Location[]>("/locations/", { params: { legal_entity: legalEntityId } }),
      api.get<Asset[]>("/assets/", { params: { legal_entity: legalEntityId } }),
    ]);
    setSession(sessionRes.data);
    setItems(itemsRes.data);
    setLocations(locationsRes.data);
    setAssetsPool(assetsRes.data);
  }, [sessionId]);

  useEffect(() => {
    (async () => {
      setHasPermission(true);
      await loadData();
    })();
  }, [loadData]);

  const scannerEnabled = useMemo(() => hasPermission === true, [hasPermission]);

  const currentItem = useMemo(() => {
    if (!resolvedAsset?.id) {
      return null;
    }
    return items.find((item) => item.asset === resolvedAsset.id) || null;
  }, [items, resolvedAsset?.id]);

  const selectedConditionLabel =
    CONDITION_OPTIONS.find((item) => item.value === condition)?.label || CONDITION_OPTIONS[0].label;

  const expectedAssets = useMemo(() => {
    if (!session) {
      return [];
    }
    const pool = assetsPool.filter((a) => a.status !== "written_off");
    if (session.location) {
      return pool.filter((a) => a.location === session.location);
    }
    return pool;
  }, [session, assetsPool]);

  const missingAssets = useMemo(() => {
    const scannedIds = new Set(items.map((i) => i.asset));
    return expectedAssets.filter((a) => !scannedIds.has(a.id));
  }, [expectedAssets, items]);

  const sessionLocationLabel = useMemo(() => {
    if (!session?.location) {
      return "Область: всё юрлицо";
    }
    const loc = locations.find((l) => l.id === session.location);
    return `Область: ${loc?.name || `помещение #${session.location}`}`;
  }, [session, locations]);

  const findAssetByCode = async (code: string) => {
    const cleanCode = code.trim();
    if (!cleanCode || !session?.legal_entity) {
      return null;
    }
    const found =
      assetsPool.find(
        (asset) => asset.inventory_number === cleanCode || asset.qr_code === cleanCode || asset.barcode === cleanCode
      ) || null;
    setResolvedAsset(found);
    return found;
  };

  /** Строка инвентаризации для текущего актива (создаётся при необходимости — до «Далее» можно сделать фото). */
  const ensureInventoryItem = async (found: Asset): Promise<InventoryItemResponse> => {
    const itemsRes = await api.get<InventoryItemResponse[]>("/inventory-items/", { params: { session: sessionId } });
    const existing = itemsRes.data.find((row) => row.asset === found.id);
    if (existing) {
      setItems(itemsRes.data);
      return existing;
    }
    const createRes = await api.post<InventoryItemResponse>("/inventory-items/", {
      session: sessionId,
      asset: found.id,
      detected: true,
      detected_inventory_number: found.inventory_number,
      condition,
      comment,
      ocr_text: scannedCode.trim() || found.inventory_number,
    });
    await loadData();
    return createRes.data;
  };

  const submit = async () => {
    try {
      const found = resolvedAsset || (await findAssetByCode(scannedCode));
      if (!found) {
        Alert.alert("Не найдено", "Актив с таким кодом не найден в вашем юрлице.");
        return;
      }
      setSaving(true);
      const row = await ensureInventoryItem(found);
      await api.patch(`/inventory-items/${row.id}/`, {
        detected: true,
        detected_inventory_number: found.inventory_number,
        condition,
        comment,
        ocr_text: scannedCode.trim() || found.inventory_number,
      });
      await api.post(`/inventory-items/${row.id}/ai-analyze/`);
      setComment("");
      setResolvedAsset(null);
      setScannedCode("");
      await loadData();
    } catch {
      Alert.alert("Ошибка", "Не удалось сохранить инвентаризацию.");
    } finally {
      setSaving(false);
    }
  };

  const makePhoto = async () => {
    const found = resolvedAsset || (await findAssetByCode(scannedCode));
    if (!found) {
      Alert.alert("Сначала найдите актив", "Отсканируйте или введите код и нажмите «Найти актив».");
      return;
    }
    const result = await launchCamera({
      mediaType: "photo",
      cameraType: "back",
      saveToPhotos: false,
      quality: 0.7,
    });
    const photo = result.assets?.[0];
    if (!photo?.uri) {
      return;
    }
    try {
      setUploadingPhoto(true);
      const row = await ensureInventoryItem(found);
      const formData = new FormData();
      formData.append("photo", {
        uri: photo.uri,
        type: photo.type || "image/jpeg",
        name: photo.fileName || `inventory-item-${row.id}.jpg`,
      } as any);
      await api.patch(`/inventory-items/${row.id}/`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      await loadData();
    } catch {
      Alert.alert("Ошибка", "Не удалось загрузить фото.");
    } finally {
      setUploadingPhoto(false);
    }
  };

  const finishSession = async () => {
    try {
      await api.post(`/inventory-sessions/${sessionId}/complete/`);
      await loadData();
      Alert.alert("Готово", "Инвентаризация переведена в статус «Завершена».", [{ text: "OK", onPress: onFinish }]);
    } catch {
      Alert.alert("Ошибка", "Не удалось завершить инвентаризацию.");
    }
  };

  const confirmExit = () => {
    Alert.alert("Выйти из сканирования?", "Сессия останется в статусе «В процессе», если вы её не завершили. Прогресс сохранён.", [
      { text: "Отмена", style: "cancel" },
      { text: "Выйти", style: "destructive", onPress: onExit },
    ]);
  };

  const confirmFinish = () => {
    Alert.alert("Завершить инвентаризацию?", "Статус сессии станет «Завершена». После этого добавлять сканы в эту сессию будет нельзя.", [
      { text: "Отмена", style: "cancel" },
      { text: "Завершить", onPress: () => void finishSession() },
    ]);
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.topBar}>
        <Pressable onPress={confirmExit} style={styles.topBarBtn}>
          <Text style={styles.topBarBtnText}>Выйти</Text>
        </Pressable>
        <View style={styles.topBarCenter}>
          <Text style={styles.topBarTitle}>Сессия #{sessionId}</Text>
          <Text style={styles.topBarMeta}>{session ? `Статус: ${statusRu(session.status)}` : "…"}</Text>
          {session ? <Text style={styles.topBarMeta}>{sessionLocationLabel}</Text> : null}
        </View>
        <View style={styles.topBarSpacer} />
      </View>

      <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
        <Text style={styles.stepsTitle}>Как пройти шаг</Text>
        <Text style={styles.caption}>
          1) Отсканируйте или введите код → «Найти актив».{"\n"}
          2) При необходимости нажмите «Сделать фото» (камера откроется сразу; строка создаётся автоматически) — или
          пропустите фото.{"\n"}
          3) Выберите состояние и нажмите «Далее» — это сохраняет отметку и запускает проверку по тексту.
        </Text>

        <Pressable style={styles.finishBanner} onPress={confirmFinish}>
          <Text style={styles.finishBannerTitle}>Завершить инвентаризацию</Text>
          <Text style={styles.finishBannerHint}>Нажмите здесь, когда всё отсканировано — статус станет «Завершена»</Text>
        </Pressable>

        {missingAssets.length > 0 ? (
          <Pressable style={styles.warningBanner} onPress={() => setMissingModalVisible(true)}>
            <Text style={styles.warningTitle}>Внимание</Text>
            <Text style={styles.warningText}>
              Не обнаружено предметов: {missingAssets.length}. Нажмите, чтобы посмотреть список с фото.
            </Text>
          </Pressable>
        ) : null}

        {scannerEnabled ? (
          <Camera
            style={styles.scanner}
            scanBarcode
            onReadCode={(event: { nativeEvent: { codeStringValue: string } }) => {
              const code = event.nativeEvent.codeStringValue;
              setScannedCode(code);
              setResolvedAsset(null);
            }}
          />
        ) : (
          <Text style={styles.muted}>Камера недоступна. Используйте ручной ввод кода.</Text>
        )}

        <TextInput
          style={styles.input}
          value={scannedCode}
          onChangeText={(value) => {
            setScannedCode(value);
            setResolvedAsset(null);
          }}
          placeholder="QR / штрихкод / инв. номер"
          placeholderTextColor={colors.textSecondary}
        />
        <Pressable
          style={[styles.lookupButton, !scannedCode.trim() && { opacity: 0.6 }]}
          disabled={!scannedCode.trim()}
          onPress={async () => {
            const found = await findAssetByCode(scannedCode);
            if (!found) {
              Alert.alert("Не найдено", "Актив с таким кодом не найден.");
            }
          }}
        >
          <Text style={styles.lookupText}>Найти актив</Text>
        </Pressable>
        <Pressable style={styles.input} onPress={() => setConditionPickerVisible(true)}>
          <Text style={styles.inputText}>Состояние по факту: {selectedConditionLabel}</Text>
        </Pressable>
        <TextInput
          style={styles.input}
          value={comment}
          onChangeText={setComment}
          placeholder="Комментарий (необязательно)"
          placeholderTextColor={colors.textSecondary}
        />

        {resolvedAsset ? (
          <View style={styles.selectedCard}>
            <Text style={styles.selectedTitle}>Текущий актив: {resolvedAsset.name}</Text>
            <Text style={styles.meta}>Инв. номер: {resolvedAsset.inventory_number}</Text>
            <Text style={styles.meta}>Строка в сессии: {currentItem ? "есть (можно фото и «Далее»)" : "появится после «Сделать фото» или «Далее»"}</Text>
          </View>
        ) : null}

        <View style={styles.summaryCard}>
          <Text style={styles.summaryTitle}>Итог по сессии</Text>
          <Text style={styles.meta}>Отмечено в инвентаризации: {items.length}</Text>
          {session?.location ? (
            <Text style={styles.metaSmall}>Ожидается по локации сессии: {expectedAssets.length} активов</Text>
          ) : (
            <Text style={styles.metaSmall}>Ожидается по юрлицу: {expectedAssets.length} активов (кроме списанных)</Text>
          )}
        </View>

        <View style={styles.bottomRow}>
          <Pressable style={[styles.actionButton, saving && { opacity: 0.7 }]} onPress={submit} disabled={saving}>
            <Text style={styles.actionText}>{saving ? "Сохраняем..." : "Далее"}</Text>
          </Pressable>
          <Pressable style={[styles.photoButton, uploadingPhoto && { opacity: 0.7 }]} onPress={makePhoto} disabled={uploadingPhoto}>
            <Text style={styles.photoText}>{uploadingPhoto ? "Загрузка..." : "Сделать фото"}</Text>
          </Pressable>
        </View>
        <Text style={styles.photoHint}>«Сделать фото» открывает камеру сразу. Закройте камеру без снимка, если фото не нужно.</Text>
      </ScrollView>

      <Modal visible={conditionPickerVisible} transparent animationType="fade" onRequestClose={() => setConditionPickerVisible(false)}>
        <Pressable style={styles.modalBackdrop} onPress={() => setConditionPickerVisible(false)}>
          <View style={styles.modalCard}>
            <Text style={styles.modalTitle}>Выберите состояние</Text>
            {CONDITION_OPTIONS.map((option) => (
              <Pressable
                key={option.value}
                style={[styles.modalOption, condition === option.value && styles.modalOptionActive]}
                onPress={() => {
                  setCondition(option.value);
                  setConditionPickerVisible(false);
                }}
              >
                <Text style={styles.modalOptionText}>{option.label}</Text>
              </Pressable>
            ))}
          </View>
        </Pressable>
      </Modal>

      <Modal visible={missingModalVisible} animationType="slide" onRequestClose={() => setMissingModalVisible(false)}>
        <SafeAreaView style={styles.missingModal}>
          <View style={styles.missingHeader}>
            <Text style={styles.missingTitle}>Не обнаружено ({missingAssets.length})</Text>
            <Pressable onPress={() => setMissingModalVisible(false)} style={styles.missingClose}>
              <Text style={styles.missingCloseText}>Закрыть</Text>
            </Pressable>
          </View>
          <FlatList
            data={missingAssets}
            keyExtractor={(a) => String(a.id)}
            contentContainerStyle={styles.missingList}
            renderItem={({ item }) => {
              const uri = toMediaUrl(item.photo);
              return (
                <View style={styles.missingCard}>
                  {uri ? <Image source={{ uri }} style={styles.missingPhoto} resizeMode="cover" /> : <View style={styles.missingPhotoPlaceholder} />}
                  <Text style={styles.missingName}>{item.name}</Text>
                  <Text style={styles.missingMeta}>Инв. номер: {item.inventory_number}</Text>
                </View>
              );
            }}
            ListEmptyComponent={<Text style={styles.meta}>Все ожидаемые активы отмечены.</Text>}
          />
        </SafeAreaView>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },
  topBar: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 10,
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
    backgroundColor: colors.surface,
  },
  topBarBtn: { paddingVertical: 8, paddingHorizontal: 10 },
  topBarBtnText: { color: colors.accent, fontWeight: "700" },
  topBarCenter: { flex: 1, alignItems: "center" },
  topBarSpacer: { width: 56 },
  topBarTitle: { color: colors.textPrimary, fontWeight: "700", fontSize: 15 },
  topBarMeta: { color: colors.textSecondary, fontSize: 12 },
  scroll: { padding: 12, gap: 8, paddingBottom: 32 },
  stepsTitle: { color: colors.textPrimary, fontWeight: "700", fontSize: 16 },
  caption: { color: colors.textSecondary, marginBottom: 4, lineHeight: 20 },
  finishBanner: {
    borderWidth: 1,
    borderColor: colors.success,
    backgroundColor: "rgba(34, 197, 94, 0.12)",
    borderRadius: 10,
    padding: 12,
    gap: 4,
  },
  finishBannerTitle: { color: colors.success, fontWeight: "800", fontSize: 16 },
  finishBannerHint: { color: colors.textPrimary, fontSize: 13 },
  warningBanner: {
    borderWidth: 1,
    borderColor: colors.danger,
    backgroundColor: "rgba(220, 53, 69, 0.12)",
    borderRadius: 10,
    padding: 12,
    gap: 4,
  },
  warningTitle: { color: colors.danger, fontWeight: "800", fontSize: 15 },
  warningText: { color: colors.textPrimary, fontWeight: "600" },
  scanner: { height: 150, borderRadius: 8, overflow: "hidden", borderWidth: 1, borderColor: colors.border },
  input: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 8,
    padding: 10,
    color: colors.textPrimary,
    backgroundColor: colors.inputBackground,
  },
  inputText: { color: colors.textPrimary },
  muted: { color: colors.textSecondary },
  selectedCard: { borderWidth: 1, borderColor: colors.border, borderRadius: 8, padding: 10, backgroundColor: colors.surface },
  selectedTitle: { color: colors.textPrimary, fontWeight: "700", marginBottom: 4 },
  meta: { color: colors.textSecondary },
  metaSmall: { color: colors.textSecondary, fontSize: 12 },
  lookupButton: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 8,
    backgroundColor: colors.surface,
    alignItems: "center",
    justifyContent: "center",
    paddingVertical: 10,
  },
  lookupText: { color: colors.textPrimary, fontWeight: "700" },
  summaryCard: { borderWidth: 1, borderColor: colors.border, borderRadius: 8, padding: 10, backgroundColor: colors.surface },
  summaryTitle: { color: colors.textPrimary, fontWeight: "700", marginBottom: 4 },
  bottomRow: { flexDirection: "row", gap: 8, marginTop: 4 },
  actionButton: { flex: 1, backgroundColor: colors.accent, borderRadius: 8, alignItems: "center", justifyContent: "center", paddingVertical: 12 },
  actionText: { color: "#fff", fontWeight: "700" },
  photoButton: { width: 120, borderWidth: 1, borderColor: colors.border, borderRadius: 8, alignItems: "center", justifyContent: "center", paddingVertical: 12, backgroundColor: colors.surface },
  photoText: { color: colors.textPrimary, fontWeight: "700", fontSize: 12 },
  photoHint: { color: colors.textSecondary, fontSize: 12, marginTop: 4 },
  modalBackdrop: { flex: 1, backgroundColor: "rgba(0,0,0,0.5)", justifyContent: "center", padding: 16 },
  modalCard: { borderRadius: 12, padding: 12, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border, gap: 8 },
  modalTitle: { color: colors.textPrimary, fontWeight: "700", marginBottom: 4 },
  modalOption: { borderWidth: 1, borderColor: colors.border, borderRadius: 8, padding: 10 },
  modalOptionActive: { borderColor: colors.accent, backgroundColor: colors.surfaceAlt },
  modalOptionText: { color: colors.textPrimary, fontWeight: "600" },
  missingModal: { flex: 1, backgroundColor: colors.background },
  missingHeader: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: 12,
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  missingTitle: { color: colors.textPrimary, fontSize: 18, fontWeight: "700" },
  missingClose: { paddingHorizontal: 12, paddingVertical: 8 },
  missingCloseText: { color: colors.accent, fontWeight: "700" },
  missingList: { padding: 12, gap: 12 },
  missingCard: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 10,
    padding: 10,
    backgroundColor: colors.surface,
    gap: 6,
  },
  missingPhoto: { width: "100%", height: 160, borderRadius: 8, backgroundColor: colors.inputBackground },
  missingPhotoPlaceholder: { width: "100%", height: 100, borderRadius: 8, backgroundColor: colors.inputBackground },
  missingName: { color: colors.textPrimary, fontWeight: "700" },
  missingMeta: { color: colors.textSecondary },
});
