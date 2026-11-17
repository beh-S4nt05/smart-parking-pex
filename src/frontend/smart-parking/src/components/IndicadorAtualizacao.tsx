import { ActivityIndicator, Text, View } from "react-native";

/** Barra pequena: nunca cobre o mapa nem bloqueia toque durante auto-sync. */
export default function IndicadorAtualizacao({
  ativo,
  rotulo = "Sincronizando dados",
}: {
  ativo: boolean;
  rotulo?: string;
}) {
  return (
    <View
      accessibilityRole="progressbar"
      accessibilityLabel={rotulo}
      accessibilityState={{ busy: ativo }}
      style={{
        minHeight: 22, paddingHorizontal: 16,
        justifyContent: "flex-end",
        alignItems: "center", flexDirection: "row",
        gap: 7, backgroundColor: "transparent",
      }}
      pointerEvents="none"
    >
      {ativo ? (
        <>
          <ActivityIndicator size="small" color="#2563EB" />
          <Text style={{ color: "#64748B", fontSize: 10 }}>{rotulo}</Text>
        </>
      ) : null}
    </View>
  );
}
