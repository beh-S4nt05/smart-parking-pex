/**
 * Armazenamento de tokens multiplataforma:
 * - Android/iOS: expo-secure-store (keystore/keychain, criptografado por hardware)
 * - Web: AsyncStorage (SecureStore NÃO existe no navegador — chamá-lo lá
 *   derruba o app, que era o comportamento anterior deste arquivo)
 */
import { Platform } from "react-native";
import * as SecureStore from "expo-secure-store";
import AsyncStorage from "@react-native-async-storage/async-storage";

const ACCESS_TOKEN_KEY = "smartparking_access_token";
const REFRESH_TOKEN_KEY = "smartparking_refresh_token";
const USER_CACHE_KEY = "smartparking_user_cache";

async function getItem(key: string): Promise<string | null> {
  if (Platform.OS === "web") {
    try {
      return await AsyncStorage.getItem(key);
    } catch {
      return null;
    }
  }
  try {
    return await SecureStore.getItemAsync(key);
  } catch {
    return null;
  }
}

async function setItem(key: string, value: string): Promise<void> {
  if (Platform.OS === "web") {
    await AsyncStorage.setItem(key, value);
  } else {
    await SecureStore.setItemAsync(key, value);
  }
}

async function removeItem(key: string): Promise<void> {
  if (Platform.OS === "web") {
    await AsyncStorage.removeItem(key);
  } else {
    await SecureStore.deleteItemAsync(key);
  }
}

export const storage = {
  getAccessToken: () => getItem(ACCESS_TOKEN_KEY),
  setAccessToken: (token: string) => setItem(ACCESS_TOKEN_KEY, token),
  getRefreshToken: () => getItem(REFRESH_TOKEN_KEY),
  setRefreshToken: (token: string) => setItem(REFRESH_TOKEN_KEY, token),

  /** Cache do último usuário conhecido — acelera o boot offline */
  getUserCache: async (): Promise<string | null> => getItem(USER_CACHE_KEY),
  setUserCache: (json: string) => setItem(USER_CACHE_KEY, json),
  clearUserCache: () => removeItem(USER_CACHE_KEY),

  clearTokens: async (): Promise<void> => {
    await Promise.all([
      removeItem(ACCESS_TOKEN_KEY),
      removeItem(REFRESH_TOKEN_KEY),
      removeItem(USER_CACHE_KEY),
    ]);
  },
};
