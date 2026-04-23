import React, { useEffect, useMemo, useState } from "react";
import { Alert, Modal, Pressable, SafeAreaView, StyleSheet, Text, TextInput, View } from "react-native";
import { Camera } from "react-native-camera-kit";
import { launchCamera } from "react-native-image-picker";
import { api } from "../../shared/api/client";
import { colors } from "../../shared/theme";
import { Asset, InventoryItemResponse, InventorySession } from "../../shared/types";

type Props = {
  sessionId: number;
};

const CONDITION_OPTIONS = [
  { value: "ok", label: "Исправен" },
  { value: "damaged", label: "Поврежден" },
  { value: "absent", label: "Отсутствует" },
];

export function InventoryScanScreen({ sessionId }: Props) {
  const [hasPermission, setHasPermission] = useState<boolean | null>(null);
  const [session, setSession] = useState<InventorySession | null>(null);
  const [items, setItems] = useState<InventoryItemResponse[]>([]);
  const [resolvedAsset, setResolvedAsset] = useState<Asset | null>(null);
  const [conditionPickerVisible, setConditionPickerVisible] = useState(false);
  const [scannedCode, setScannedCode] = useState("");
  const [condition, setCondition] = useState("ok");
  const [comment, setComment] = useState("");
  const [saving, setSaving] = useState(false);
  const [uploadingPhoto, setUploadingPhoto] = useState(false);

  useEffect(() => {
    (async () => {
      // react-native-camera-kit requests permission from native layer.
      setHasPermission(true);
      await loadData();
    })();
  }, []);

  const scannerEnabled = useMemo(() => hasPermission === true, [hasPermission]);

  const currentItem = useMemo(() => {
    if (!resolvedAsset?.id) {
      return null;
    }
    return items.find((item) => item.asset === resolvedAsset.id) || null;
  }, [items, resolvedAsset?.id]);

  const selectedConditionLabel =
    CONDITION_OPTIONS.find((item) => item.value === condition)?.label || CONDITION_OPTIONS[0].label;

  const loadData = async () => {
    const sessionRes = await api.get<InventorySession>(`/inventory-sessions/${sessionId}/`);
    const itemsRes = await api.get<InventoryItemResponse[]>("/inventory-items/", { params: { session: sessionId } });
    setSession(sessionRes.data);
    setItems(itemsRes.data);
  };

  const findAssetByCode = async (code: string) => {
    const cleanCode = code.trim();
    if (!cleanCode || !session?.legal_entity) {
      return null;
    }
    const res = await api.get<Asset[]>("/assets/", { params: { legal_entity: session.legal_entity } });
    const found =
      res.data.find(
        (asset) => asset.inventory_number === cleanCode || asset.qr_code === cleanCode || asset.barcode === cleanCode
      ) || null;
    setResolvedAsset(found);
    return found;
  };

  const submit = async () => {
    try {
      const found = resolvedAsset || (await findAssetByCode(scannedCode));
      if (!found) {
        Alert.alert("Не найдено", "Актив с таким кодом не найден в вашем юрлице.");
        return;
      }
      setSaving(true);
      const existing = items.find((item) => item.asset === found.id);
      let itemId = existing?.id;
      if (existing) {
        await api.patch(`/inventory-items/${existing.id}/`, {
          detected: true,
          detected_inventory_number: found.inventory_number,
          condition,
          comment,
          ocr_text: scannedCode || found.inventory_number,
        });
      } else {
        const createRes = await api.post("/inventory-items/", {
          session: sessionId,
          asset: found.id,
          detected: true,
          detected_inventory_number: found.inventory_number,
          condition,
          comment,
          ocr_text: scannedCode || found.inventory_number,
        });
        itemId = createRes.data.id;
      }
      await api.post(`/inventory-items/${itemId}/ai-analyze/`);
      Alert.alert("Сохранено", `Актив ${found.inventory_number} добавлен в инвентаризацию.`);
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
      Alert.alert("Выберите актив", "Сначала отсканируйте/введите код актива и сохраните результат инвентаризации.");
      return;
    }
    const existing = items.find((item) => item.asset === found.id);
    if (!existing) {
      Alert.alert("Сначала сохраните", "Сначала нажмите 'Сохранить результат', чтобы создать запись по активу.");
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
      const formData = new FormData();
      formData.append("photo", {
        uri: photo.uri,
        type: photo.type || "image/jpeg",
        name: photo.fileName || `inventory-item-${existing.id}.jpg`,
      } as any);
      await api.patch(`/inventory-items/${existing.id}/`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      Alert.alert("Готово", "Фото обновлено.");
      await loadData();
    } catch {
      Alert.alert("Ошибка", "Не удалось загрузить фото.");
    } finally {
      setUploadingPhoto(false);
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <Text style={styles.title}>Сессия #{sessionId}</Text>
      <Text style={styles.caption}>
        Состав инвентаризации формируете вы: сканируйте или вводите код, фиксируйте состояние и сохраняйте.
      </Text>

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
        <Text style={styles.muted}>Камера недоступна. Используйте ручной ввод.</Text>
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
        <Text style={styles.inputText}>Статус: {selectedConditionLabel}</Text>
      </Pressable>
      <TextInput
        style={styles.input}
        value={comment}
        onChangeText={setComment}
        placeholder="Комментарий"
        placeholderTextColor={colors.textSecondary}
      />

      {resolvedAsset ? (
        <View style={styles.selectedCard}>
          <Text style={styles.selectedTitle}>Текущий актив: {resolvedAsset.name}</Text>
          <Text style={styles.meta}>Инв. номер: {resolvedAsset.inventory_number}</Text>
          <Text style={styles.meta}>
            Текущая запись: {currentItem ? "есть" : "пока нет"}
          </Text>
        </View>
      ) : null}

      <View style={styles.summaryCard}>
        <Text style={styles.summaryTitle}>Итог по сессии</Text>
        <Text style={styles.meta}>Добавлено в инвентаризацию: {items.length}</Text>
      </View>

      <View style={styles.bottomRow}>
        <Pressable style={[styles.actionButton, saving && { opacity: 0.7 }]} onPress={submit} disabled={saving}>
          <Text style={styles.actionText}>{saving ? "Сохраняем..." : "Сохранить результат"}</Text>
        </Pressable>
        <Pressable style={[styles.photoButton, uploadingPhoto && { opacity: 0.7 }]} onPress={makePhoto} disabled={uploadingPhoto}>
          <Text style={styles.photoText}>{uploadingPhoto ? "Загрузка..." : "Сделать фото"}</Text>
        </Pressable>
      </View>

      <Modal visible={conditionPickerVisible} transparent animationType="fade" onRequestClose={() => setConditionPickerVisible(false)}>
        <Pressable style={styles.modalBackdrop} onPress={() => setConditionPickerVisible(false)}>
          <View style={styles.modalCard}>
            <Text style={styles.modalTitle}>Выберите статус</Text>
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
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 12, gap: 8, backgroundColor: colors.background },
  title: { fontSize: 18, fontWeight: "700", color: colors.textPrimary },
  caption: { color: colors.textSecondary, marginBottom: 6 },
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
  modalBackdrop: { flex: 1, backgroundColor: "rgba(0,0,0,0.5)", justifyContent: "center", padding: 16 },
  modalCard: { borderRadius: 12, padding: 12, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border, gap: 8 },
  modalTitle: { color: colors.textPrimary, fontWeight: "700", marginBottom: 4 },
  modalOption: { borderWidth: 1, borderColor: colors.border, borderRadius: 8, padding: 10 },
  modalOptionActive: { borderColor: colors.accent, backgroundColor: colors.surfaceAlt },
  modalOptionText: { color: colors.textPrimary, fontWeight: "600" },
});
