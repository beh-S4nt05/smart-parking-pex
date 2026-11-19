/** Registro opt-in de Expo Push Token; requer build nativo e credenciais FCM/APNs. */
import { Platform } from "react-native";
import Constants from "expo-constants";
import { notificacoesApi } from "./notificacoesApi";
import { storage } from "./storage";

export function diagnosticoBuildPush(): string | null {
  if (Platform.OS === "web") {
    return "O push do dispositivo precisa de um aplicativo Android/iOS instalado, não do navegador.";
  }
  if (Constants.appOwnership === "expo") {
    return "O Expo Go não suporta push remoto no Android SDK 58. Instale um APK de preview (EAS Build).";
  }
  const projectId = Constants.easConfig?.projectId ??
    (Constants.expoConfig?.extra?.eas as { projectId?: string } | undefined)?.projectId;
  if (!projectId) {
    return "O aplicativo não tem um EAS projectId. Execute 'eas init' e gere um novo APK de preview.";
  }
  return null;
}

/** Consulta a permissão do sistema sem mostrar diálogo; útil para diagnóstico. */
export async function estadoPermissaoPushNativa(): Promise<"permitida" | "solicitar" | "bloqueada" | null> {
  if (diagnosticoBuildPush()) return null;
  const Notifications = await import("expo-notifications");
  const permissao = await Notifications.getPermissionsAsync();
  if (permissao.granted) return "permitida";
  return permissao.canAskAgain ? "solicitar" : "bloqueada";
}

export async function habilitarPushMobile(): Promise<string> {
  const problema = diagnosticoBuildPush();
  if (problema) throw new Error(problema);
  const projectId = (Constants.easConfig?.projectId ??
    (Constants.expoConfig?.extra?.eas as { projectId?: string } | undefined)?.projectId)!;
  const Notifications = await import("expo-notifications");
  if (Platform.OS === "android") {
    await Notifications.setNotificationChannelAsync("reservas", {
      name: "Reservas", importance: Notifications.AndroidImportance.DEFAULT,
    });
    await Notifications.setNotificationChannelAsync("vagas", {
      name: "Disponibilidade de vagas", importance: Notifications.AndroidImportance.DEFAULT,
    });
    await Notifications.setNotificationChannelAsync("financeiro", {
      name: "Financeiro", importance: Notifications.AndroidImportance.DEFAULT,
    });
  }
  const atual = await Notifications.getPermissionsAsync();
  const permissao = atual.granted ? atual : await Notifications.requestPermissionsAsync();
  if (!permissao.granted) {
    throw new Error("Permissão de notificações negada nas configurações do celular.");
  }
  let token: string;
  try {
    token = (await Notifications.getExpoPushTokenAsync({ projectId })).data;
  } catch {
    throw new Error(
      "Não foi possível obter o token do aparelho. Verifique conexão, Google Play Services e as credenciais Firebase FCM/APNs do build EAS.",
    );
  }
  if (!token) throw new Error("O dispositivo não retornou um token de notificações.");
  const id = await notificacoesApi.registrarDispositivo(token, Platform.OS as "android" | "ios");
  try {
    await storage.setNotificationDeviceId(id);
  } catch (e) {
    await notificacoesApi.desvincularDispositivo(id).catch(() => undefined);
    throw e;
  }
  return id;
}

/**
 * Revalida um token de um usuário que JÁ ativou push. Nunca mostra o prompt do SO
 * em background: se a permissão foi revogada, a central interna continua disponível.
 * Ajuda quando o aparelho recebe um novo token ou volta a ficar online.
 */
export async function sincronizarPushAutorizado(): Promise<void> {
  if (diagnosticoBuildPush()) return;
  const pref = await notificacoesApi.preferencias();
  if (!pref.push_ativo) return;

  const Notifications = await import("expo-notifications");
  const permissao = await Notifications.getPermissionsAsync();
  if (!permissao.granted) return;

  const projectId = Constants.easConfig?.projectId ??
    (Constants.expoConfig?.extra?.eas as { projectId?: string } | undefined)?.projectId;
  if (!projectId) return;

  // Revalidação silenciosa: não altera preferência, nem inscreve contas
  // que ainda não consentiram. Mantém a autorização do JWT no servidor.
  const { data: token } = await Notifications.getExpoPushTokenAsync({ projectId });
  if (!token) return;

  const antigo = await storage.getNotificationDeviceId();
  const id = await notificacoesApi.registrarDispositivo(token, Platform.OS as "android" | "ios");
  await storage.setNotificationDeviceId(id);
  if (antigo && antigo !== id) {
    // Token trocado ou login em outra conta: o backend só permite excluir
    // aparelhos da própria conta. 404 não interrompe a sincronização.
    await notificacoesApi.desvincularDispositivo(antigo).catch(() => undefined);
  }
}

export function destinoNotificacaoSeguro(value: unknown): string | null {
  if (typeof value !== "string") return null;
  if (["/reservas", "/dashboard", "/perfil", "/notificacoes"].includes(value)) return value;
  if (/^\/shopping\/[A-Za-z0-9_-]+$/.test(value)) return value;
  return null;
}
