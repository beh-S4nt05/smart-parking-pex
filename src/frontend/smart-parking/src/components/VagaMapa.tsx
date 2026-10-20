/**
 * Grade de vagas — mesma célula para o Mapa do motorista e para o Simulador.
 * No simulador, a célula mostra o STATUS sob o código e aceita seleção.
 */
import { memo } from "react";
import { Pressable, Text, View, useWindowDimensions } from "react-native";
import { VAGA_TIPO_LABEL, vagaTone } from "../theme";
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
  const { width } = useWindowDimensions();
  const numColunas = colunas ?? (width >= 1024 ? 8 : width >= 640 ? 6 : 4);
  const larguraCelula = Math.floor(
    Math.min((Math.min(width, 1200) - 96) / numColunas, 128),
  );

  return (
    <View className="flex-row flex-wrap justify-start gap-2">
      {vagas.map((vaga) => {
        const tom = vagaTone(vaga.status);
        const destacada = destaqueId === vaga.id;
        const marcada = selecionadas?.has(vaga.id) ?? false;
        const rotulo =
          rotuloInferior === "tipo"
            ? VAGA_TIPO_LABEL[vaga.tipo] ?? vaga.tipo
            : vaga.status;
        return (
          <Pressable
            key={vaga.id}
            onPress={onPressVaga ? () => onPressVaga(vaga) : undefined}
            accessibilityRole={onPressVaga ? "button" : undefined}
            accessibilityLabel={`Vaga ${vaga.codigo} — ${vaga.status}`}
            className="items-center justify-center rounded-xl border py-2.5"
            style={{
              width: larguraCelula,
              minHeight: larguraCelula * 0.62,
              backgroundColor: tom.bg,
              borderColor: marcada || destacada ? "#2563EB" : tom.border,
              borderWidth: marcada ? 2.5 : destacada ? 2 : 1,
              opacity: vaga.status === "inativa" ? 0.6 : 1,
            }}
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
