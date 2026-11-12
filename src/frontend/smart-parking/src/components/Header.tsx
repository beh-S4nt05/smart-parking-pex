import { Alert, Linking, Platform, Pressable, Text, View } from "react-native";
import { Link, useRouter } from "expo-router";
import { useAuth } from "../hooks/useAuth";
import { API_URL } from "../services/api";
import { Botao, LogoBlox, Logo } from "./ui";

/**
 * Cabeçalho público unificado, com dois arranjos puramente CSS (sem medir a
 * janela em JS, para não gerar salto de layout nem React #418 na hidratação):
 *
 *  · ≥ lg: navegação completa em linha;
 *  · < lg: navegação visível em uma segunda linha, dentro do fluxo.
 *
 * Antes a barra usava `md:flex` para os quatro links e mantinha todas as
 * ações autenticadas na mesma linha: em 768/900/1024px o conteúdo somava
 * ~1202px e empurrava os botões para fora da viewport (medido no Chromium).
 *
 * Os itens de navegação são UM único <Link>: envolver um Pressable com
 * accessibilityRole="link" dentro de outro <Link> duplicava o papel na
 * árvore de acessibilidade (dois "links" com o mesmo nome).
 */
const LINKS = [
  { label: "Início", href: "/" },
  { label: "Explorar shoppings", href: "/explorar" },
] as const;

const CLASSE_LINK =
  "min-h-11 flex-row items-center content-center rounded-lg px-3 transition-colors hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 motion-reduce:transition-none";

export default function Header({ rotaAtual = "/" }: { rotaAtual?: string }) {
  const router = useRouter();
  const { isAuthenticated, canAccessPanel, signOut } = useAuth();

  const abrirAjuda = () =>
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
    );

  const links = () =>
    LINKS.map((l) => {
      const ativo = rotaAtual === l.href;
      return (
        <Link
          key={l.label}
          href={l.href as never}
          accessibilityRole="link"
          accessibilityLabel={l.label}
          accessibilityState={{ selected: ativo }}
          className={`${CLASSE_LINK} ${ativo ? "bg-blue-50" : ""}`}
        >
          <Text
            className={`text-sm font-semibold content-center items-center ${ativo ? "text-blue-700" : "text-slate-700"
              }`}
          >
            {l.label}
          </Text>
        </Link>
      );
    });

  const ajuda = () => (
    <Pressable
      onPress={abrirAjuda}
      accessibilityRole="button"
      accessibilityLabel="Abrir ajuda do HelpDesk"
      hitSlop={4}
      className="min-h-11 flex-row items-center content-center rounded-lg px-3 py-2 transition-colors hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
    >
      <Text className="text-sm font-semibold text-blue-700">Ajuda</Text>
    </Pressable>
  );

  return (
    <View className="border-b border-slate-200 bg-white">
      <View className="mx-auto w-full max-w-7xl flex-row items-center justify-between gap-3 px-4 py-3 sm:px-6">
        <Link
          href="/"
          accessibilityRole="link"
          accessibilityLabel="Ir para a página inicial"
          className="min-h-11 min-w-11 flex-row items-center justify-center"
        >
          <View className="sm:hidden"><Logo size={40} /></View>
          <View className="hidden sm:flex"><LogoBlox /></View>
        </Link>

        <View className="hidden min-w-0 flex-1 flex-row items-center justify-center gap-1 lg:flex">
          {links()}
          {ajuda()}
        </View>

        <View className="flex-row items-center gap-2">
          {isAuthenticated ? (
            <>
              <Link
                href={canAccessPanel ? "/dashboard" : "/reservas"}
                accessibilityRole="link"
                accessibilityLabel={canAccessPanel ? "Abrir painel administrativo" : "Minhas reservas"}
                className="min-h-11 flex-row items-center justify-center rounded-lg bg-blue-600 px-4 transition-colors hover:bg-blue-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
              >
                <Text className="text-sm font-semibold text-white">{canAccessPanel ? "Painel" : "Reservas"}</Text>
              </Link>
              <Link
                href="/perfil"
                accessibilityRole="link"
                accessibilityLabel="Minha conta"
                className="hidden min-h-11 flex-row items-center justify-center rounded-lg px-3 transition-colors hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 sm:flex"
              >
                <Text className="text-sm font-semibold text-slate-700">Conta</Text>
              </Link>
              <Pressable
                onPress={() => signOut()}
                accessibilityRole="button"
                accessibilityLabel="Encerrar sessão"
                className="hidden min-h-11 flex-row items-center justify-center rounded-lg px-3 transition-colors hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 sm:flex"
              >
                <Text className="text-sm font-medium text-slate-600">Sair</Text>
              </Pressable>
            </>
          ) : (
            <Botao label="Entrar" onPress={() => router.push("/login")} className="rounded-lg px-5 py-2" />
          )}
        </View>
      </View>

      <View className="border-t border-slate-100 px-2 sm:px-4 lg:hidden">
        <View className="mx-auto w-full max-w-7xl flex-row flex-wrap items-center justify-between gap-x-2">
          <View className="flex-row items-center gap-1">
            {links()}
            {ajuda()}
          </View>
          {isAuthenticated ? (
            <View className="flex-row items-center sm:hidden">
              <Link
                href="/perfil"
                accessibilityRole="link"
                accessibilityLabel="Minha conta"
                className="min-h-11 flex-row items-center justify-center rounded-lg px-2 transition-colors hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
              >
                <Text className="text-sm font-semibold text-slate-700">Conta</Text>
              </Link>
              <Pressable
                onPress={() => signOut()}
                accessibilityRole="button"
                accessibilityLabel="Encerrar sessão"
                className="min-h-11 flex-row items-center justify-center rounded-lg px-2 transition-colors hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
              >
                <Text className="text-sm font-medium text-slate-600">Sair</Text>
              </Pressable>
            </View>
          ) : null}
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
        <View className="min-w-0 flex-1">
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
