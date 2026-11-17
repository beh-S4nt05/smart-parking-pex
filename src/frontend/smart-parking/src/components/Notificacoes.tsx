import React, { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { Animated, Pressable, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

type Nivel = "sucesso" | "erro" | "info";
type Acao = { rotulo: string; onPress: () => void };
type Mensagem = { id: number; titulo: string; texto?: string; nivel: Nivel; acao?: Acao };
type Contexto = {
  avisar: (titulo: string, texto?: string, nivel?: Nivel, acao?: Acao) => void;
};

const Context = createContext<Contexto>({ avisar: () => {} });

export function useNotificacoes(): Contexto {
  return useContext(Context);
}

/**
 * Faixa de alerta não modal, nativa em Android/iOS e compatível com Web.
 * Confirmações destrutivas continuam com Alert.alert do sistema.
 * Um único toast por vez para não esconder navegação nem bombardear o usuário.
 */
export function NotificacoesProvider({ children }: { children: React.ReactNode }) {
  const insets = useSafeAreaInsets();
  const [mensagem, setMensagem] = useState<Mensagem | null>(null);
  const contador = useRef(0);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const opacidade = useRef(new Animated.Value(0)).current;
  const deslocamento = useRef(new Animated.Value(-8)).current;

  const dispensar = useCallback(() => {
    if (timer.current) clearTimeout(timer.current);
    timer.current = null;
    setMensagem(null);
  }, []);

  useEffect(() => () => {
    if (timer.current) clearTimeout(timer.current);
  }, []);

  const avisar = useCallback((titulo: string, texto?: string, nivel: Nivel = "info", acao?: Acao) => {
    if (timer.current) clearTimeout(timer.current);
    const id = ++contador.current;
    setMensagem({ id, titulo, texto, nivel, acao });
    opacidade.setValue(0);
    deslocamento.setValue(-8);
    Animated.parallel([
      Animated.timing(opacidade, { toValue: 1, duration: 160, useNativeDriver: true }),
      Animated.timing(deslocamento, { toValue: 0, duration: 160, useNativeDriver: true }),
    ]).start();
    timer.current = setTimeout(dispensar, nivel === "erro" ? 4800 : 3400);
  }, [deslocamento, dispensar, opacidade]);

  const borda = mensagem?.nivel === "erro" ? "#DC2626"
    : mensagem?.nivel === "sucesso" ? "#059669" : "#2563EB";

  return (
    <Context.Provider value={{ avisar }}>
      {children}
      {mensagem ? (
        <View
          pointerEvents="box-none"
          style={{
            position: "absolute", top: insets.top + 8,
            left: 12, right: 12, zIndex: 9999, alignItems: "center",
          }}
        >
          <Animated.View
            style={{
              opacity: opacidade, transform: [{ translateY: deslocamento }],
              width: "100%", maxWidth: 440,
              backgroundColor: "#FFFFFF", borderRadius: 14,
              borderLeftWidth: 4, borderLeftColor: borda,
              borderWidth: 1, borderColor: "#E2E8F0",
              shadowColor: "#0F172A", shadowOpacity: 0.12,
              shadowRadius: 12, elevation: 6,
            }}
          >
            <Pressable
              accessibilityRole="button"
              accessibilityLabel={`${mensagem.titulo}. ${mensagem.texto ?? ""}. Dispensar aviso`}
              onPress={dispensar}
              style={{ paddingHorizontal: 15, paddingVertical: 11 }}
            >
              <Text style={{ fontSize: 13, fontWeight: "800", color: "#0F172A" }}>
                {mensagem.titulo}
              </Text>
              {mensagem.texto ? (
                <Text style={{ color: "#475569", fontSize: 12, marginTop: 3 }}>
                  {mensagem.texto}
                </Text>
              ) : null}
            </Pressable>
            {mensagem.acao ? (
              <Pressable
                accessibilityRole="button"
                accessibilityLabel={mensagem.acao.rotulo}
                onPress={() => {
                  const executar = mensagem.acao?.onPress;
                  dispensar();
                  executar?.();
                }}
                style={{ alignSelf: "flex-start", paddingHorizontal: 15, paddingBottom: 12 }}
              >
                <Text style={{ fontSize: 12, fontWeight: "800", color: "#2563EB" }}>
                  {mensagem.acao.rotulo}
                </Text>
              </Pressable>
            ) : null}
          </Animated.View>
        </View>
      ) : null}
    </Context.Provider>
  );
}
