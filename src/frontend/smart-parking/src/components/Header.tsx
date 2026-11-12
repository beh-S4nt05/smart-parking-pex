import { useEffect, useState } from "react";
import { Alert, Linking, Platform, Pressable, Text, View } from "react-native";
import { Link, useRouter } from "expo-router";
import { useAuth } from "../hooks/useAuth";
import { API_URL } from "../services/api";
import { Botao, IconeMenu, LogoBlox, Logo } from "./ui";

/**
 * Cabeçalho público unificado, com dois arranjos puramente CSS (sem medir a
 * janela em JS, para não gerar salto de layout nem React #418 na hidratação):
 *
 *  · ≥ xl (1280px): navegação completa + ações de conta em linha;
 *  · < xl: botão "Menu" com dropdown flutuante + ação principal.
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
  { label: "Home", href: "/", destacar: true },
  { label: "Reservar Vaga", href: "/explorar", destacar: true },
  { label: "Status do Estacionamento", href: "/", destacar: false },
  { label: "Lista de Shoppings", href: "/explorar", destacar: false },
] as const;

const CLASSE_LINK =
  "min-h-11 flex-row content-center rounded-lg px-3 transition-colors hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 motion-reduce:transition-none";

export default function Header({ rotaAtual = "/" }: { rotaAtual?: string }) {
  const router = useRouter();
  const { user, isAuthenticated, canAccessPanel, signOut } = useAuth();
  const [menuAberto, setMenuAberto] = useState(false);

  const nomePrim = user?.nome?.split(" ")[0] ?? "";

  // Escape fecha o menu na Web; backdrop e onRequestClose cobrem o nativo.
  useEffect(() => {
    if (!menuAberto || Platform.OS !== "web") return;
    const aoTeclar = (evento: KeyboardEvent) => {
      if (evento.key === "Escape") setMenuAberto(false);
    };
    document.addEventListener("keydown", aoTeclar);
    return () => document.removeEventListener("keydown", aoTeclar);
  }, [menuAberto]);

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

  const links = (compacto: boolean) =>
    LINKS.map((l) => {
      const ativo = l.destacar && rotaAtual === l.href;
      return (
        <Link
          key={l.label}
          href={l.href as never}
          accessibilityRole="link"
          accessibilityLabel={l.label}
          accessibilityState={{ selected: ativo }}
          onPress={() => setMenuAberto(false)}
          className={`${CLASSE_LINK} ${compacto ? "w-full" : ""} ${ativo ? "bg-blue-50" : ""}`}
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

  const ajuda = (compacto: boolean) => (
    <Pressable
      onPress={() => {
        setMenuAberto(false);
        abrirAjuda();
      }}
      accessibilityRole="button"
      accessibilityLabel="Abrir ajuda do HelpDesk"
      hitSlop={4}
      className={`min-h-11 flex-row items-center content-center rounded-lg px-3 py-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 ${compacto ? "w-full" : ""
        }`}
    >
      <Text className="text-sm font-semibold text-blue-700">HelpDesk</Text>
    </Pressable>
  );

  const acaoConta = (
    <>
      {canAccessPanel ? (
        <Link
          href="/dashboard"
          accessibilityRole="link"
          accessibilityLabel="Abrir painel administrativo"
          className="min-h-11 min-w-11 flex-row items-center content-center justify-center rounded-full bg-slate-900 px-4 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
        >
          <Text className="text-sm font-semibold text-white">Painel</Text>
        </Link>
      ) : (
        <Link
          href="/reservas"
          accessibilityRole="link"
          accessibilityLabel="Minhas reservas"
          className="min-h-11 min-w-11 flex-row items-center content-center justify-center rounded-full bg-blue-50 px-4 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
        >
          <Text className="text-sm font-semibold text-blue-700">Minhas reservas</Text>
        </Link>
      )}
      <Link
        href="/perfil"
        accessibilityRole="link"
        accessibilityLabel="Minha conta"
        className="min-h-11 min-w-11 flex-row items-center content-center justify-center rounded-md px-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
      >
        <Text className="text-sm font-semibold text-blue-700">Minha conta</Text>
      </Link>
      <Pressable
        onPress={() => signOut()}
        accessibilityRole="button"
        accessibilityLabel="Encerrar sessão"
        hitSlop={6}
        className="min-h-11 min-w-11 flex-row items-center content-center justify-center rounded-md px-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
      >
        <Text className="text-sm font-medium text-slate-600">Sair</Text>
      </Pressable>
    </>
  );

  return (
    <View className="relative z-30 border-b border-slate-200 bg-white">
      {/* backdrop: fecha o menu sem deslocar o conteúdo */}
      {menuAberto ? (
        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Fechar menu clicando fora"
          accessibilityHint="Fecha o menu sem alterar a página atual"
          onPress={() => setMenuAberto(false)}
          className="absolute inset-0 z-10"
        />
      ) : null}

      <View className="mx-auto w-full max-w-7xl flex-row items-center content-center justify-between gap-3 px-4 py-3 sm:px-6">
        <Link
          href="/"
          accessibilityRole="link"
          accessibilityLabel="Ir para a página inicial"
          className="min-h-11 min-w-11 flex-row items-center justify-center"
        >
          <View className="sm:hidden"><Logo size={40} /></View>
          <View className="hidden sm:flex"><LogoBlox /></View>
        </Link>

        {/* ---------------- desktop (>= 1280px) ---------------- */}
        <View className="hidden min-w-0 flex-row items-center justify-end gap-3 xl:flex">
          <View className="min-w-0 flex-row items-center gap-1">{links(false)}</View>
          {ajuda(false)}
          {isAuthenticated ? (
            <View className="flex-row items-center content-center gap-2">
              <View className="flex-row items-center content-center gap-2 rounded-full bg-slate-100 py-1 pl-1 pr-3">
                <View className="h-7 w-7 items-center content-center justify-center rounded-full bg-blue-600">
                  <Text className="text-xs font-bold text-white">
                    {nomePrim.slice(0, 1).toUpperCase()}
                  </Text>
                </View>
                <Text className="text-[13px] font-semibold text-slate-700">{nomePrim}</Text>
              </View>
              {acaoConta}
            </View>
          ) : (
            <Botao
              label="Entrar"
              onPress={() => router.push("/login")}
              className="rounded-full px-5 py-2"
            />
          )}
        </View>

        {/* ---------------- compacto (< 1280px) ---------------- */}
        <View className="relative z-20 flex-row items-center gap-2 xl:hidden">
          <Pressable
            nativeID="menu-toggle"
            onPress={() => setMenuAberto((v) => !v)}
            accessibilityRole="button"
            accessibilityLabel={menuAberto ? "Fechar menu de navegação" : "Abrir menu de navegação"}
            accessibilityState={{ expanded: menuAberto }}
            aria-expanded={menuAberto}
            hitSlop={4}
            className="min-h-11 min-w-11 flex-row items-center content-center justify-center gap-1.5 rounded-lg border border-slate-200 px-3 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
          >
            <IconeMenu aberto={menuAberto} />
            <Text className="hidden text-sm font-semibold text-slate-700 sm:inline">Menu</Text>
          </Pressable>

          {isAuthenticated ? (
            canAccessPanel ? (
              <Link
                href="/dashboard"
                accessibilityRole="link"
                accessibilityLabel="Ir para o painel"
                className="min-h-11 min-w-11 flex-row items-center content-center justify-center rounded-full bg-slate-900 px-4 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
              >
                <Text className="text-sm font-semibold text-white">Painel</Text>
              </Link>
            ) : (
              <Link
                href="/reservas"
                accessibilityRole="link"
                accessibilityLabel="Minhas reservas"
                className="min-h-11 min-w-11 flex-row items-center content-center justify-center rounded-full bg-blue-50 px-4 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
              >
                <Text className="text-sm font-semibold text-blue-700">Reservas</Text>
              </Link>
            )
          ) : (
            <Botao
              label="Entrar"
              onPress={() => router.push("/login")}
              className="rounded-full px-4 py-2"
            />
          )}

          {menuAberto ? (
            <View
              nativeID="menu-navegacao"
              accessibilityRole="menu"
              accessibilityLabel="Menu de navegação"
              className="absolute right-0 top-full z-30 flex mt-2 w-64 rounded-2xl border border-slate-200 bg-white p-2"
              style={{
                position: "absolute",
                elevation: 12,
                shadowColor: "#0F172A",
                shadowOpacity: 0.16,
                shadowRadius: 20,
                shadowOffset: { width: 0, height: 10 },
              }}
            >
              {links(true)}
              {ajuda(true)}
              {isAuthenticated ? (
                <View className="mt-1 border-t border-slate-100 pt-1">
                  <Link
                    href="/perfil"
                    onPress={() => setMenuAberto(false)}
                    accessibilityRole="link"
                    accessibilityLabel="Minha conta"
                    className="min-h-11 w-full flex-row items-center content-center rounded-lg px-3 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
                  >
                    <Text className="text-sm font-semibold text-blue-700">Minha conta</Text>
                  </Link>
                  <Pressable
                    onPress={() => {
                      setMenuAberto(false);
                      signOut();
                    }}
                    accessibilityRole="button"
                    accessibilityLabel="Encerrar sessão"
                    hitSlop={4}
                    className="min-h-11 w-full flex-row items-center content-center rounded-lg px-3 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
                  >
                    <Text className="text-sm font-medium text-slate-600">Sair</Text>
                  </Pressable>
                </View>
              ) : null}
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
