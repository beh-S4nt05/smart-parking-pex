// Estilo global NativeWind — SEM este import as classes não são aplicadas
// (comportamento que fazia o app render "sem estilo" em dev)
import "../../assets/Styles/global.css";

import { Stack } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { AuthProvider } from "../context/AuthContext";

export default function Layout() {
  return (
    <AuthProvider>
      <StatusBar style="dark" />
      <Stack
        screenOptions={{
          headerShown: false,
          contentStyle: { backgroundColor: "#F8FAFC" },
        }}
      />
    </AuthProvider>
  );
}
