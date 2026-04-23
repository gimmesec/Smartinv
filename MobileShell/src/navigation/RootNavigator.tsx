import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import React, { useState } from "react";
import { ActivityIndicator, Pressable, SafeAreaView, Text } from "react-native";
import { AdminCreateAssetScreen } from "../features/assets/AdminCreateAssetScreen";
import { AssetsScreen } from "../features/assets/AssetsScreen";
import { MyResponsibleAssetsScreen } from "../features/assets/MyResponsibleAssetsScreen";
import { useAuth } from "../features/auth/AuthContext";
import { LoginScreen } from "../features/auth/LoginScreen";
import { InventoryScanScreen } from "../features/inventory/InventoryScanScreen";
import { InventorySessionDetailScreen } from "../features/inventory/InventorySessionDetailScreen";
import { InventorySessionScreen } from "../features/inventory/InventorySessionScreen";
import { colors } from "../shared/theme";
import { InventorySession } from "../shared/types";

const AuthStack = createNativeStackNavigator();
const Tabs = createBottomTabNavigator();

function InventoryEntryScreen() {
  const [selectedSession, setSelectedSession] = useState<InventorySession | null>(null);
  const [startedSessionId, setStartedSessionId] = useState<number | null>(null);

  if (startedSessionId) {
    return <InventoryScanScreen sessionId={startedSessionId} />;
  }
  if (selectedSession) {
    return <InventorySessionDetailScreen session={selectedSession} onBack={() => setSelectedSession(null)} />;
  }
  return <InventorySessionScreen onOpenSession={setSelectedSession} onStartSession={setStartedSessionId} />;
}

function MainTabs() {
  const { logout, user } = useAuth();
  const isAdmin = !!user?.is_admin;

  return (
    <Tabs.Navigator
      screenOptions={{
        headerStyle: { backgroundColor: colors.surface },
        headerTitleStyle: { color: colors.textPrimary },
        tabBarStyle: { backgroundColor: colors.surface, borderTopColor: colors.border },
        tabBarActiveTintColor: colors.accent,
        tabBarInactiveTintColor: colors.textSecondary,
        headerRightContainerStyle: { paddingRight: 12 },
        headerRight: () => (
          <Pressable onPress={logout} style={{ paddingHorizontal: 6, paddingVertical: 4 }} hitSlop={8}>
            <Text style={{ color: colors.accent, fontWeight: "700" }}>Выйти</Text>
          </Pressable>
        ),
      }}
    >
      <Tabs.Screen
        name="Assets"
        component={AssetsScreen}
        options={{
          title: "Активы",
          tabBarIcon: ({ color, size }) => <Text style={{ color, fontSize: size }}>📦</Text>,
        }}
      />
      <Tabs.Screen
        name="Inventory"
        component={InventoryEntryScreen}
        options={{
          title: "Инвентаризация",
          tabBarIcon: ({ color, size }) => <Text style={{ color, fontSize: size }}>📋</Text>,
        }}
      />
      {isAdmin ? (
        <Tabs.Screen
          name="CreateAsset"
          component={AdminCreateAssetScreen}
          options={{
            title: "Добавить актив",
            tabBarIcon: ({ color, size }) => <Text style={{ color, fontSize: size }}>➕</Text>,
          }}
        />
      ) : (
        <Tabs.Screen
          name="MyResponsible"
          component={MyResponsibleAssetsScreen}
          options={{
            title: "Ответственность",
            tabBarIcon: ({ color, size }) => <Text style={{ color, fontSize: size }}>👤</Text>,
          }}
        />
      )}
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
