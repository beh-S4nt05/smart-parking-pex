import type { ReactNode } from "react";
import { Pressable, Text, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useRouter } from "expo-router";

const C = {
  navy: "#0F1E38",
  blue: "#2563EB",
  muted: "#516078",
  line: "#E3EAF4",
};

type Active = "home" | "explorar" | "reservas" | "conta";

const ITEMS = [
  { key: "home", label: "Início", icon: "home-outline", activeIcon: "home", href: "/" },
  { key: "explorar", label: "Explorar", icon: "compass-outline", activeIcon: "compass", href: "/explorar" },
  { key: "reservas", label: "Reservas", icon: "ticket-outline", activeIcon: "ticket", href: "/reservas" },
  { key: "conta", label: "Conta", icon: "person-outline", activeIcon: "person", href: "/perfil" },
] as const;

export function MobileBottomNav({ active }: { active: Active }) {
  const router = useRouter();
  return (
    <View
      style={{
        backgroundColor: "#FFFFFF",
        borderTopWidth: 1,
        borderColor: C.line,
        paddingHorizontal: 10,
        paddingTop: 8,
        paddingBottom: 10,
        flexDirection: "row",
        justifyContent: "space-around",
      }}
    >
      {ITEMS.map((item) => {
        const selected = item.key === active;
        return (
          <Pressable
            key={item.key}
            accessibilityRole="button"
            accessibilityLabel={item.label}
            accessibilityState={{ selected }}
            onPress={() => router.push(item.href as never)}
            style={{
              minWidth: 64,
              minHeight: 48,
              borderRadius: 14,
              paddingHorizontal: 8,
              paddingVertical: 5,
              alignItems: "center",
              justifyContent: "center",
              gap: 3,
              backgroundColor: selected ? "#EEF4FF" : "transparent",
            }}
          >
            <Ionicons
              name={(selected ? item.activeIcon : item.icon) as any}
              size={21}
              color={selected ? C.blue : C.muted}
            />
            <Text style={{ color: selected ? C.blue : C.muted, fontSize: 10, fontWeight: "700" }}>
              {item.label}
            </Text>
          </Pressable>
        );
      })}
    </View>
  );
}

export function MobileScreenHeader({
  title,
  subtitle,
  right,
}: {
  title: string;
  subtitle?: string;
  right?: ReactNode;
}) {
  return (
    <View
      style={{
        backgroundColor: C.navy,
        paddingHorizontal: 20,
        paddingTop: 16,
        paddingBottom: 18,
        borderBottomLeftRadius: 24,
        borderBottomRightRadius: 24,
      }}
    >
      <View style={{ flexDirection: "row", alignItems: "center", gap: 12 }}>
        <View
          style={{
            width: 40,
            height: 40,
            borderRadius: 13,
            backgroundColor: C.blue,
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <Ionicons name="car-sport" size={22} color="#FFFFFF" />
        </View>
        <View style={{ flex: 1 }}>
          <Text style={{ color: "#FFFFFF", fontSize: 19, fontWeight: "800" }}>{title}</Text>
          {subtitle ? (
            <Text style={{ color: "#AFC4E3", fontSize: 11, marginTop: 2 }} numberOfLines={1}>
              {subtitle}
            </Text>
          ) : null}
        </View>
        {right}
      </View>
    </View>
  );
}
