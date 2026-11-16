import { Pressable, Text, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import type { Estacionamento } from "../types/api";

export default function MobileShoppingList({
  shoppings,
  onPress,
}: {
  shoppings: Estacionamento[];
  onPress: (est: Estacionamento) => void;
}) {
  return (
    <View style={{ gap: 12 }}>
      {shoppings.map((est) => {
        const livres = est.vagas_disponiveis_total ?? 0;
        const total = est.total_vagas ?? 0;
        const pct = total > 0 ? Math.round((livres / total) * 100) : 0;
        const cor = pct >= 25 ? "#059669" : pct >= 10 ? "#B45309" : "#DC2626";
        return (
          <Pressable
            key={est.id}
            accessibilityRole="button"
            accessibilityLabel={`${est.nome}, ${livres} vagas livres`}
            onPress={() => onPress(est)}
            style={{
              padding: 16,
              backgroundColor: "#FFFFFF",
              borderRadius: 19,
              minHeight: 104,
              gap: 13,
            }}
          >
            <View style={{ flexDirection: "row", alignItems: "center", gap: 13 }}>
              <View style={{ width: 48, height: 48, backgroundColor: "#EAF1FF", borderRadius: 15, justifyContent: "center", alignItems: "center" }}>
                <Ionicons name="business-outline" size={25} color="#2563EB" />
              </View>
              <View style={{ flex: 1, minWidth: 0 }}>
                <Text style={{ color: "#15233B", fontSize: 16, fontWeight: "800" }} numberOfLines={2}>{est.nome}</Text>
                <Text style={{ color: "#71819A", fontSize: 12, marginTop: 3 }}>
                  {est.total_andares} andares · {total} vagas
                </Text>
              </View>
              <Ionicons name="chevron-forward" size={22} color="#2563EB" />
            </View>
            <View style={{ borderTopWidth: 1, borderColor: "#EEF2F7", paddingTop: 11, flexDirection: "row", alignItems: "center", justifyContent: "space-between" }}>
              <View style={{ flexDirection: "row", gap: 6, alignItems: "center" }}>
                <View style={{ width: 7, height: 7, borderRadius: 5, backgroundColor: cor }} />
                <Text style={{ fontSize: 12, color: "#64748B" }}>Disponibilidade atual</Text>
              </View>
              <Text style={{ color: cor, fontSize: 13, fontWeight: "800" }}>{livres} livres · {pct}%</Text>
            </View>
          </Pressable>
        );
      })}
    </View>
  );
}
