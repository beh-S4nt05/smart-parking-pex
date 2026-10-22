import { Alert, Linking, Platform, Pressable, Text, View } from "react-native";
import { Link, useRouter } from "expo-router";
import { useAuth } from "../hooks/useAuth";
import { API_URL } from "../services/api";
import { LogoBlox, Logo } from "./ui";

/**
 * Cabeçalho público unificado:
 * - Web: barra completa com navegação (como no template Home WEB do Figma)
 * - Mobile: barra compacta com logo + ação de login/painel
 */
const LINKS = [
  { label: "Home", href: "/" },
  { label: "Reservar Vaga", href: "/explorar" },
  { label: "Status do Estacionamento", href: "/" },
  { label: "Lista de Shoppings", href: "/explorar" },
] as const;

export default function Header({ rotaAtual = "/" }: { rotaAtual?: string }) {
  const router = useRouter();
  const { user, isAuthenticated, canAccessPanel, signOut } = useAuth();

  const nomePrim = user?.nome?.split(" ")[0] ?? "";

  return (
    <View className="border-b border-slate-200 bg-white">
      <View className="mx-auto w-full max-w-7xl flex-row items-center justify-between gap-4 px-4 py-3 sm:px-6">
        <Link href="/">
          <LogoBlox />
        </Link>

        {/* nav web */}
        <View className="hidden flex-row items-center gap-1 md:flex">
          {LINKS.map((l) => {
            const ativo = rotaAtual === l.href && l.label !== "Reservar Vaga";
            return (
              <Link key={l.label} href={l.href as any}>
                <Pressable
                  className={`rounded-lg px-3 py-2 ${ativo ? "bg-blue-50" : ""}`}
                >
                  <Text
                    className={`text-sm font-semibold ${
                      ativo ? "text-blue-700" : "text-slate-700"
                    }`}
                  >
                    {l.label}
                  </Text>
                </Pressable>
              </Link>
            );
          })}
        </View>

        <View className="flex-row items-center gap-2 sm:gap-3">
          <Pressable
            onPress={() =>
              Alert.alert(
                "HelpDesk Smart Parking",
                "Documentação da API em /docs · (92) 98123-0258\nbehsolutionsandautomations@gmail.com",
                Platform.OS === "web"
                  ? [
                      { text: "Fechar", style: "cancel" },
                      {
                        text: "Abrir /docs",
                        onPress: () => Linking.openURL(`${API_URL}/docs`),
                      },
                    ]
                  : [{ text: "Fechar" }],
              )
            }
            className="hidden px-3 py-2 sm:block"
          >
            <Text className="text-sm font-semibold text-blue-700">HelpDesk</Text>
          </Pressable>

          {isAuthenticated ? (
            <View className="flex-row items-center gap-2">
              <View className="hidden flex-row items-center gap-2 rounded-full bg-slate-100 py-1 pl-1 pr-3 sm:flex">
                <View className="h-7 w-7 items-center justify-center rounded-full bg-blue-600">
                  <Text className="text-xs font-bold text-white">
                    {nomePrim.slice(0, 1).toUpperCase()}
                  </Text>
                </View>
                <Text className="text-[13px] font-semibold text-slate-700">
                  {nomePrim}
                </Text>
              </View>
              {canAccessPanel ? (
                <Link href="/dashboard">
                  <Pressable className="rounded-full bg-slate-900 px-4 py-2">
                    <Text className="text-sm font-semibold text-white">Painel</Text>
                  </Pressable>
                </Link>
              ) : (
                <Link href="/reservas">
                  <Pressable className="rounded-full bg-blue-50 px-4 py-2">
                    <Text className="text-sm font-semibold text-blue-700">
                      Minhas reservas
                    </Text>
                  </Pressable>
                </Link>
              )}
              <Link href="/perfil">
                <Pressable className="px-1">
                  <Text className="text-sm font-semibold text-blue-700">Minha conta</Text>
                </Pressable>
              </Link>
              <Pressable onPress={() => signOut()} className="px-1">
                <Text className="text-sm font-medium text-slate-400">Sair</Text>
              </Pressable>
            </View>
          ) : (
            <>
              <Pressable
                onPress={() => router.push("/login")}
                className="rounded-full bg-blue-600 px-5 py-2 active:bg-blue-700"
              >
                <Text className="text-sm font-semibold text-white">Entrar</Text>
              </Pressable>
            </>
          )}
        </View>
      </View>
    </View>
  );
}

/** barra superior escura usada no Mapa (mobile) e no Simulador */
export function BarraEscura({
  titulo,
  subtitulo,
  aoVivo,
  voltar,
  direita,
}: {
  titulo: string;
  subtitulo?: string;
  aoVivo?: boolean;
  voltar?: React.ReactNode;
  direita?: React.ReactNode;
}) {
  return (
    <View className="bg-slate-900 px-4 py-4 sm:px-6">
      <View className="mx-auto flex w-full max-w-7xl flex-row items-center gap-3">
        {voltar}
        <View className="flex-1">
          <Text className="text-lg font-bold text-white">{titulo}</Text>
          {subtitulo ? (
            <Text className="mt-0.5 text-xs text-slate-300">{subtitulo}</Text>
          ) : null}
        </View>
        {aoVivo ? (
          <View className="flex-row items-center gap-1.5">
            <View className="h-2 w-2 rounded-full bg-emerald-400" />
          </View>
        ) : null}
        {direita}
      </View>
    </View>
  );
}

export { Logo };
