import React, { useEffect, useMemo, useState } from "react";
import { Alert, Image, Modal, Pressable, SafeAreaView, ScrollView, StyleSheet, Text, TextInput, View } from "react-native";
import { Camera } from "react-native-camera-kit";
import { launchCamera } from "react-native-image-picker";
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
  const [scannerVisible, setScannerVisible] = useState(false);
  const [photoUri, setPhotoUri] = useState<string | null>(null);
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
    if (!photoUri) {
      Alert.alert("Фото обязательно", "Перед созданием актива сделайте фото.");
      return;
    }
    if (!selectedLocation && !selectedEmployee) {
      Alert.alert("Ошибка", "Нужно выбрать либо помещение, либо ответственного сотрудника.");
      return;
    }
    setSaving(true);
    try {
      const created = await api.post<{ id: number; photo?: string | null }>("/assets/", {
        legal_entity: selectedEntity,
        name: name.trim(),
        inventory_number: inventoryNumber.trim(),
        description: description.trim(),
        location: selectedLocation,
        responsible_employee: selectedEmployee,
        category: selectedCategory,
        status: "active",
      });
      if (photoUri) {
        const formData = new FormData();
        formData.append("photo", {
          uri: photoUri,
          name: `asset-${Date.now()}.jpg`,
          type: "image/jpeg",
        } as any);
        await api.patch(`/assets/${created.data.id}/`, formData, {
          headers: { "Content-Type": "multipart/form-data" },
        });
      }
      Alert.alert("Готово", "Материальный актив создан.");
      setName("");
      setInventoryNumber("");
      setDescription("");
      setPhotoUri(null);
      setSelectedLocation(null);
      setSelectedEmployee(null);
      setSelectedCategory(null);
    } catch (error: any) {
      const data = error?.response?.data;
      const detail =
        typeof data === "string"
          ? data
          : data?.detail ||
            data?.non_field_errors?.[0] ||
            data?.inventory_number?.[0] ||
            data?.responsible_employee?.[0] ||
            data?.location?.[0];
      Alert.alert("Ошибка", detail || "Не удалось создать актив.");
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
        <View style={styles.inline}>
          <TextInput
            style={[styles.input, styles.inlineInput]}
            value={inventoryNumber}
            onChangeText={setInventoryNumber}
            placeholder="Инвентарный номер / QR / штрихкод"
            placeholderTextColor={colors.textSecondary}
          />
          <Pressable style={styles.inlineButton} onPress={() => setScannerVisible(true)}>
            <Text style={styles.inlineButtonText}>Сканировать</Text>
          </Pressable>
        </View>
        <TextInput style={styles.input} value={description} onChangeText={setDescription} placeholder="Описание" placeholderTextColor={colors.textSecondary} />
        <Pressable
          style={styles.photoButton}
          onPress={async () => {
            const result = await launchCamera({
              mediaType: "photo",
              cameraType: "back",
              saveToPhotos: false,
              quality: 0.7,
            });
            const photo = result.assets?.[0];
            if (photo?.uri) {
              setPhotoUri(photo.uri);
            }
          }}
        >
          <Text style={styles.photoButtonText}>{photoUri ? "Переснять фото актива" : "Сделать фото актива"}</Text>
        </Pressable>
        {photoUri ? <Image source={{ uri: photoUri }} style={styles.photoPreview} resizeMode="cover" /> : null}

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

        <Pressable style={[styles.button, (!photoUri || saving) && { opacity: 0.7 }]} onPress={submit} disabled={saving || !photoUri}>
          <Text style={styles.buttonText}>{saving ? "Сохраняем..." : "Создать актив"}</Text>
        </Pressable>
      </ScrollView>
      <Modal visible={scannerVisible} animationType="slide" onRequestClose={() => setScannerVisible(false)}>
        <SafeAreaView style={styles.scannerContainer}>
          <Text style={styles.scannerTitle}>Сканируйте QR/штрихкод</Text>
          <Camera
            style={styles.scanner}
            scanBarcode
            onReadCode={(event: { nativeEvent: { codeStringValue: string } }) => {
              const code = event.nativeEvent.codeStringValue;
              if (!code) {
                return;
              }
              setInventoryNumber(code);
              setScannerVisible(false);
            }}
          />
          <Pressable style={styles.scannerCloseButton} onPress={() => setScannerVisible(false)}>
            <Text style={styles.scannerCloseText}>Закрыть</Text>
          </Pressable>
        </SafeAreaView>
      </Modal>
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
  inline: { flexDirection: "row", alignItems: "center", gap: 8 },
  inlineInput: { flex: 1 },
  inlineButton: {
    backgroundColor: colors.accent,
    borderRadius: 8,
    paddingVertical: 10,
    paddingHorizontal: 12,
  },
  inlineButtonText: { color: "#fff", fontWeight: "700" },
  input: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 8,
    backgroundColor: colors.inputBackground,
    color: colors.textPrimary,
    padding: 10,
  },
  photoButton: {
    backgroundColor: colors.surfaceAlt,
    borderColor: colors.border,
    borderWidth: 1,
    borderRadius: 10,
    paddingVertical: 10,
    alignItems: "center",
  },
  photoButtonText: { color: colors.textPrimary, fontWeight: "600" },
  photoPreview: {
    width: "100%",
    height: 220,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: colors.border,
  },
  button: {
    marginTop: 8,
    backgroundColor: colors.accent,
    borderRadius: 10,
    paddingVertical: 12,
    alignItems: "center",
  },
  buttonText: { color: "#fff", fontWeight: "700" },
  scannerContainer: { flex: 1, backgroundColor: colors.background, padding: 12 },
  scannerTitle: { color: colors.textPrimary, fontSize: 18, fontWeight: "700", marginBottom: 8 },
  scanner: { flex: 1, borderRadius: 12, overflow: "hidden" },
  scannerCloseButton: {
    marginTop: 12,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: colors.border,
    paddingVertical: 12,
    alignItems: "center",
    backgroundColor: colors.surface,
  },
  scannerCloseText: { color: colors.textPrimary, fontWeight: "700" },
});
