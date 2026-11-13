/**
 * Grade de vagas — mesma célula para o Mapa do motorista e para o Simulador.
 * No simulador, a célula mostra o STATUS sob o código e aceita seleção.
 */
import { memo, useState } from "react";
import { Platform, Pressable, Text, View, ViewStyle } from "react-native";
import { VAGA_TIPO_LABEL, vagaTone } from "../theme";
import { useLarguraResponsiva } from "../hooks/useLarguraResponsiva";
import { useMovimentoReduzido } from "../hooks/useMovimentoReduzido";
import type { Vaga } from "../types/api";

interface Props {
  vagas: Vaga[];
  /** id em destaque (ex.: próxima vaga sugerida "Ver no mapa") */
  destaqueId?: string | null;
  /** ids marcados (modo seleção do simulador) */
  selecionadas?: Set<string>;
  onPressVaga?: (vaga: Vaga) => void;
  /** rotulo inferior: tipo (mapa) ou status (simulador) */
  rotuloInferior?: "tipo" | "status";
  colunas?: number;
}

function VagaMapa({
  vagas,
  destaqueId,
  selecionadas,
  onPressVaga,
  rotuloInferior = "tipo",
  colunas,
}: Props) {
  const width = useLarguraResponsiva();
  const [larguraGrade, setLarguraGrade] = useState<number | null>(null);
  const reduzido = useMovimentoReduzido();
  // Pressable do react-native-web NÃO aplica style em função: o feedback de
  // pressão precisa de estado próprio para o width/height continuarem fixos.
  const [pressionada, setPressionada] = useState<string | null>(null);
  // O mapa também vive dentro de cards e da coluna lateral do painel. A
  // largura da janela não representa o espaço disponível para suas células.
  const disponivel = larguraGrade ?? Math.max(240, width - 80);
  const desejadas = Math.max(1, colunas ?? (width >= 1024 ? 8 : width >= 640 ? 6 : 4));
  const numColunas = Math.max(1, Math.min(desejadas, Math.floor((disponivel + 8) / 64)));
  const larguraCelula = Math.min(128, Math.floor((disponivel - 8 * (numColunas - 1)) / numColunas));
  const interativo = Boolean(onPressVaga);

  return (
    <View
      className="w-full min-w-0 flex-row flex-wrap justify-start gap-2"
      onLayout={(event) => {
        const nova = Math.floor(event.nativeEvent.layout.width);
        if (nova > 0 && nova !== larguraGrade) setLarguraGrade(nova);
      }}
    >
      {vagas.map((vaga) => {
        const tom = vagaTone(vaga.status);
        const destacada = destaqueId === vaga.id;
        const marcada = selecionadas?.has(vaga.id) ?? false;
        const pressionadaAqui = pressionada === vaga.id;
        const rotulo =
          rotuloInferior === "tipo"
            ? VAGA_TIPO_LABEL[vaga.tipo] ?? vaga.tipo
            : vaga.status;
        const feedback: ViewStyle =
          pressionadaAqui && Platform.OS !== "web" && !reduzido
            ? { opacity: 0.82, transform: [{ scale: 0.97 }] }
            : {};
        const estilo: ViewStyle = {
          width: larguraCelula,
          minHeight: Math.max(44, larguraCelula * 0.62),
          backgroundColor: tom.bg,
          borderColor: marcada || destacada ? "#2563EB" : tom.border,
          borderWidth: marcada ? 2.5 : destacada ? 2 : 1,
          opacity: vaga.status === "inativa" ? 0.6 : 1,
          ...feedback,
        };

        return (
          <Pressable
            key={vaga.id}
            onPress={
              onPressVaga
                ? () => {
                    setPressionada(null);
                    onPressVaga(vaga);
                  }
                : undefined
            }
            onPressIn={interativo ? () => setPressionada(vaga.id) : undefined}
            onPressOut={() => setPressionada(null)}
            disabled={!interativo}
            hitSlop={6}
            accessibilityRole={interativo ? "button" : undefined}
            accessibilityLabel={`Vaga ${vaga.codigo} — ${vaga.status}${
              rotuloInferior === "tipo" ? ` — ${rotulo}` : ""
            }`}
            accessibilityHint={
              interativo
                ? "Toque para selecionar esta vaga"
                : "Status da vaga, somente leitura"
            }
            accessibilityState={{ selected: marcada, disabled: !interativo }}
            {...(Platform.OS === "web" ? { "aria-pressed": marcada } : {})}
            className={`items-center justify-center rounded-xl border py-2.5 ${
              Platform.OS === "web"
                ? "web:transition-all web:duration-200 web:ease-out hover:scale-[1.02] active:scale-[0.98] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 web:motion-reduce:transform-none web:motion-reduce:transition-none web:motion-reduce:hover:transform-none web:motion-reduce:active:transform-none"
                : ""
            }`}
            style={estilo}
          >
            <Text className="text-[13px] font-extrabold" style={{ color: tom.text }}>
              {vaga.codigo}
            </Text>
            <Text className="mt-0.5 text-[11px] font-medium capitalize text-slate-600">
              {rotulo}
            </Text>
          </Pressable>
        );
      })}
    </View>
  );
}

export default memo(VagaMapa);
