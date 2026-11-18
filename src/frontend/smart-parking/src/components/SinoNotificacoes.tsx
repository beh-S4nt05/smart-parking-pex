import { useCallback, useState } from "react";
import { Pressable, Text, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useFocusEffect, useRouter } from "expo-router";
import { useAuth } from "../hooks/useAuth";
import { notificacoesApi } from "../services/notificacoesApi";

export default function SinoNotificacoes({ claro = false }: { claro?: boolean }) {
  const { isAuthenticated, user } = useAuth();
  const router = useRouter();
  const [naoLidas, setNaoLidas] = useState(0);
  useFocusEffect(useCallback(() => {
    if (!isAuthenticated) {
      setNaoLidas(0);
      return;
    }
    let vivo = true;
    const consultar = async () => {
      try {
        const n = await notificacoesApi.contador();
        if (vivo) setNaoLidas(n);
      } catch {
        // Não bloquear navegação por instabilidade da API.
      }
    };
    void consultar();
    const id = setInterval(() => void consultar(),
      user?.role === "gestor" || user?.role === "admin" ? 3000 : 15000);
    return () => { vivo = false; clearInterval(id); };
  }, [isAuthenticated, user?.role]));
  if (!isAuthenticated) return null;
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={naoLidas ? `Abrir notificações, ${naoLidas} não lidas` : "Abrir notificações"}
      onPress={() => router.push("/notificacoes")}
      style={{ minHeight: 44, minWidth: 44, alignItems: "center", justifyContent: "center", position: "relative" }}
    >
      <Ionicons name={naoLidas ? "notifications" : "notifications-outline"} size={21} color={claro ? "#FFFFFF" : "#2563EB"} />
      {naoLidas > 0 ? (
        <View style={{ position: "absolute", top: 1, right: 0, backgroundColor: "#DC2626", minWidth: 18, height: 18, borderRadius: 9, alignItems: "center", justifyContent: "center", paddingHorizontal: 2 }}>
          <Text style={{ color: "#fff", fontSize: 10, fontWeight: "800" }}>{naoLidas > 99 ? "99+" : naoLidas}</Text>
        </View>
      ) : null}
    </Pressable>
  );
}
