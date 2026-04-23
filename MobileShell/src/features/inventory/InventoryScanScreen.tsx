import React, { useEffect, useMemo, useState } from "react";
import { Alert, Button, SafeAreaView, StyleSheet, Text, TextInput, View } from "react-native";
import { Camera } from "react-native-camera-kit";
import { api } from "../../shared/api/client";
import { colors } from "../../shared/theme";

type Props = {
  sessionId: number;
};

export function InventoryScanScreen({ sessionId }: Props) {
  const [hasPermission, setHasPermission] = useState<boolean | null>(null);
  const [scannedCode, setScannedCode] = useState("");
  const [condition, setCondition] = useState("ok");
  const [comment, setComment] = useState("");

  useEffect(() => {
    (async () => {
      // react-native-camera-kit requests permission from native layer.
      setHasPermission(true);
    })();
  }, []);

  const scannerEnabled = useMemo(() => hasPermission === true, [hasPermission]);

  const submit = async () => {
    try {
      if (!scannedCode.trim()) {
        Alert.alert("Ошибка", "Сначала отсканируйте или введите инвентарный номер.");
        return;
      }
      const assetRes = await api.get("/assets/");
      const found = (assetRes.data as any[]).find(
        (a) => a.inventory_number === scannedCode || a.qr_code === scannedCode || a.barcode === scannedCode
      );
      if (!found) {
        Alert.alert("Не найдено", "Актив с таким кодом не найден.");
        return;
      }

      const createRes = await api.post("/inventory-items/", {
        session: sessionId,
        asset: found.id,
        detected: true,
        detected_inventory_number: found.inventory_number,
        condition,
        comment,
        ocr_text: scannedCode,
      });

      const itemId = createRes.data.id;
      await api.post(`/inventory-items/${itemId}/ai-analyze/`);
      Alert.alert("Успешно", `Инвентаризация сохранена для актива ${found.inventory_number}.`);
      setComment("");
    } catch {
      Alert.alert("Ошибка", "Не удалось сохранить инвентаризацию.");
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <Text style={styles.title}>Сессия #{sessionId}</Text>
      <Text style={styles.caption}>Сканируйте QR/штрихкод или введите номер вручную.</Text>
      {scannerEnabled ? (
        <Camera
          style={styles.scanner}
          scanBarcode
          onReadCode={(event: { nativeEvent: { codeStringValue: string } }) => {
            setScannedCode(event.nativeEvent.codeStringValue);
          }}
        />
      ) : (
        <Text style={styles.muted}>Камера недоступна. Используйте ручной ввод.</Text>
      )}

      <TextInput
        style={styles.input}
        value={scannedCode}
        onChangeText={setScannedCode}
        placeholder="QR / штрихкод / инв. номер"
        placeholderTextColor={colors.textSecondary}
      />
      <TextInput
        style={styles.input}
        value={condition}
        onChangeText={setCondition}
        placeholder="condition: ok/damaged/absent"
        placeholderTextColor={colors.textSecondary}
      />
      <TextInput
        style={styles.input}
        value={comment}
        onChangeText={setComment}
        placeholder="Комментарий"
        placeholderTextColor={colors.textSecondary}
      />
      <View style={styles.button}>
        <Button title="Сохранить результат" onPress={submit} />
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 12, gap: 8, backgroundColor: colors.background },
  title: { fontSize: 18, fontWeight: "700", color: colors.textPrimary },
  caption: { color: colors.textSecondary, marginBottom: 6 },
  scanner: { height: 220, borderRadius: 8, overflow: "hidden", borderWidth: 1, borderColor: colors.border },
  input: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 8,
    padding: 10,
    color: colors.textPrimary,
    backgroundColor: colors.inputBackground,
  },
  muted: { color: colors.textSecondary },
  button: { marginTop: 4 },
});
