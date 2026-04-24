import React, { useEffect, useState } from "react";
import { Alert, FlatList, Pressable, SafeAreaView, StyleSheet, Text, View } from "react-native";
import { useAuth } from "../auth/AuthContext";
import { api } from "../../shared/api/client";
import { colors } from "../../shared/theme";
import { Employee, InventorySession, LegalEntity } from "../../shared/types";

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
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [selectedEmployeeIds, setSelectedEmployeeIds] = useState<number[]>(user?.employee_id ? [user.employee_id] : []);
  const [starting, setStarting] = useState(false);

  const getSessionStatusRu = (status: string) => {
    const map: Record<string, string> = {
      draft: "Черновик",
      in_progress: "В процессе",
      completed: "Завершена",
    };
    return map[status] ?? status;
  };

  useEffect(() => {
    (async () => {
      const [sessionsRes, entitiesRes] = await Promise.all([
        api.get<InventorySession[]>("/inventory-sessions/"),
        api.get<LegalEntity[]>("/legal-entities/"),
      ]);
      setSessions(sessionsRes.data);
      setLegalEntities(entitiesRes.data);
      if (!selectedLegalEntityId && entitiesRes.data.length) {
        const firstEntityId = entitiesRes.data[0].id;
        setSelectedLegalEntityId(firstEntityId);
      }
    })();
  }, [selectedLegalEntityId]);

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
      const targetSession =
        activeSession ||
        (
          await api.post<InventorySession>("/inventory-sessions/", {
            legal_entity: selectedLegalEntityId,
            status: "draft",
          })
        ).data;
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

  return (
    <SafeAreaView style={styles.container}>
      <Text style={styles.titleHeader}>Сессии инвентаризации</Text>
      <FlatList
        data={sessions}
        keyExtractor={(item) => String(item.id)}
        renderItem={({ item }) => (
          <Pressable style={styles.card}>
            <Text style={styles.title}>Сессия #{item.id}</Text>
            <Text style={styles.meta}>Статус: {getSessionStatusRu(item.status)}</Text>
            <Text style={styles.meta}>Дата: {item.started_at ? new Date(item.started_at).toLocaleString("ru-RU") : "не указана"}</Text>
            <Pressable style={styles.linkButton} onPress={() => onOpenSession(item)}>
              <Text style={styles.linkText}>Подробнее</Text>
            </Pressable>
          </Pressable>
        )}
        contentContainerStyle={{ paddingBottom: isAdmin ? 190 : 120 }}
      />
      <View style={styles.employeeBox}>
        <Text style={styles.meta}>Юрлицо проведения:</Text>
        <View style={styles.employeeWrap}>
          {legalEntities.map((entity) => (
            <Pressable
              key={entity.id}
              style={[styles.employeeChip, selectedLegalEntityId === entity.id && styles.employeeChipSelected]}
              onPress={() => setSelectedLegalEntityId(entity.id)}
            >
              <Text style={styles.employeeChipText}>{entity.name}</Text>
            </Pressable>
          ))}
        </View>
        {isAdmin ? (
          <>
            <Text style={styles.meta}>Кто проводит (можно выбрать несколько):</Text>
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
                  <Text style={styles.employeeChipText}>
                    {employee.full_name} ({employee.id})
                  </Text>
                </Pressable>
              ))}
            </View>
          </>
        ) : (
          <Text style={styles.meta}>Кто проводит: {user?.employee_name || "Текущий сотрудник"}</Text>
        )}
      </View>
      <Pressable style={[styles.actionButton, starting && { opacity: 0.7 }]} onPress={startConduct} disabled={starting}>
        <Text style={styles.actionText}>{starting ? "Создаём..." : "Начать новую инвентаризацию"}</Text>
      </Pressable>
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
  employeeBox: {
    position: "absolute",
    left: 12,
    right: 12,
    bottom: 70,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 10,
    backgroundColor: colors.surface,
    padding: 10,
    gap: 8,
  },
  employeeWrap: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  employeeChip: { borderWidth: 1, borderColor: colors.border, borderRadius: 8, paddingHorizontal: 10, paddingVertical: 6 },
  employeeChipSelected: { borderColor: colors.accent, backgroundColor: colors.surfaceAlt },
  employeeChipText: { color: colors.textPrimary },
  actionButton: {
    position: "absolute",
    left: 12,
    right: 12,
    bottom: 12,
    borderRadius: 10,
    backgroundColor: colors.accent,
    paddingVertical: 12,
    alignItems: "center",
  },
  actionText: { color: "#fff", fontWeight: "700" },
});
