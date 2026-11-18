/** Registro opt-in de Expo Push Token. Nunca executado no Expo Go como pré-requisito. */
import { Platform } from "react-native";
import Constants from "expo-constants";
import { notificacoesApi } from "./notificacoesApi";
import { storage } from "./storage";

export async function habilitarPushMobile(): Promise<string> {
  if (Platform.OS === "web") {
    throw new Error("Push remoto está disponível apenas no aplicativo Android/iOS instalado.");
  }
  const projectId = Constants.easConfig?.projectId ??
    (Constants.expoConfig?.extra?.eas as { projectId?: string } | undefined)?.projectId;
  if (!projectId) {
    throw new Error("Falta configurar o EAS projectId no build próprio do Smart Parking.");
  }
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
  const { data: token } = await Notifications.getExpoPushTokenAsync({ projectId });
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

export function destinoNotificacaoSeguro(value: unknown): string | null {
  if (typeof value !== "string") return null;
  if (["/reservas", "/dashboard", "/perfil", "/notificacoes"].includes(value)) return value;
  if (/^\/shopping\/[A-Za-z0-9_-]+$/.test(value)) return value;
  return null;
}
