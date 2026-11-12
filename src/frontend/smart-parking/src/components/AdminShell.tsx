/**
 * Casca do painel administrativo: sidebar escura no web, lista de navegação
 * horizontal no mobile — mesma árvore de rotas, dois "modos de acesso" como
 * previsto no modelo híbrido web+mobile do app.
 */
import { ReactNode } from "react";
import {
  Pressable,
  ScrollView,
  Text,
  View,
} from "react-native";
import { useRouter } from "expo-router";
import { useAuth } from "../hooks/useAuth";
import { useLarguraResponsiva } from "../hooks/useLarguraResponsiva";
import { IconeVoltar, Logo, SeloAoVivo } from "./ui";

export type AbaPainel =
  | "dashboard"
  | "estacionamentos"
  | "andares"
  | "simulador-qr"
  | "relatorios"
  | "usuarios";

const ABAS: { id: AbaPainel; label: string }[] = [
  { id: "dashboard", label: "Dashboard" },
  { id: "estacionamentos", label: "Estacionamentos" },
  { id: "andares", label: "Andares e Vagas" },
  { id: "simulador-qr", label: "Simulador QR" },
  { id: "relatorios", label: "Relatórios" },
  { id: "usuarios", label: "Usuários" },
];

export default function AdminShell({
  aba,
  onAba,
  titulo,
  subtitulo,
  direita,
  children,
}: {
  aba: AbaPainel;
  onAba: (a: AbaPainel) => void;
  titulo: string;
  subtitulo?: string;
  direita?: ReactNode;
  children: ReactNode;
}) {
  const width = useLarguraResponsiva();
  const isWeb = width >= 1024;
  const router = useRouter();
  const { user, signOut } = useAuth();

  // Simulador QR é tooling de infraestrutura: visível SOMENTE ao admin global
  const abas = ABAS.filter((a) => a.id !== "simulador-qr" || user?.role === "admin");

  const trocar = (a: AbaPainel) => {
    if (a === "simulador-qr") {
      router.push("/simulador-qr");
      return;
    }
    onAba(a);
  };

  if (isWeb) {
    return (
      <View className="flex-1 flex-row bg-slate-50">
        {/* sidebar escura */}
        <View className="w-64 justify-between border-r border-slate-800 bg-slate-900 px-4 py-5">
          <View>
            <View className="mb-6 flex-row items-center gap-2.5 px-2">
              <Logo size={36} />
              <View>
                <Text className="text-sm font-bold text-white">Smart Parking</Text>
                <Text className="text-[11px] text-slate-400">Painel Admin</Text>
              </View>
            </View>
            <View className="gap-1">
              {abas.map((item) => {
                const ativo = item.id === aba;
                return (
                  <Pressable
                    key={item.id}
                    onPress={() => trocar(item.id)}
                    accessibilityRole="tab"
                    accessibilityLabel={item.label}
                    accessibilityHint={`Abre a seção ${item.label} do painel`}
                    accessibilityState={{ selected: ativo, disabled: false }}
                    hitSlop={6}
                    className={`min-h-11 flex-row items-center gap-2.5 rounded-lg px-3.5 py-2.5 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-400 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900 motion-reduce:transition-none ${
                      ativo ? "bg-blue-600" : "hover:bg-slate-800 active:bg-slate-800"
                    }`}
                  >
                    <View
                      className={`h-1.5 w-1.5 rounded-full ${
                        ativo ? "bg-white" : "bg-slate-500"
                      }`}
                    />
                    <Text
                      className={`text-sm font-semibold ${
                        ativo ? "text-white" : "text-slate-300"
                      }`}
                    >
                      {item.label}
                    </Text>
                  </Pressable>
                );
              })}
            </View>
          </View>

          <View className="rounded-xl bg-slate-800/70 p-3">
            <View className="flex-row items-center gap-2.5">
              <View className="h-8 w-8 items-center justify-center rounded-full bg-blue-600">
                <Text className="text-xs font-bold text-white">
                  {(user?.nome ?? "A").slice(0, 1).toUpperCase()}
                </Text>
              </View>
              <View className="flex-1">
                <Text className="text-[13px] font-bold text-white">
                  {user?.nome ?? "Usuário"}
                </Text>
                <Text className="text-[11px] text-slate-400">{user?.email}</Text>
              </View>
            </View>
            <Pressable
              onPress={() => router.push("/" as never)}
              accessibilityRole="button"
              accessibilityLabel="Voltar ao site"
              hitSlop={6}
              className="mt-3 min-h-11 flex-row items-center justify-center rounded-lg border border-slate-700 py-2 active:bg-slate-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-400"
            >
              <View className="flex-row items-center justify-center gap-1.5">
                <IconeVoltar cor="#E2E8F0" tamanho={12} />
                <Text className="text-center text-xs font-semibold text-slate-200">
                  Voltar ao site
                </Text>
              </View>
            </Pressable>
            <Pressable
              onPress={() => signOut()}
              accessibilityRole="button"
              accessibilityLabel="Encerrar sessão"
              hitSlop={6}
              className="mt-2 min-h-11 flex-row items-center justify-center rounded-lg py-1.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-300"
            >
              <Text className="text-center text-xs font-semibold text-red-300">
                Encerrar sessão
              </Text>
            </Pressable>
          </View>
        </View>

        {/* conteúdo */}
        <ScrollView className="min-w-0 flex-1" contentContainerStyle={{ padding: 28 }}>
          <View className="mx-auto w-full min-w-0 max-w-6xl">
            <View className="mb-6 flex-row flex-wrap items-end justify-between gap-3">
              <View className="min-w-0 flex-1">
                <Text className="text-3xl font-extrabold text-slate-900">
                  {titulo}
                </Text>
                {subtitulo ? (
                  <Text className="mt-1 text-sm text-slate-600">{subtitulo}</Text>
                ) : null}
              </View>
              <View className="flex-row flex-wrap items-center gap-3">
                <SeloAoVivo />
                {direita}
              </View>
            </View>
            {children}
          </View>
        </ScrollView>
      </View>
    );
  }

  // -------- mobile --------
  return (
    <View className="flex-1 bg-slate-50">
      <View className="border-b border-slate-800 bg-slate-900 pt-5">
        <View className="px-4">
          <View className="min-w-0 flex-1">
            <Text className="text-xl font-bold text-white">{titulo}</Text>
            {subtitulo ? (
              <Text className="mt-1 text-xs leading-5 text-slate-300">{subtitulo}</Text>
            ) : null}
          </View>
          <View className="mt-3 flex-row flex-wrap items-center justify-between gap-2 border-t border-slate-700 py-2">
            <SeloAoVivo />
            <View className="flex-row items-center gap-1">
            <Pressable
              onPress={() => router.push("/" as never)}
              accessibilityRole="button"
              accessibilityLabel="Voltar ao site"
              hitSlop={6}
              className="min-h-11 flex-row items-center justify-center rounded-lg px-3 transition-colors active:bg-slate-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-400"
            >
              <View className="flex-row items-center gap-1">
                <IconeVoltar cor="#E2E8F0" tamanho={12} />
                <Text className="text-xs font-semibold text-slate-200">Site</Text>
              </View>
            </Pressable>
            <Pressable
              onPress={() => signOut()}
              accessibilityRole="button"
              accessibilityLabel="Encerrar sessão"
              hitSlop={6}
              className="min-h-11 flex-row items-center justify-center rounded-lg px-3 transition-colors active:bg-slate-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-300"
            >
              <Text className="text-xs font-semibold text-red-200">Sair</Text>
            </Pressable>
            </View>
          </View>
        </View>
        <View className="flex-row flex-wrap gap-1 border-t border-slate-700 px-2">
          {abas.map((item) => {
            const ativo = item.id === aba;
            return (
              <Pressable
                key={item.id}
                onPress={() => trocar(item.id)}
                accessibilityRole="tab"
                accessibilityLabel={item.label}
                accessibilityHint={`Abre a seção ${item.label} do painel`}
                accessibilityState={{ selected: ativo, disabled: false }}
                hitSlop={6}
                className={`min-h-11 flex-row items-center justify-center border-b-2 px-3.5 py-1.5 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-400 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900 motion-reduce:transition-none ${
                  ativo ? "border-blue-400" : "border-transparent hover:bg-slate-800 active:bg-slate-800"
                }`}
              >
                <Text
                  className={`text-xs font-semibold ${
                    ativo ? "text-white" : "text-slate-300"
                  }`}
                >
                  {item.label}
                </Text>
              </Pressable>
            );
          })}
        </View>
      </View>
      <ScrollView contentContainerStyle={{ padding: 16, paddingBottom: 40 }}>
        <View className="gap-4">
          {direita}
          {children}
        </View>
      </ScrollView>
    </View>
  );
}

export { ABAS };
