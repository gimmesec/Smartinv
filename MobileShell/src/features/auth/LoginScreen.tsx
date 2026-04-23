import React, { useState } from "react";
import { Alert, Pressable, SafeAreaView, StyleSheet, Text, TextInput, View } from "react-native";
import { useAuth } from "./AuthContext";
import { colors } from "../../shared/theme";

export function LoginScreen() {
  const { login } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const onLogin = async () => {
    try {
      setSubmitting(true);
      await login(username.trim(), password);
    } catch {
      Alert.alert("Ошибка входа", "Проверьте логин и пароль.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.card}>
        <Text style={styles.title}>SmartInv</Text>
        <Text style={styles.subtitle}>Учет материальных активов</Text>

        <TextInput
          style={styles.input}
          placeholder="Логин"
          placeholderTextColor={colors.textSecondary}
          autoCapitalize="none"
          value={username}
          onChangeText={setUsername}
        />
        <TextInput
          style={styles.input}
          placeholder="Пароль"
          placeholderTextColor={colors.textSecondary}
          secureTextEntry
          value={password}
          onChangeText={setPassword}
        />
        <Pressable style={styles.primaryButton} onPress={onLogin} disabled={submitting}>
          <Text style={styles.primaryButtonText}>
            {submitting ? "Подождите..." : "Войти"}
          </Text>
        </Pressable>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, justifyContent: "center", padding: 16, backgroundColor: colors.background },
  card: {
    borderRadius: 16,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.surface,
    padding: 16,
    gap: 12,
  },
  title: { fontSize: 28, fontWeight: "700", color: colors.textPrimary, textAlign: "center" },
  subtitle: { fontSize: 14, color: colors.textSecondary, textAlign: "center", marginBottom: 8 },
  input: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 10,
    padding: 12,
    color: colors.textPrimary,
    backgroundColor: colors.inputBackground,
  },
  primaryButton: {
    marginTop: 4,
    borderRadius: 10,
    backgroundColor: colors.accent,
    paddingVertical: 12,
    alignItems: "center",
  },
  primaryButtonText: { color: "#fff", fontWeight: "700" },
});
