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
  const reduzido = useMovimentoReduzido();
  // Pressable do react-native-web NÃO aplica style em função: o feedback de
  // pressão precisa de estado próprio para o width/height continuarem fixos.
  const [pressionada, setPressionada] = useState<string | null>(null);
  const numColunas = Math.max(1, colunas ?? (width >= 1024 ? 8 : width >= 640 ? 6 : 4));
  // Piso de 56px: a célula continua sendo um alvo de toque confortável mesmo
  // em viewports estreitos; o teto de 128px evita cards gigantes no desktop.
  const larguraBase = Math.floor(
    (Math.min(Math.max(width, 320), 1200) - 96) / numColunas,
  );
  const larguraCelula = Math.max(56, Math.min(128, larguraBase));
  const interativo = Boolean(onPressVaga);

  return (
    <View className="flex-row flex-wrap justify-start gap-2">
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
                ? "transition-all duration-200 ease-out hover:scale-[1.02] active:scale-[0.98] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 motion-reduce:transform-none motion-reduce:transition-none motion-reduce:hover:transform-none motion-reduce:active:transform-none"
                : ""
            }`}
            style={estilo}
          >
            <Text className="text-[13px] font-extrabold" style={{ color: tom.text }}>
              {vaga.codigo}
            </Text>
            <Text className="mt-0.5 text-[10px] font-medium capitalize text-slate-500">
              {rotulo}
            </Text>
          </Pressable>
        );
      })}
    </View>
  );
}

export default memo(VagaMapa);
