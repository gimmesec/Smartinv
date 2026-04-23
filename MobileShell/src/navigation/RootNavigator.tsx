import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import React, { useState } from "react";
import { ActivityIndicator, Pressable, SafeAreaView, Text } from "react-native";
import { AdminScreen } from "../features/admin/AdminScreen";
import { AssetsScreen } from "../features/assets/AssetsScreen";
import { useAuth } from "../features/auth/AuthContext";
import { LoginScreen } from "../features/auth/LoginScreen";
import { InventoryScanScreen } from "../features/inventory/InventoryScanScreen";
import { InventorySessionScreen } from "../features/inventory/InventorySessionScreen";
import { colors } from "../shared/theme";

const AuthStack = createNativeStackNavigator();
const Tabs = createBottomTabNavigator();

function InventoryEntryScreen() {
  const [selectedSessionId, setSelectedSessionId] = useState<number | null>(null);
  if (selectedSessionId) {
    return <InventoryScanScreen sessionId={selectedSessionId} />;
  }
  return <InventorySessionScreen onSelectSession={setSelectedSessionId} />;
}

function MainTabs() {
  const { user, logout } = useAuth();
  const isAdmin = !!user?.is_admin;

  return (
    <Tabs.Navigator
      screenOptions={{
        headerStyle: { backgroundColor: colors.surface },
        headerTitleStyle: { color: colors.textPrimary },
        tabBarStyle: { backgroundColor: colors.surface, borderTopColor: colors.border },
        tabBarActiveTintColor: colors.accent,
        tabBarInactiveTintColor: colors.textSecondary,
        headerRight: () => (
          <Pressable onPress={logout}>
            <Text style={{ color: colors.accent, fontWeight: "700" }}>Выйти</Text>
          </Pressable>
        ),
      }}
    >
      <Tabs.Screen name="Assets" component={AssetsScreen} options={{ title: "Активы" }} />
      <Tabs.Screen name="Inventory" component={InventoryEntryScreen} options={{ title: "Инвентаризация" }} />
      {isAdmin ? <Tabs.Screen name="Admin" component={AdminScreen} options={{ title: "Админ" }} /> : null}
    </Tabs.Navigator>
  );
}

export function RootNavigator() {
  const { loading, user } = useAuth();

  if (loading) {
    return (
      <SafeAreaView style={{ flex: 1, alignItems: "center", justifyContent: "center", backgroundColor: colors.background }}>
        <ActivityIndicator color={colors.accent} />
        <Text style={{ color: colors.textPrimary }}>Загрузка сессии...</Text>
      </SafeAreaView>
    );
  }

  return (
    <AuthStack.Navigator screenOptions={{ headerShown: false }}>
      {user ? <AuthStack.Screen name="Main" component={MainTabs} /> : <AuthStack.Screen name="Login" component={LoginScreen} />}
    </AuthStack.Navigator>
  );
}
