/**
 * Alert da WEB — shim de emergência (auditoria E2E, rodada 12).
 *
 * O `Alert` do react-native-web (0.21) é LITERALMENTE um no-op:
 *   class Alert { static alert() {} }   // node_modules/react-native-web/exports/Alert
 * → todo `Alert.alert("Cancelar reserva", ..., [{onPress: cancelar}])` nas
 * telas (reservas, shopping/[id], dashboard, perfil…) NÃO ABRE NADA no
 * navegador e o `onPress` nunca roda. Na prática: o botão "Cancelar" sumia
 * sem erro nenhum — exatamente o bug relatado ("problema na parte de
 * cancelar reservas/vagas na web").
 *
 * Em vez dos 50 call sites ganharem um Modal novo, este módulo SUBSTITUI
 * `Alert.alert` UMA vez no boot — SOMENTE na web — mapeando para o diálogo
 * padrão do navegador:
 *   · sem botões            → window.alert(msg)  (feedback simples)
 *   · 1 botão               → window.alert + onPress do botão
 *   · ≥2 (cancel+confirmar) → window.confirm; OK → botão não-cancel,
 *                              Cancelar → o botão style:"cancel"
 * O fluxo de cada tela (onPress → API → refresh) permanece idêntico ao
 * nativo; nenhum import de tela muda.
 */
import { Alert, Platform } from "react-native";

type BotãoAlerta = {
  text?: string;
  style?: "default" | "cancel" | "destructive";
  onPress?: () => void;
};
type AlertFn = (
  titulo?: string,
  mensagem?: string,
  botões?: BotãoAlerta[],
  opções?: { cancelable?: boolean; onDismiss?: () => void },
) => void;

type JanelaWeb = {
  alert: (m?: string) => void;
  confirm: (m?: string) => boolean;
};

let aplicado = false;

export function instalarAlertaWeb(): void {
  if (aplicado || Platform.OS !== "web") return;
  aplicado = true;

  const w = globalThis as unknown as JanelaWeb;
  // ambientes sem diálogo (SSR do static export, headless) → shim silencioso
  if (typeof w.alert !== "function" || typeof w.confirm !== "function") return;

  const texto = (t?: string, m?: string) =>
    [t, m].filter((x) => x && x.trim()).join("\n\n");

  const shim: AlertFn = (titulo, mensagem, botões, opções) => {
    const bs = (Array.isArray(botões) ? botões : []).filter(
      (b) => b && (b.onPress || b.text),
    );
    if (bs.length === 0) {
      w.alert(texto(titulo, mensagem));
      return;
    }
    if (bs.length === 1) {
      w.alert(texto(titulo, mensagem));
      bs[0].onPress?.();
      return;
    }
    const cancelar = bs.find((b) => b.style === "cancel");
    const confirmar = bs.find((b) => b.style !== "cancel") ?? bs[bs.length - 1];
    const confirmMsg =
      texto(titulo, mensagem) +
      (confirmar?.text ? `\n\n— ${confirmar.text}` : "") +
      (cancelar ? "" : "\n\n(OK = continuar · Cancelar = desfazer)");
    if (w.confirm(confirmMsg)) confirmar?.onPress?.();
    else if (cancelar) cancelar.onPress?.();
    else opções?.onDismiss?.();
  };

  (Alert as unknown as { alert: AlertFn }).alert = shim;
}
