// Estilo global NativeWind — SEM este import as classes não são aplicadas
// (comportamento que fazia o app render "sem estilo" em dev)
import "../../assets/Styles/global.css";

import { AppState, Platform } from "react-native";
import { useEffect } from "react";
import { instalarAlertaWeb } from "../services/web-alert-shim";

instalarAlertaWeb(); // Alert.alert é no-op no RN-web — shim p/ window.alert/confirm (ver módulo)
import { Stack, useRouter } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { AuthProvider } from "../context/AuthContext";
import { useAuth } from "../hooks/useAuth";
import { NotificacoesProvider } from "../components/Notificacoes";
import { destinoNotificacaoSeguro, sincronizarPushAutorizado } from "../services/pushNotificacoes";

/**
 * Push é uma capacidade NATIVA da V1. Só reinscreve automaticamente quem já
 * optou por receber push; nunca solicita permissão do sistema no boot.
 * O worker remoto continua independente da UI, inclusive com app fechado.
 */
function SincronizacaoPushNativa() {
  const { user, loading } = useAuth();
  useEffect(() => {
    if (Platform.OS === "web" || loading || !user) return;
    let ativo = true;
    let ultimaTentativa = 0;
    const sincronizar = () => {
      if (!ativo || Date.now() - ultimaTentativa < 5 * 60 * 1000) return;
      ultimaTentativa = Date.now();
      void sincronizarPushAutorizado().catch(() => {
        // Rede indisponível/credencial expirada não interrompe a abertura
        // do app. A tentativa será refeita quando voltar ao primeiro plano.
      });
    };
    sincronizar();
    const assinatura = AppState.addEventListener("change", (estado) => {
      if (estado === "active") sincronizar();
    });
    return () => {
      ativo = false;
      assinatura.remove();
    };
  }, [loading, user?.id]);
  return null;
}

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
    let ultimoId: string | null = null;
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
      const abrirResposta = (response: import("expo-notifications").NotificationResponse) => {
        const destino = destinoNotificacaoSeguro(response.notification.request.content.data?.destino);
        const id = response.notification.request.identifier;
        if (!ativo || !destino || ultimoId === id) return;
        ultimoId = id;
        router.push(destino as never);
        // Evita reabrir a mesma rota em próximos boots ou re-renderizações.
        void Notifications.clearLastNotificationResponseAsync().catch(() => undefined);
      };
      listener = Notifications.addNotificationResponseReceivedListener(abrirResposta);
      // O listener sozinho não cobre um toque que abriu o app já encerrado.
      void Notifications.getLastNotificationResponseAsync().then(resposta => {
        if (ativo && resposta) abrirResposta(resposta);
      }).catch(() => undefined);
    }).catch(() => { /* Central interna continua funcional sem módulo nativo */ });
    return () => {
      ativo = false;
      listener?.remove();
    };
  }, [router]);
  const topo = Platform.OS === "web" ? 0 : insets.top;
  const base = Platform.OS === "web" ? 0 : Math.max(insets.bottom, 8);
  return (
    <AuthProvider>
      <SincronizacaoPushNativa />
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
