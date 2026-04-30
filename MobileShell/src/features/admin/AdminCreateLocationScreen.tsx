import React, { useEffect, useMemo, useState } from "react";
import { Alert, Pressable, SafeAreaView, ScrollView, StyleSheet, Text, TextInput, View } from "react-native";
import { api } from "../../shared/api/client";
import { colors } from "../../shared/theme";
import { LegalEntity, Location } from "../../shared/types";

export function AdminCreateLocationScreen() {
  const [entities, setEntities] = useState<LegalEntity[]>([]);
  const [locations, setLocations] = useState<Location[]>([]);
  const [selectedEntity, setSelectedEntity] = useState<number | null>(null);
  const [name, setName] = useState("");
  const [saving, setSaving] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);

  const load = async () => {
    const [entitiesRes, locationsRes] = await Promise.all([api.get<LegalEntity[]>("/legal-entities/"), api.get<Location[]>("/locations/")]);
    setEntities(entitiesRes.data);
    setLocations(locationsRes.data);
  };

  useEffect(() => {
    load();
  }, []);

  const entityLocations = useMemo(() => locations.filter((location) => location.legal_entity === selectedEntity), [locations, selectedEntity]);

  const submit = async () => {
    if (!selectedEntity || !name.trim()) {
      Alert.alert("Ошибка", "Выберите юрлицо и введите название помещения.");
      return;
    }
    setSaving(true);
    try {
      await api.post("/locations/", {
        legal_entity: selectedEntity,
        name: name.trim(),
      });
      Alert.alert("Готово", "Помещение создано.");
      setName("");
      await load();
    } catch (error: any) {
      const detail = error?.response?.data?.detail || error?.response?.data?.non_field_errors?.[0] || "Не удалось создать помещение.";
      Alert.alert("Ошибка", detail);
    } finally {
      setSaving(false);
    }
  };

  const updateLocation = async (id: number) => {
    if (!selectedEntity || !name.trim()) {
      Alert.alert("Ошибка", "Выберите юрлицо и введите название помещения.");
      return;
    }
    setSaving(true);
    try {
      await api.patch(`/locations/${id}/`, {
        legal_entity: selectedEntity,
        name: name.trim(),
      });
      Alert.alert("Готово", "Помещение обновлено.");
      setEditingId(null);
      setName("");
      await load();
    } catch (error: any) {
      const detail = error?.response?.data?.detail || "Не удалось обновить помещение.";
      Alert.alert("Ошибка", detail);
    } finally {
      setSaving(false);
    }
  };

  const removeLocation = async (id: number) => {
    Alert.alert("Удалить помещение?", "Действие необратимо.", [
      { text: "Отмена", style: "cancel" },
      {
        text: "Удалить",
        style: "destructive",
        onPress: async () => {
          try {
            await api.delete(`/locations/${id}/`);
            await load();
          } catch (error: any) {
            const detail = error?.response?.data?.detail || "Не удалось удалить помещение.";
            Alert.alert("Ошибка", detail);
          }
        },
      },
    ]);
  };

  const startEdit = (location: Location) => {
    setEditingId(location.id);
    setSelectedEntity(location.legal_entity);
    setName(location.name);
  };

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.content}>
        <Text style={styles.title}>Добавить помещение</Text>

        <Text style={styles.label}>Юрлицо</Text>
        <View style={styles.wrap}>
          {entities.map((entity) => (
            <Pressable
              key={entity.id}
              style={[styles.chip, selectedEntity === entity.id && styles.chipSelected]}
              onPress={() => {
                setSelectedEntity(entity.id);
              }}
            >
              <Text style={styles.chipText}>{entity.name}</Text>
            </Pressable>
          ))}
        </View>

        <TextInput
          style={styles.input}
          value={name}
          onChangeText={setName}
          placeholder="Название помещения"
          placeholderTextColor={colors.textSecondary}
        />

        <Pressable style={[styles.button, saving && { opacity: 0.7 }]} onPress={() => (editingId ? updateLocation(editingId) : submit())} disabled={saving}>
          <Text style={styles.buttonText}>{saving ? "Сохраняем..." : editingId ? "Сохранить изменения" : "Создать помещение"}</Text>
        </Pressable>
        {editingId ? (
          <Pressable
            style={styles.secondaryButton}
            onPress={() => {
              setEditingId(null);
              setName("");
            }}
          >
            <Text style={styles.secondaryButtonText}>Отменить редактирование</Text>
          </Pressable>
        ) : null}

        <Text style={styles.subtitle}>Существующие помещения</Text>
        {entityLocations.map((location) => (
          <View key={location.id} style={styles.card}>
            <Text style={styles.cardTitle}>{location.name}</Text>
            <View style={styles.row}>
              <Pressable style={styles.secondaryButton} onPress={() => startEdit(location)}>
                <Text style={styles.secondaryButtonText}>Изменить</Text>
              </Pressable>
              <Pressable style={styles.deleteButton} onPress={() => removeLocation(location.id)}>
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
  title: { color: colors.textPrimary, fontSize: 20, fontWeight: "700" },
  subtitle: { color: colors.textPrimary, fontSize: 17, fontWeight: "700", marginTop: 8 },
  label: { color: colors.textPrimary, fontWeight: "600", marginTop: 6 },
  wrap: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
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
  card: { backgroundColor: colors.surface, borderRadius: 10, padding: 12, borderWidth: 1, borderColor: colors.border, gap: 6 },
  cardTitle: { color: colors.textPrimary, fontWeight: "700" },
  row: { flexDirection: "row", gap: 8, marginTop: 4 },
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
