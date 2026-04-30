import React, { useEffect, useState } from "react";
import { Alert, Pressable, SafeAreaView, ScrollView, StyleSheet, Text, TextInput, View } from "react-native";
import { api } from "../../shared/api/client";
import { colors } from "../../shared/theme";
import { LegalEntity } from "../../shared/types";

export function AdminCreateLegalEntityScreen() {
  const [items, setItems] = useState<LegalEntity[]>([]);
  const [name, setName] = useState("");
  const [taxId, setTaxId] = useState("");
  const [kpp, setKpp] = useState("");
  const [address, setAddress] = useState("");
  const [saving, setSaving] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);

  const load = async () => {
    const res = await api.get<LegalEntity[]>("/legal-entities/");
    setItems(res.data);
  };

  useEffect(() => {
    load();
  }, []);

  const submit = async () => {
    if (!name.trim() || !taxId.trim()) {
      Alert.alert("Ошибка", "Заполните обязательные поля: название и ИНН.");
      return;
    }
    setSaving(true);
    try {
      await api.post("/legal-entities/", {
        name: name.trim(),
        tax_id: taxId.trim(),
        kpp: kpp.trim(),
        address: address.trim(),
      });
      Alert.alert("Готово", "Юрлицо создано.");
      setName("");
      setTaxId("");
      setKpp("");
      setAddress("");
      await load();
    } catch (error: any) {
      const detail = error?.response?.data?.detail || error?.response?.data?.tax_id?.[0] || "Не удалось создать юрлицо.";
      Alert.alert("Ошибка", detail);
    } finally {
      setSaving(false);
    }
  };

  const updateEntity = async (id: number) => {
    if (!name.trim() || !taxId.trim()) {
      Alert.alert("Ошибка", "Для изменения заполните обязательные поля: название и ИНН.");
      return;
    }
    setSaving(true);
    try {
      await api.patch(`/legal-entities/${id}/`, {
        name: name.trim(),
        tax_id: taxId.trim(),
        kpp: kpp.trim(),
        address: address.trim(),
      });
      Alert.alert("Готово", "Юрлицо обновлено.");
      setEditingId(null);
      setName("");
      setTaxId("");
      setKpp("");
      setAddress("");
      await load();
    } catch (error: any) {
      const detail = error?.response?.data?.detail || "Не удалось обновить юрлицо.";
      Alert.alert("Ошибка", detail);
    } finally {
      setSaving(false);
    }
  };

  const removeEntity = async (id: number) => {
    Alert.alert("Удалить юрлицо?", "Действие необратимо.", [
      { text: "Отмена", style: "cancel" },
      {
        text: "Удалить",
        style: "destructive",
        onPress: async () => {
          try {
            await api.delete(`/legal-entities/${id}/`);
            await load();
          } catch (error: any) {
            const detail = error?.response?.data?.detail || "Не удалось удалить юрлицо.";
            Alert.alert("Ошибка", detail);
          }
        },
      },
    ]);
  };

  const startEdit = (item: LegalEntity) => {
    setEditingId(item.id);
    setName(item.name || "");
    setTaxId(item.tax_id || "");
    setKpp((item as any).kpp || "");
    setAddress((item as any).address || "");
  };

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.content}>
        <Text style={styles.title}>Добавить юрлицо</Text>
        <TextInput
          style={styles.input}
          value={name}
          onChangeText={setName}
          placeholder="Название"
          placeholderTextColor={colors.textSecondary}
        />
        <TextInput
          style={styles.input}
          value={taxId}
          onChangeText={setTaxId}
          placeholder="ИНН"
          placeholderTextColor={colors.textSecondary}
        />
        <TextInput style={styles.input} value={kpp} onChangeText={setKpp} placeholder="КПП" placeholderTextColor={colors.textSecondary} />
        <TextInput
          style={styles.input}
          value={address}
          onChangeText={setAddress}
          placeholder="Адрес"
          placeholderTextColor={colors.textSecondary}
        />
        <Pressable
          style={[styles.button, saving && { opacity: 0.7 }]}
          onPress={() => (editingId ? updateEntity(editingId) : submit())}
          disabled={saving}
        >
          <Text style={styles.buttonText}>{saving ? "Сохраняем..." : editingId ? "Сохранить изменения" : "Создать юрлицо"}</Text>
        </Pressable>
        {editingId ? (
          <Pressable
            style={styles.cancelButton}
            onPress={() => {
              setEditingId(null);
              setName("");
              setTaxId("");
              setKpp("");
              setAddress("");
            }}
          >
            <Text style={styles.cancelButtonText}>Отменить редактирование</Text>
          </Pressable>
        ) : null}

        <Text style={styles.subtitle}>Существующие юрлица</Text>
        {items.map((item) => (
          <View key={item.id} style={styles.card}>
            <Text style={styles.cardTitle}>{item.name}</Text>
            <Text style={styles.meta}>ИНН: {item.tax_id}</Text>
            <View style={styles.row}>
              <Pressable style={styles.secondaryButton} onPress={() => startEdit(item)}>
                <Text style={styles.secondaryButtonText}>Изменить</Text>
              </Pressable>
              <Pressable style={styles.deleteButton} onPress={() => removeEntity(item.id)}>
                <Text style={styles.deleteButtonText}>Удалить</Text>
              </Pressable>
            </View>
          </View>
        ))}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },
  content: { padding: 12, gap: 10 },
  title: { color: colors.textPrimary, fontSize: 20, fontWeight: "700", marginBottom: 6 },
  subtitle: { color: colors.textPrimary, fontSize: 17, fontWeight: "700", marginTop: 12 },
  input: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 8,
    backgroundColor: colors.inputBackground,
    color: colors.textPrimary,
    padding: 10,
  },
  button: {
    marginTop: 8,
    backgroundColor: colors.accent,
    borderRadius: 10,
    paddingVertical: 12,
    alignItems: "center",
  },
  buttonText: { color: "#fff", fontWeight: "700" },
  cancelButton: {
    borderRadius: 10,
    borderWidth: 1,
    borderColor: colors.border,
    paddingVertical: 10,
    alignItems: "center",
    backgroundColor: colors.surface,
  },
  cancelButtonText: { color: colors.textPrimary, fontWeight: "600" },
  card: { backgroundColor: colors.surface, borderRadius: 10, padding: 12, borderWidth: 1, borderColor: colors.border, gap: 6 },
  cardTitle: { color: colors.textPrimary, fontWeight: "700" },
  meta: { color: colors.textSecondary },
  row: { flexDirection: "row", gap: 8, marginTop: 6 },
  secondaryButton: {
    borderRadius: 8,
    borderWidth: 1,
    borderColor: colors.border,
    paddingVertical: 8,
    paddingHorizontal: 10,
    backgroundColor: colors.surfaceAlt,
  },
  secondaryButtonText: { color: colors.textPrimary, fontWeight: "600" },
  deleteButton: {
    borderRadius: 8,
    paddingVertical: 8,
    paddingHorizontal: 10,
    backgroundColor: colors.danger,
  },
  deleteButtonText: { color: "#fff", fontWeight: "700" },
});
