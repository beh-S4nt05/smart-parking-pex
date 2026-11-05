import { useEffect, useState } from "react";
import { Platform, useWindowDimensions } from "react-native";

/**
 * Largura responsiva compatível com o pré-render estático do Expo Router.
 *
 * No Web, servidor e primeira renderização do cliente começam com o mesmo
 * viewport móvel de referência. Só depois da hidratação a largura real é
 * aplicada. Isso evita o React #418 sem desativar o pré-render e sem gerar
 * medidas negativas no mapa. No nativo, a largura real continua imediata,
 * inclusive em rotações e mudanças de janela.
 */
export function useLarguraResponsiva(): number {
  const { width } = useWindowDimensions();
  const [larguraWeb, setLarguraWeb] = useState(390);

  useEffect(() => {
    if (Platform.OS === "web") setLarguraWeb(width);
  }, [width]);

  return Platform.OS === "web" ? larguraWeb : width;
}
