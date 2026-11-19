/**
 * Barra discreta no Hero da V1, compartilhada entre web e mobile.
 * Exibe o estado real da consulta (não inventa percentuais de progresso).
 * Com movimento reduzido, permanece estática e conserva o texto do estado.
 */
import { useEffect, useRef, useState } from "react";
import { Animated, Easing, Platform, Text, View } from "react-native";
import { useMovimentoReduzido } from "../hooks/useMovimentoReduzido";

type Props = {
  atualizando: boolean;
  erro?: boolean;
  escura?: boolean;
};

export default function BarraAtualizacaoHero({
  atualizando,
  erro = false,
  escura = false,
}: Props) {
  const reduzido = useMovimentoReduzido();
  const [larguraTrilho, setLarguraTrilho] = useState(0);
  const animacao = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    animacao.stopAnimation();
    animacao.setValue(0);
    if (!atualizando || reduzido || larguraTrilho <= 0) return;

    const ciclo = Animated.loop(
      Animated.timing(animacao, {
        toValue: 1,
        duration: 1050,
        easing: Easing.inOut(Easing.quad),
        useNativeDriver: Platform.OS !== "web",
      }),
    );
    ciclo.start();
    return () => ciclo.stop();
  }, [animacao, atualizando, larguraTrilho, reduzido]);

  const corPrincipal = erro && !atualizando ? "#D97706" : escura ? "#70E1B4" : "#2563EB";
  const legenda = atualizando
    ? "Atualizando vagas..."
    : erro
      ? "Atualização indisponível — exibindo os últimos dados"
      : "Vagas sincronizadas · nova consulta a cada 1,5 s";

  return (
    <View
      style={{ alignSelf: "stretch", width: "100%", marginTop: 14 }}
      accessible
      accessibilityRole={atualizando ? "progressbar" : "text"}
      accessibilityLabel={legenda}
    >
      <View
        testID="hero-barra-atualizacao"
        onLayout={(evento) => {
          const largura = evento.nativeEvent.layout.width;
          if (Math.abs(largura - larguraTrilho) >= 1) setLarguraTrilho(largura);
        }}
        style={{
          height: 5,
          borderRadius: 6,
          overflow: "hidden",
          backgroundColor: escura ? "#2D4568" : "#DBEAFE",
        }}
      >
        {atualizando ? (
          <Animated.View
            testID="hero-barra-indeterminada"
            style={{
              height: 5,
              width: "36%",
              borderRadius: 6,
              backgroundColor: corPrincipal,
              transform: [
                {
                  translateX: reduzido
                    ? 0
                    : animacao.interpolate({
                        inputRange: [0, 1],
                        outputRange: [-larguraTrilho * 0.36, larguraTrilho],
                      }),
                },
              ],
            }}
          />
        ) : (
          <View
            style={{
              height: 5,
              width: "100%",
              borderRadius: 6,
              backgroundColor: corPrincipal,
              opacity: erro ? 0.65 : 0.45,
            }}
          />
        )}
      </View>
      <Text
        style={{
          marginTop: 7,
          color: escura ? "#C7D8F1" : "#475569",
          fontSize: 11,
          fontWeight: "600",
          textAlign: "center",
        }}
      >
        {legenda}
      </Text>
    </View>
  );
}
