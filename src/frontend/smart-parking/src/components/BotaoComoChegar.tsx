/** Abre rotas reais no Google Maps (web + Android/iOS), sem API paga. */
import { Alert, Linking, Pressable, Text } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import type { Estacionamento } from "../types/api";
import { urlComoChegar } from "../services/rotasShoppings";

type Props = {
  shopping: Estacionamento | null;
  onErro?: () => void;
};

export default function BotaoComoChegar({ shopping, onErro }: Props) {
  const url = urlComoChegar(shopping);
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={shopping ? `Como chegar ao ${shopping.nome} pelo Google Maps` : "Como chegar pelo Google Maps"}
      accessibilityHint="Abre a navegação até o shopping no Google Maps"
      accessibilityState={{ disabled: !url }}
      disabled={!url}
      onPress={() => {
        if (!url) return;
        void Linking.openURL(url).catch(() => {
          if (onErro) onErro();
          else Alert.alert("Google Maps indisponível", "Não foi possível abrir a rota. Verifique a conexão.");
        });
      }}
      style={{
        flexDirection: "row",
        alignItems: "center",
        alignSelf: "flex-start",
        gap: 7,
        backgroundColor: "#EFF6FF",
        borderRadius: 12,
        borderWidth: 1,
        borderColor: "#BFDBFE",
        minHeight: 48,
        paddingHorizontal: 14,
        paddingVertical: 10,
        opacity: url ? 1 : 0.6,
      }}
    >
      <Ionicons name="navigate-outline" size={18} color="#1D4ED8" />
      <Text style={{ fontSize: 13, fontWeight: "700", color: "#1D4ED8" }}>
        Como chegar
      </Text>
    </Pressable>
  );
}
