import React, { useEffect, useMemo, useState } from "react";
import { Alert, Pressable, SafeAreaView, ScrollView, StyleSheet, Text, TextInput, View } from "react-native";
import { api } from "../../shared/api/client";
import { colors } from "../../shared/theme";
import { Employee, LegalEntity, Location } from "../../shared/types";

type AssetCategory = { id: number; name: string };

export function AdminCreateAssetScreen() {
  const [entities, setEntities] = useState<LegalEntity[]>([]);
  const [locations, setLocations] = useState<Location[]>([]);
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [categories, setCategories] = useState<AssetCategory[]>([]);

  const [name, setName] = useState("");
  const [inventoryNumber, setInventoryNumber] = useState("");
  const [description, setDescription] = useState("");
  const [selectedEntity, setSelectedEntity] = useState<number | null>(null);
  const [selectedLocation, setSelectedLocation] = useState<number | null>(null);
  const [selectedEmployee, setSelectedEmployee] = useState<number | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    (async () => {
      const [entitiesRes, locationsRes, employeesRes, categoriesRes] = await Promise.all([
        api.get<LegalEntity[]>("/legal-entities/"),
        api.get<Location[]>("/locations/"),
        api.get<Employee[]>("/employees/"),
        api.get<AssetCategory[]>("/asset-categories/"),
      ]);
      setEntities(entitiesRes.data);
      setLocations(locationsRes.data);
      setEmployees(employeesRes.data);
      setCategories(categoriesRes.data);
    })();
  }, []);

  const entityLocations = useMemo(() => locations.filter((item) => item.legal_entity === selectedEntity), [locations, selectedEntity]);
  const entityEmployees = useMemo(() => employees.filter((item) => item.legal_entity === selectedEntity), [employees, selectedEntity]);

  const submit = async () => {
    if (!selectedEntity || !name.trim() || !inventoryNumber.trim()) {
      Alert.alert("Ошибка", "Заполните минимум: юрлицо, название и инвентарный номер.");
      return;
    }
    if (!selectedLocation && !selectedEmployee) {
      Alert.alert("Ошибка", "Нужно выбрать либо помещение, либо ответственного сотрудника.");
      return;
    }
    setSaving(true);
    try {
      await api.post("/assets/", {
        legal_entity: selectedEntity,
        name: name.trim(),
        inventory_number: inventoryNumber.trim(),
        description: description.trim(),
        location: selectedLocation,
        responsible_employee: selectedEmployee,
        category: selectedCategory,
        status: "active",
      });
      Alert.alert("Готово", "Материальный актив создан.");
      setName("");
      setInventoryNumber("");
      setDescription("");
      setSelectedLocation(null);
      setSelectedEmployee(null);
      setSelectedCategory(null);
    } catch {
      Alert.alert("Ошибка", "Не удалось создать актив.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.content}>
        <Text style={styles.title}>Добавить актив</Text>

        <Text style={styles.label}>Юрлицо</Text>
        <View style={styles.wrap}>
          {entities.map((entity) => (
            <Pressable
              key={entity.id}
              style={[styles.chip, selectedEntity === entity.id && styles.chipSelected]}
              onPress={() => {
                setSelectedEntity(entity.id);
                setSelectedLocation(null);
                setSelectedEmployee(null);
              }}
            >
              <Text style={styles.chipText}>{entity.name}</Text>
            </Pressable>
          ))}
        </View>

        <TextInput style={styles.input} value={name} onChangeText={setName} placeholder="Название актива" placeholderTextColor={colors.textSecondary} />
        <TextInput
          style={styles.input}
          value={inventoryNumber}
          onChangeText={setInventoryNumber}
          placeholder="Инвентарный номер"
          placeholderTextColor={colors.textSecondary}
        />
        <TextInput style={styles.input} value={description} onChangeText={setDescription} placeholder="Описание" placeholderTextColor={colors.textSecondary} />

        <Text style={styles.label}>Помещение/локация</Text>
        <View style={styles.wrap}>
          {entityLocations.map((location) => (
            <Pressable
              key={location.id}
              style={[styles.chip, selectedLocation === location.id && styles.chipSelected]}
              onPress={() => setSelectedLocation(location.id)}
            >
              <Text style={styles.chipText}>{location.name}</Text>
            </Pressable>
          ))}
        </View>

        <Text style={styles.label}>Ответственный сотрудник</Text>
        <View style={styles.wrap}>
          {entityEmployees.map((employee) => (
            <Pressable
              key={employee.id}
              style={[styles.chip, selectedEmployee === employee.id && styles.chipSelected]}
              onPress={() => setSelectedEmployee(employee.id)}
            >
              <Text style={styles.chipText}>{employee.full_name}</Text>
            </Pressable>
          ))}
        </View>

        <Text style={styles.label}>Категория</Text>
        <View style={styles.wrap}>
          {categories.map((category) => (
            <Pressable
              key={category.id}
              style={[styles.chip, selectedCategory === category.id && styles.chipSelected]}
              onPress={() => setSelectedCategory(category.id)}
            >
              <Text style={styles.chipText}>{category.name}</Text>
            </Pressable>
          ))}
        </View>

        <Pressable style={styles.button} onPress={submit} disabled={saving}>
          <Text style={styles.buttonText}>{saving ? "Сохраняем..." : "Создать актив"}</Text>
        </Pressable>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },
  content: { padding: 12, gap: 10 },
  title: { color: colors.textPrimary, fontSize: 20, fontWeight: "700" },
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
});
