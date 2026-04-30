import { useFocusEffect } from "@react-navigation/native";
import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Alert, FlatList, Pressable, RefreshControl, SafeAreaView, StyleSheet, Text, View } from "react-native";
import { useAuth } from "../auth/AuthContext";
import { api } from "../../shared/api/client";
import { colors } from "../../shared/theme";
import { Employee, InventorySession, LegalEntity, Location } from "../../shared/types";

type Props = {
  onOpenSession: (session: InventorySession) => void;
  onStartSession: (sessionId: number) => void;
};

export function InventorySessionScreen({ onOpenSession, onStartSession }: Props) {
  const { user } = useAuth();
  const isAdmin = !!user?.is_admin;
  const [sessions, setSessions] = useState<InventorySession[]>([]);
  const [legalEntities, setLegalEntities] = useState<LegalEntity[]>([]);
  const [selectedLegalEntityId, setSelectedLegalEntityId] = useState<number | null>(user?.legal_entity_id ?? null);
  /** null = вся территория юрлица; иначе id помещения для ожидаемого списка в сессии */
  const [selectedLocationId, setSelectedLocationId] = useState<number | null>(null);
  const [locations, setLocations] = useState<Location[]>([]);
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [selectedEmployeeIds, setSelectedEmployeeIds] = useState<number[]>(user?.employee_id ? [user.employee_id] : []);
  const [showConductors, setShowConductors] = useState(false);
  const [starting, setStarting] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  const loadSessionsAndEntities = useCallback(async () => {
    try {
      const [sessionsRes, entitiesRes] = await Promise.all([
        api.get<InventorySession[]>("/inventory-sessions/"),
        api.get<LegalEntity[]>("/legal-entities/"),
      ]);
      setSessions(sessionsRes.data);
      setLegalEntities(entitiesRes.data);
      setSelectedLegalEntityId((prev) => prev ?? (entitiesRes.data[0]?.id ?? null));
    } catch {
      Alert.alert("Ошибка", "Не удалось загрузить сессии инвентаризации.");
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      void loadSessionsAndEntities();
    }, [loadSessionsAndEntities])
  );

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    try {
      await loadSessionsAndEntities();
    } finally {
      setRefreshing(false);
    }
  }, [loadSessionsAndEntities]);

  useEffect(() => {
    if (!selectedLegalEntityId && user?.legal_entity_id) {
      setSelectedLegalEntityId(user.legal_entity_id);
    }
  }, [selectedLegalEntityId, user?.legal_entity_id]);

  useEffect(() => {
    if (!selectedLegalEntityId || !isAdmin) {
      setEmployees([]);
      return;
    }
    (async () => {
      const res = await api.get<Employee[]>("/employees/", { params: { legal_entity: selectedLegalEntityId } });
      const uniqueEmployees = Array.from(new Map(res.data.map((emp) => [emp.id, emp])).values());
      setEmployees(uniqueEmployees);
      setSelectedEmployeeIds((prev) => prev.filter((id) => uniqueEmployees.some((emp) => emp.id === id)));
    })();
  }, [isAdmin, selectedLegalEntityId]);

  useEffect(() => {
    if (!selectedLegalEntityId) {
      setLocations([]);
      return;
    }
    (async () => {
      const res = await api.get<Location[]>("/locations/", { params: { legal_entity: selectedLegalEntityId } });
      setLocations(res.data);
    })();
  }, [selectedLegalEntityId]);

  const startConduct = async () => {
    if (!selectedLegalEntityId) {
      Alert.alert("Выберите юрлицо", "Нужно указать юрлицо для проведения инвентаризации.");
      return;
    }
    if (isAdmin && selectedEmployeeIds.length === 0) {
      Alert.alert("Выберите проводящих", "Для запуска выберите хотя бы одного сотрудника.");
      return;
    }
    setStarting(true);
    try {
      const activeSessionsRes = await api.get<InventorySession[]>("/inventory-sessions/", {
        params: { legal_entity: selectedLegalEntityId, status: "in_progress" },
      });
      const activeSession = activeSessionsRes.data[0];
      let targetSession =
        activeSession ||
        (
          await api.post<InventorySession>("/inventory-sessions/", {
            legal_entity: selectedLegalEntityId,
            status: "draft",
            location: selectedLocationId,
          })
        ).data;
      if (activeSession) {
        await api.patch(`/inventory-sessions/${targetSession.id}/`, { location: selectedLocationId });
        const refreshed = await api.get<InventorySession>(`/inventory-sessions/${targetSession.id}/`);
        targetSession = refreshed.data;
      }
      const payload = {
        legal_entity_id: selectedLegalEntityId,
        ...(isAdmin ? { employee_ids: selectedEmployeeIds } : {}),
      };
      await api.post(`/inventory-sessions/${targetSession.id}/conduct/`, payload);
      onStartSession(targetSession.id);
    } catch (error: any) {
      const detail = error?.response?.data?.detail;
      Alert.alert("Ошибка", detail || "Не удалось создать и запустить инвентаризацию.");
    } finally {
      setStarting(false);
    }
  };

  const selectedEmployeesLabel = useMemo(() => {
    if (!isAdmin) {
      return user?.employee_name || "Текущий сотрудник";
    }
    if (selectedEmployeeIds.length === 0) {
      return "Не выбрано";
    }
    const selected = employees.filter((emp) => selectedEmployeeIds.includes(emp.id)).map((emp) => emp.full_name);
    if (selected.length <= 2) {
      return selected.join(", ");
    }
    return `${selected.slice(0, 2).join(", ")} +${selected.length - 2}`;
  }, [employees, isAdmin, selectedEmployeeIds, user?.employee_name]);

  return (
    <SafeAreaView style={styles.container}>
      <Text style={styles.titleHeader}>Сессии инвентаризации</Text>
      <FlatList
        data={sessions}
        keyExtractor={(item) => String(item.id)}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
        renderItem={({ item }) => (
          <Pressable style={styles.card}>
            <Text style={styles.title}>Сессия #{item.id}</Text>
            <Text style={styles.meta}>{item.legal_entity_name ?? "—"}</Text>
            {item.location_name ? <Text style={styles.meta}>Помещение: {item.location_name}</Text> : null}
            <Text style={styles.meta}>Дата: {item.started_at ? new Date(item.started_at).toLocaleString("ru-RU") : "не указана"}</Text>
            <Pressable style={styles.linkButton} onPress={() => onOpenSession(item)}>
              <Text style={styles.linkText}>Подробнее</Text>
            </Pressable>
          </Pressable>
        )}
        ListFooterComponent={
          <View style={styles.controlsBox}>
            <Text style={styles.meta}>Юрлицо проведения:</Text>
            <View style={styles.employeeWrap}>
              {legalEntities.map((entity) => (
                <Pressable
                  key={entity.id}
                  style={[styles.employeeChip, selectedLegalEntityId === entity.id && styles.employeeChipSelected]}
                  onPress={() => {
                    setSelectedLegalEntityId(entity.id);
                    setSelectedLocationId(null);
                  }}
                >
                  <Text style={styles.employeeChipText}>{entity.name}</Text>
                </Pressable>
              ))}
            </View>

            <Text style={styles.meta}>Помещение (опционально)</Text>
            <Text style={styles.hintSmall}>
              Если выберете помещение, в инвентаризации будут ожидаться только активы, привязанные к нему. «Всё юрлицо» — по всему юрлицу.
            </Text>
            <View style={styles.employeeWrap}>
              <Pressable
                style={[styles.employeeChip, selectedLocationId === null && styles.employeeChipSelected]}
                onPress={() => setSelectedLocationId(null)}
              >
                <Text style={styles.employeeChipText}>Всё юрлицо</Text>
              </Pressable>
              {locations.map((loc) => (
                <Pressable
                  key={loc.id}
                  style={[styles.employeeChip, selectedLocationId === loc.id && styles.employeeChipSelected]}
                  onPress={() => setSelectedLocationId(loc.id)}
                >
                  <Text style={styles.employeeChipText}>{loc.name}</Text>
                </Pressable>
              ))}
            </View>

            <Pressable style={styles.dropdown} onPress={() => setShowConductors((prev) => !prev)}>
              <Text style={styles.dropdownLabel}>Кто проводит:</Text>
              <Text style={styles.dropdownValue}>{selectedEmployeesLabel}</Text>
            </Pressable>

            {showConductors ? (
              isAdmin ? (
                <View style={styles.employeeWrap}>
                  {employees.map((employee) => (
                    <Pressable
                      key={employee.id}
                      style={[styles.employeeChip, selectedEmployeeIds.includes(employee.id) && styles.employeeChipSelected]}
                      onPress={() =>
                        setSelectedEmployeeIds((prev) =>
                          prev.includes(employee.id) ? prev.filter((id) => id !== employee.id) : [...prev, employee.id]
                        )
                      }
                    >
                      <Text style={styles.employeeChipText}>{employee.full_name}</Text>
                    </Pressable>
                  ))}
                </View>
              ) : (
                <Text style={styles.meta}>{user?.employee_name || "Текущий сотрудник"}</Text>
              )
            ) : null}

            <Pressable style={[styles.actionButton, starting && { opacity: 0.7 }]} onPress={startConduct} disabled={starting}>
              <Text style={styles.actionText}>{starting ? "Создаём..." : "Начать новую инвентаризацию"}</Text>
            </Pressable>
          </View>
        }
        contentContainerStyle={{ paddingBottom: 20 }}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 12, backgroundColor: colors.background },
  titleHeader: { color: colors.textPrimary, fontSize: 20, fontWeight: "700", marginBottom: 8 },
  card: { borderWidth: 1, borderColor: colors.border, backgroundColor: colors.surface, borderRadius: 8, padding: 12, marginBottom: 10 },
  title: { fontWeight: "700", marginBottom: 4, color: colors.textPrimary },
  meta: { color: colors.textSecondary },
  linkButton: { marginTop: 8, alignSelf: "flex-start" },
  linkText: { color: colors.accent, fontWeight: "600" },
  controlsBox: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 10,
    backgroundColor: colors.surface,
    padding: 10,
    gap: 8,
    marginTop: 6,
  },
  employeeWrap: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  employeeChip: { borderWidth: 1, borderColor: colors.border, borderRadius: 8, paddingHorizontal: 10, paddingVertical: 6 },
  employeeChipSelected: { borderColor: colors.accent, backgroundColor: colors.surfaceAlt },
  employeeChipText: { color: colors.textPrimary },
  dropdown: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 8,
    backgroundColor: colors.inputBackground,
    paddingHorizontal: 10,
    paddingVertical: 8,
  },
  dropdownLabel: { color: colors.textSecondary, fontSize: 12 },
  dropdownValue: { color: colors.textPrimary, fontWeight: "600", marginTop: 2 },
  hintSmall: { color: colors.textSecondary, fontSize: 12, lineHeight: 16 },
  actionButton: {
    borderRadius: 10,
    backgroundColor: colors.accent,
    paddingVertical: 12,
    alignItems: "center",
  },
  actionText: { color: "#fff", fontWeight: "700" },
});
