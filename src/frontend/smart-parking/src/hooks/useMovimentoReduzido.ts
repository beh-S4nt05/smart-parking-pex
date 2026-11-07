import { useEffect, useState } from "react";
import { AccessibilityInfo, Platform } from "react-native";

type Assinatura = { remove: () => void } | undefined;

/**
 * Preferência real de `prefers-reduced-motion` / "Reduzir movimento" do SO.
 *
 * No Web usa `matchMedia` (inclusive mudança em tempo real); no nativo usa
 * `AccessibilityInfo`. Componentes que animam com `Animated` consultam este
 * hook para ficarem parados sem perder cor, foco, contraste ou conteúdo.
 */
export function useMovimentoReduzido(): boolean {
  const [reduzido, setReduzido] = useState(false);

  useEffect(() => {
    let ativo = true;
    let assinatura: Assinatura;

    if (
      Platform.OS === "web" &&
      typeof window !== "undefined" &&
      typeof window.matchMedia === "function"
    ) {
      const consulta = window.matchMedia("(prefers-reduced-motion: reduce)");
      const atualizar = () => {
        if (ativo) setReduzido(consulta.matches);
      };
      atualizar();
      if (typeof consulta.addEventListener === "function") {
        consulta.addEventListener("change", atualizar);
        assinatura = {
          remove: () => consulta.removeEventListener("change", atualizar),
        };
      } else if (typeof consulta.addListener === "function") {
        consulta.addListener(atualizar);
        assinatura = { remove: () => consulta.removeListener(atualizar) };
      }
      return () => {
        ativo = false;
        assinatura?.remove();
      };
    }

    if (Platform.OS !== "web") {
      AccessibilityInfo.isReduceMotionEnabled()
        .then((valor) => {
          if (ativo) setReduzido(Boolean(valor));
        })
        .catch(() => {});
      const evento = AccessibilityInfo.addEventListener(
        "reduceMotionChanged",
        (valor) => {
          if (ativo) setReduzido(Boolean(valor));
        },
      );
      assinatura = { remove: () => evento?.remove?.() };
    }

    return () => {
      ativo = false;
      assinatura?.remove();
    };
  }, []);

  return reduzido;
}
