import { useState } from "react";
import { FlatList, Modal, Pressable, ScrollView, Text, View, useWindowDimensions } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useRouter } from "expo-router";
import type { Estacionamento } from "../types/api";
import { formatarMinutos } from "./ui";

const C = { navy: "#0F1E38", blue: "#2563EB", ink: "#15233B", muted: "#64748B", canvas: "#F3F7FD", line: "#E3EAF4", green: "#059669" };

type Props = {
  shoppings: Estacionamento[];
  selecionadoId: string | null;
  onSelect: (id: string) => void;
  onBuscar: () => void;
  tempoMedio: number | null;
  loading: boolean;
  erro: string | null;
  refresh: () => void;
  onAbrirShopping: (id: string) => void;
};

export default function MobileHome({ shoppings, selecionadoId, onSelect, onBuscar, tempoMedio, loading, erro, refresh, onAbrirShopping }: Props) {
  const router = useRouter();
  const { height } = useWindowDimensions();
  const [picker, setPicker] = useState(false);
  const selecionado = shoppings.find(s => s.id === selecionadoId) ?? shoppings[0] ?? null;
  const total = selecionado?.total_vagas ?? 0;
  const livres = selecionado?.vagas_disponiveis_total ?? 0;
  const taxa = total > 0 ? Math.round(livres / total * 100) : 0;
  const desativado = !selecionado;

  return (
    <View style={{ flex: 1, backgroundColor: C.canvas }}>
      <ScrollView contentContainerStyle={{ paddingBottom: 40 }} showsVerticalScrollIndicator={false}>
        <View style={{ backgroundColor: C.navy, paddingHorizontal: 22, paddingTop: 18, paddingBottom: 38, borderBottomLeftRadius: 30, borderBottomRightRadius: 30 }}>
          <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between", marginBottom: 28 }}>
            <View style={{ flexDirection: "row", alignItems: "center", gap: 11 }}>
              <View style={{ width: 44, height: 44, borderRadius: 14, backgroundColor: "#2563EB", alignItems: "center", justifyContent: "center" }}>
                <Ionicons name="car-sport" size={24} color="#FFFFFF" />
              </View>
              <View>
                <Text style={{ fontWeight: "800", color: "white", fontSize: 18 }}>Smart Parking</Text>
                <Text style={{ color: "#AFC4E3", fontSize: 11, marginTop: 1 }}>Sua vaga, sem complicação</Text>
              </View>
            </View>
            <Pressable onPress={() => router.push("/login")} accessibilityLabel="Abrir conta" style={{ width: 42, height: 42, backgroundColor: "#253B5B", borderRadius: 14, alignItems: "center", justifyContent: "center" }}>
              <Ionicons name="person-outline" size={22} color="white" />
            </Pressable>
          </View>
          <View style={{ alignSelf: "flex-start", backgroundColor: "#174F51", paddingHorizontal: 12, paddingVertical: 7, borderRadius: 50, flexDirection: "row", alignItems: "center", gap: 7, marginBottom: 15 }}>
            <View style={{ width: 7, height: 7, borderRadius: 4, backgroundColor: "#5EE1B2" }} />
            <Text style={{ color: "#B5F6D7", fontWeight: "700", fontSize: 11 }}>VAGAS EM TEMPO REAL</Text>
          </View>
          <Text style={{ color: "#FFFFFF", fontWeight: "800", fontSize: 32, lineHeight: 38, letterSpacing: -0.8 }}>Estacione com{"\n"}mais facilidade.</Text>
          <Text style={{ color: "#B5C7E2", fontSize: 14, lineHeight: 21, marginTop: 11 }}>Escolha seu shopping, encontre uma vaga e aproveite seu tempo.</Text>
        </View>

        <View style={{ paddingHorizontal: 18, marginTop: -20 }}>
          <View style={{ backgroundColor: "#FFFFFF", borderRadius: 22, padding: 18, shadowColor: "#0F1E38", shadowOpacity: 0.1, shadowRadius: 14, elevation: 4 }}>
            <Text style={{ color: C.muted, fontSize: 11, fontWeight: "800", letterSpacing: 1, marginBottom: 12 }}>ONDE VAMOS ESTACIONAR?</Text>
            <Pressable accessibilityRole="button" accessibilityLabel="Selecionar shopping" disabled={shoppings.length === 0} onPress={() => setPicker(true)} style={{ borderColor: C.line, borderWidth: 1, borderRadius: 15, minHeight: 64, flexDirection: "row", alignItems: "center", paddingHorizontal: 13, gap: 11, backgroundColor: "#F8FAFF" }}>
              <Ionicons name="location" size={23} color={C.blue} />
              <View style={{ flex: 1 }}>
                <Text style={{ color: C.muted, fontSize: 11, marginBottom: 2 }}>Shopping selecionado</Text>
                <Text style={{ color: C.ink, fontSize: 14, fontWeight: "700" }} numberOfLines={1}>{selecionado?.nome ?? "Carregando shoppings..."}</Text>
              </View>
              <Ionicons name="chevron-down" size={20} color={C.muted} />
            </Pressable>
            <Pressable disabled={desativado} onPress={onBuscar} accessibilityRole="button" accessibilityLabel="Encontrar vagas disponíveis" style={{ backgroundColor: desativado ? "#8EADE9" : C.blue, marginTop: 12, borderRadius: 15, minHeight: 56, alignItems: "center", justifyContent: "center", flexDirection: "row", gap: 10 }}>
              <Ionicons name="navigate" size={18} color="white" />
              <Text style={{ fontSize: 15, fontWeight: "800", color: "white" }}>Encontrar minha vaga</Text>
              <Ionicons name="arrow-forward" size={18} color="white" />
            </Pressable>
          </View>

          {erro ? <View style={{ backgroundColor: "#FEF3C7", padding: 12, borderRadius: 12, marginTop: 16 }}><Text style={{ color: "#92400E" }}>{erro}</Text></View> : null}

          <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between", marginTop: 28, marginBottom: 14 }}>
            <View>
              <Text style={{ fontSize: 20, fontWeight: "800", color: C.ink }}>Visão geral</Text>
              <Text style={{ color: C.muted, fontSize: 12, marginTop: 3 }}>Disponibilidade neste momento</Text>
            </View>
            <Pressable onPress={refresh} accessibilityRole="button" accessibilityLabel="Atualizar disponibilidade" style={{ width: 40, height: 40, borderRadius: 13, backgroundColor: "#E6EDFA", alignItems: "center", justifyContent: "center" }}>
              <Ionicons name="refresh" size={21} color={C.blue} />
            </Pressable>
          </View>

          <View style={{ backgroundColor: C.navy, padding: 20, borderRadius: 21, marginBottom: 12, flexDirection: "row", alignItems: "center", justifyContent: "space-between" }}>
            <View>
              <Text style={{ color: "#B7C8E2", fontSize: 12 }}>Vagas disponíveis</Text>
              <View style={{ flexDirection: "row", alignItems: "baseline", gap: 7, marginTop: 4 }}>
                <Text style={{ color: "#FFFFFF", fontSize: 43, fontWeight: "900" }}>{livres}</Text>
                <Text style={{ color: "#B7C8E2", fontSize: 14 }}>de {total}</Text>
              </View>
              <Text style={{ color: "#70E1B4", fontSize: 12, fontWeight: "700", marginTop: 4 }}>{taxa}% das vagas estão livres</Text>
            </View>
            <View style={{ width: 76, height: 76, borderRadius: 38, borderWidth: 7, borderColor: "#25C994", alignItems: "center", justifyContent: "center", backgroundColor: "#1B3553" }}>
              <Ionicons name="car-outline" color="#FFFFFF" size={29} />
            </View>
          </View>

          <View style={{ flexDirection: "row", gap: 12 }}>
            <View style={{ flex: 1, backgroundColor: "white", borderRadius: 18, padding: 17 }}>
              <Ionicons name="time-outline" color="#7C3AED" size={24} />
              <Text style={{ fontSize: 19, fontWeight: "800", color: C.ink, marginTop: 11 }}>{formatarMinutos(tempoMedio)}</Text>
              <Text style={{ fontSize: 12, color: C.muted, marginTop: 3 }}>Permanência média</Text>
            </View>
            <View style={{ flex: 1, backgroundColor: "white", borderRadius: 18, padding: 17 }}>
              <Ionicons name="layers-outline" color={C.blue} size={24} />
              <Text style={{ fontSize: 19, fontWeight: "800", color: C.ink, marginTop: 11 }}>{total}</Text>
              <Text style={{ fontSize: 12, color: C.muted, marginTop: 3 }}>Total de vagas</Text>
            </View>
          </View>

          <View style={{ marginTop: 30, marginBottom: 14 }}>
            <Text style={{ color: C.ink, fontSize: 20, fontWeight: "800" }}>Explore os shoppings</Text>
            <Text style={{ color: C.muted, fontSize: 12, marginTop: 4 }}>Toque para abrir o mapa de vagas</Text>
          </View>
          {shoppings.map((s) => {
            const vagas = s.vagas_disponiveis_total ?? 0;
            return <Pressable key={s.id} accessibilityRole="button" accessibilityLabel={`Abrir ${s.nome}`} onPress={() => onAbrirShopping(s.id)} style={{ backgroundColor: "white", borderRadius: 18, padding: 16, marginBottom: 11, flexDirection: "row", alignItems: "center", gap: 13 }}>
              <View style={{ backgroundColor: "#EAF1FF", width: 50, height: 50, borderRadius: 15, alignItems: "center", justifyContent: "center" }}><Ionicons name="business-outline" size={25} color={C.blue} /></View>
              <View style={{ flex: 1 }}>
                <Text numberOfLines={2} style={{ color: C.ink, fontSize: 14, fontWeight: "800" }}>{s.nome}</Text>
                <Text style={{ color: C.muted, fontSize: 12, marginTop: 4 }}>{vagas} vagas disponíveis</Text>
              </View>
              <Ionicons name="chevron-forward" size={21} color={C.blue} />
            </Pressable>;
          })}
          {loading && shoppings.length === 0 ? <Text style={{ textAlign: "center", color: C.muted, padding: 20 }}>Consultando estacionamentos...</Text> : null}
        </View>
      </ScrollView>

      <View style={{ backgroundColor: "white", borderTopWidth: 1, borderColor: C.line, paddingHorizontal: 14, paddingTop: 9, paddingBottom: 12, flexDirection: "row", justifyContent: "space-around" }}>
        {([{ label: "Início", icon: "home", href: "/" }, { label: "Explorar", icon: "compass-outline", href: "/explorar" }, { label: "Reservas", icon: "ticket-outline", href: "/reservas" }, { label: "Conta", icon: "person-outline", href: "/perfil" }] as const).map(item =>
          <Pressable key={item.label} accessibilityRole="button" accessibilityLabel={item.label} onPress={() => router.push(item.href as never)} style={{ minWidth: 62, padding: 5, alignItems: "center", gap: 4 }}>
            <Ionicons name={item.icon} size={22} color={item.label === "Início" ? C.blue : "#71819A"} />
            <Text style={{ color: item.label === "Início" ? C.blue : "#71819A", fontSize: 10, fontWeight: "700" }}>{item.label}</Text>
          </Pressable>
        )}
      </View>

      <Modal visible={picker} transparent animationType="fade" onRequestClose={() => setPicker(false)}>
        <View style={{ flex: 1, backgroundColor: "rgba(8,18,38,0.55)", justifyContent: "center", padding: 20 }}>
          <Pressable onPress={() => setPicker(false)} style={{ position: "absolute", top: 0, bottom: 0, left: 0, right: 0 }} />
          <View style={{ backgroundColor: "white", borderRadius: 23, padding: 18, maxHeight: height * 0.7 }}>
            <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 15 }}>
              <Text style={{ fontWeight: "800", fontSize: 18, color: C.ink }}>Escolher shopping</Text>
              <Pressable onPress={() => setPicker(false)} accessibilityLabel="Fechar lista" style={{ padding: 8 }}><Ionicons name="close" size={23} color={C.muted} /></Pressable>
            </View>
            <FlatList data={shoppings} keyExtractor={s => s.id} ItemSeparatorComponent={() => <View style={{ height: 9 }} />} renderItem={({ item }) =>
              <Pressable accessibilityRole="button" accessibilityLabel={item.nome} onPress={() => { onSelect(item.id); setPicker(false); }} style={{ borderWidth: 1, borderColor: selecionado?.id === item.id ? "#93C5FD" : C.line, backgroundColor: selecionado?.id === item.id ? "#EAF1FF" : "#F8FAFF", borderRadius: 13, minHeight: 65, padding: 12, flexDirection: "row", alignItems: "center", gap: 10 }}>
                <Ionicons name="location-outline" size={21} color={C.blue} />
                <View style={{ flex: 1 }}><Text style={{ fontWeight: "700", color: C.ink }}>{item.nome}</Text><Text style={{ marginTop: 4, fontSize: 11, color: C.muted }}>{item.vagas_disponiveis_total ?? 0} vagas livres</Text></View>
                {selecionado?.id === item.id ? <Ionicons name="checkmark-circle" size={22} color={C.blue} /> : null}
              </Pressable>
            } />
          </View>
        </View>
      </Modal>
    </View>
  );
}
