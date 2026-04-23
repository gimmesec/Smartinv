import React, { useEffect, useState } from "react";
import { SafeAreaView, StyleSheet, Text, View } from "react-native";
import { api } from "../../shared/api/client";
import { colors } from "../../shared/theme";

export function AdminScreen() {
  const [employeesCount, setEmployeesCount] = useState(0);
  const [locationsCount, setLocationsCount] = useState(0);

  useEffect(() => {
    (async () => {
      const [employees, locations] = await Promise.all([api.get("/employees/"), api.get("/locations/")]);
      setEmployeesCount(employees.data.length);
      setLocationsCount(locations.data.length);
    })();
  }, []);

  return (
    <SafeAreaView style={styles.container}>
      <Text style={styles.title}>Админ-раздел</Text>
      <View style={styles.card}>
        <Text style={styles.metric}>Сотрудников: {employeesCount}</Text>
        <Text style={styles.metric}>Локаций: {locationsCount}</Text>
        <Text style={styles.helper}>Импорт XML: Django Admin {"->"} OneC XML Import</Text>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 12, backgroundColor: colors.background },
  title: { fontSize: 20, fontWeight: "700", marginBottom: 12, color: colors.textPrimary },
  card: { borderWidth: 1, borderColor: colors.border, borderRadius: 10, padding: 12, gap: 8, backgroundColor: colors.surface },
  metric: { color: colors.textPrimary },
  helper: { color: colors.textSecondary, marginTop: 6 },
});
