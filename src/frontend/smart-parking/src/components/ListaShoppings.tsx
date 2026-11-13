/**
 * Lista organizada de shoppings do painel.
 *
 * Substitui a fileira de botões "Todos / nome / nome" que misturava ações com
 * conteúdo. Regras de negócio:
 *  - Admin global: vê "Todos os shoppings" + todos, e é o ÚNICO que pode
 *    alterar a seleção e os vínculos (os vínculos em si ficam na aba Usuários).
 *  - Gestor: vê SOMENTE os shoppings vinculados à conta (pode ser vários) e
 *    pode alternar entre eles. Não vê os outros e não edita a lista.
 *  - Financeiro: vê UM shopping, travado — sem alternância.
 *
 * Nada é flutuante/absolute: a lista participa do fluxo e empurra o conteúdo.
 */
import { Pressable, Text, View } from "react-native";
import type { Estacionamento } from "../types/api";
import { IconeCheck } from "./ui";
import { textoApoio, textoAuxiliar, tituloCard } from "../styles/recipes";

interface Props {
  shoppings: Estacionamento[];
  selecionado: string | null;
  onChange: (id: string | null) => void;
  podeEditar: boolean;
  /** Financeiro: um único shopping, sem nenhuma ação de seleção. */
  travado: boolean;
  carregando?: boolean;
}

function bairro(endereco?: string | null): string {
  if (!endereco) return "Manaus, AM";
  // Endereço do seed: "Av. Norte, 200 - Cidade Nova, Manaus - AM".
  // O último trecho é a UF; o bairro/cidade vem no penúltimo.
  const partes = endereco.split(" - ").map((p) => p.trim()).filter(Boolean);
  const ultimo = partes[partes.length - 1] ?? "";
  const uf = /^[A-Za-z]{2}$/.test(ultimo) ? ultimo : "";
  const local = uf ? (partes[partes.length - 2] ?? ultimo) : ultimo;
  const cidade = local.split(",").map((p) => p.trim()).filter(Boolean);
  const bairroNome = cidade[0] || "Manaus";
  return uf ? `${bairroNome}, ${uf}` : local || "Manaus, AM";
}

export default function ListaShoppings({
  shoppings,
  selecionado,
  onChange,
  podeEditar,
  travado,
  carregando = false,
}: Props) {
  const permiteSelecao = podeEditar || (!travado && shoppings.length > 1);
  const mostrarTodos = podeEditar;

  const linha = (
    id: string | null,
    titulo: string,
    subtitulo: string,
    ativo: boolean,
    acao: boolean,
    extras?: string,
  ) => (
    <Pressable
      key={id ?? "todos"}
      testID={`shopping-linha-${id ?? "todos"}`}
      onPress={acao ? () => onChange(id) : undefined}
      disabled={!acao}
      accessibilityRole="button"
      accessibilityLabel={acao ? `Selecionar ${titulo}` : titulo}
      accessibilityState={{ selected: ativo, disabled: !acao }}
      className={`min-h-11 flex-row items-center gap-3 rounded-xl border px-3 py-2.5 transition-colors motion-reduce:transition-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 ${
        ativo ? "border-blue-300 bg-blue-50" : "border-slate-200 bg-white"
      } ${acao ? "hover:bg-blue-50 active:bg-blue-100" : ""}`}
    >
      <View
        className={`h-5 w-5 shrink-0 items-center justify-center rounded-full border-2 ${
          ativo ? "border-blue-600 bg-blue-600" : "border-slate-300 bg-white"
        }`}
      >
        {ativo ? <IconeCheck cor="#FFFFFF" tamanho={9} /> : null}
      </View>
      <View className="min-w-0 flex-1">
        <Text
          className={`text-[14px] font-semibold ${ativo ? "text-blue-800" : "text-slate-800"}`}
        >
          {titulo}
        </Text>
        <Text className="mt-0.5 text-[12px] text-slate-600">
          {subtitulo}
        </Text>
      </View>
      {extras ? (
        <View className="shrink-0 rounded-full bg-emerald-50 px-2.5 py-1">
          <Text className="text-[11px] font-semibold text-emerald-700">{extras}</Text>
        </View>
      ) : null}
    </Pressable>
  );

  return (
    <View className="mb-4 gap-2 rounded-2xl border border-slate-200 bg-white p-4 3xl:p-5">
      <View className="min-w-0 flex-row flex-wrap items-center justify-between gap-2">
        <Text className={tituloCard}>Shoppings</Text>
        <Text className={textoAuxiliar}>
          {podeEditar
            ? "Somente o administrador altera esta lista"
            : travado
              ? "Vinculado à sua conta · travado"
              : "Seus shoppings vinculados · lista travada"}
        </Text>
      </View>

      {carregando ? (
        <Text className={textoApoio}>Carregando shoppings…</Text>
      ) : (
        <View className="gap-2">
          {mostrarTodos
            ? linha(
                null,
                "Todos os shoppings",
                "Visão consolidada da rede",
                selecionado === null,
                podeEditar,
              )
            : null}
          {shoppings.map((e) =>
            linha(
              e.id,
              e.nome,
              bairro(e.endereco),
              e.id === selecionado,
              permiteSelecao,
              `${e.vagas_disponiveis_total ?? 0} livres`,
            ),
          )}
          {shoppings.length === 0 ? (
            <Text className={textoApoio}>Nenhum shopping vinculado.</Text>
          ) : null}
        </View>
      )}

      {!podeEditar ? (
        <Text className={textoAuxiliar}>
          Vínculos são definidos pelo administrador global. Você só acessa os
          shoppings listados acima.
        </Text>
      ) : null}
    </View>
  );
}
