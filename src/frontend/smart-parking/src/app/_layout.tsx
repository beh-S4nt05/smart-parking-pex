// Estilo global NativeWind — SEM este import as classes não são aplicadas
// (comportamento que fazia o app render "sem estilo" em dev)
import "../../assets/Styles/global.css";

import { Platform } from "react-native";
import { useEffect } from "react";
import { instalarAlertaWeb } from "../services/web-alert-shim";

instalarAlertaWeb(); // Alert.alert é no-op no RN-web — shim p/ window.alert/confirm (ver módulo)
import { Stack, useRouter } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { AuthProvider } from "../context/AuthContext";
import { NotificacoesProvider } from "../components/Notificacoes";
import { destinoNotificacaoSeguro } from "../services/pushNotificacoes";

/**
 * Amarração edge-to-edge (rodada UI 22/10): com android.edgeToEdgeEnabled o
 * app passa POR DEBAIXO das barras do sistema (o "tela inteira" pedido), e
 * todo screen ganha respiro seguro no topo — os botões voltam a ser clicáveis
 * — e embaixo (gesto/nav bar no Android, home indicator no iOS).
 * No web os insets são 0: comportamento idêntico ao anterior.
 */
export default function Layout() {
  const insets = useSafeAreaInsets();
  const router = useRouter();
  useEffect(() => {
    if (Platform.OS === "web") return;
    let ativo = true;
    let listener: { remove: () => void } | undefined;
    void import("expo-notifications").then(Notifications => {
      if (!ativo) return;
      // Sem handler, o push pode chegar mas não aparecer como aviso visível
      // quando o Smart Parking está aberto em primeiro plano.
      Notifications.setNotificationHandler({
        handleNotification: async () => ({
          shouldShowBanner: true,
          shouldShowList: true,
          shouldPlaySound: true,
          shouldSetBadge: false,
        }),
      });
      listener = Notifications.addNotificationResponseReceivedListener(response => {
        const destino = destinoNotificacaoSeguro(response.notification.request.content.data?.destino);
        if (destino) router.push(destino as never);
      });
    }).catch(() => { /* expo-notifications disponível em development builds próprios */ });
    return () => {
      ativo = false;
      listener?.remove();
    };
  }, [router]);
  const topo = Platform.OS === "web" ? 0 : insets.top;
  const base = Platform.OS === "web" ? 0 : Math.max(insets.bottom, 8);
  return (
    <AuthProvider>
      <NotificacoesProvider>
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
      </NotificacoesProvider>
    </AuthProvider>
  );
}
