import { NavigationContainer } from "@react-navigation/native";
import React from "react";
import { StatusBar } from "react-native";
import { AuthProvider } from "./src/features/auth/AuthContext";
import { RootNavigator } from "./src/navigation/RootNavigator";
import { colors } from "./src/shared/theme";

export default function App() {
  return (
    <AuthProvider>
      <NavigationContainer>
        <StatusBar barStyle="light-content" backgroundColor={colors.background} />
        <RootNavigator />
      </NavigationContainer>
    </AuthProvider>
  );
}
