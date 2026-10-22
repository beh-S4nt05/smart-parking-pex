// Estilo global NativeWind — SEM este import as classes não são aplicadas
// (comportamento que fazia o app render "sem estilo" em dev)
import "../../assets/Styles/global.css";

import { Platform } from "react-native";
import { Stack } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { AuthProvider } from "../context/AuthContext";

/**
 * Amarração edge-to-edge (rodada UI 22/10): com android.edgeToEdgeEnabled o
 * app passa POR DEBAIXO das barras do sistema (o "tela inteira" pedido), e
 * todo screen ganha respiro seguro no topo — os botões voltam a ser clicáveis
 * — e embaixo (gesto/nav bar no Android, home indicator no iOS).
 * No web os insets são 0: comportamento idêntico ao anterior.
 */
export default function Layout() {
  const insets = useSafeAreaInsets();
  const topo = Platform.OS === "web" ? 0 : insets.top;
  const base = Platform.OS === "web" ? 0 : Math.max(insets.bottom, 8);
  return (
    <AuthProvider>
      <StatusBar style="dark" />
      <Stack
        screenOptions={{
          headerShown: false,
          contentStyle: {
            backgroundColor: "#F8FAFC",
            paddingTop: topo,
            paddingBottom: base,
          },
        }}
      />
    </AuthProvider>
  );
}
