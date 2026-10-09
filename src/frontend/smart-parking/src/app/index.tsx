// src/app/index.tsx
import { View, Text, Pressable, useWindowDimensions } from "react-native";
import { Link, useRouter } from "expo-router";

const PURPLE = "#6D28D9";

export default function Index() {
  const router = useRouter();
  const { width } = useWindowDimensions();
  const isWide = width >= 900;

  return (
    <View className="flex-1 bg-slate-50">
      {/* Topo */}
      <View className="flex-row items-center justify-between px-6 py-5 md:px-12">
        <View className="flex-row items-center gap-2">
          <View className="h-9 w-9 items-center justify-center rounded-lg bg-slate-900">
            <Text className="text-white">🚗</Text>
          </View>
          <View>
            <Text className="text-sm font-bold text-slate-900">Smart Parking</Text>
            <Text className="text-xs text-slate-400">Shoppings</Text>
          </View>
        </View>

        <View className="flex-row items-center gap-4">
          <Pressable onPress={() => router.push("/explorar")}>
            <Text className="text-sm font-medium text-slate-600">
              Ver vagas sem cadastro
            </Text>
          </Pressable>
          <Link href="/login" className="text-sm font-semibold text-violet-700">
            Entrar
          </Link>
        </View>
      </View>

      {/* Corpo principal */}
      <View
        className={`flex-1 items-center gap-10 px-6 py-10 md:px-12 ${
          isWide ? "flex-row justify-center" : "flex-col justify-center"
        }`}
      >
        {/* Texto + CTAs */}
        <View className={isWide ? "flex-1" : "w-full"}>
          <View className="mb-5 self-start rounded-full bg-violet-100 px-3 py-1.5">
            <Text className="text-xs font-medium text-violet-700">
              • Monitoramento em tempo real
            </Text>
          </View>

          <Text className="mb-3 text-3xl font-bold leading-tight text-slate-900 md:text-4xl">
            Encontre e reserve sua vaga em segundos.
          </Text>
          <Text className="mb-8 text-sm leading-relaxed text-slate-500 md:text-base">
            Acompanhe vagas disponíveis por setor nos shoppings de Manaus,
            reserve com Pix ou cartão e evite perder tempo procurando
            estacionamento.
          </Text>

          <View className="mb-8 flex-row flex-wrap gap-3">
            <Pressable
              onPress={() => router.push("/cadastro")}
              className="items-center rounded-xl px-6 py-3.5 active:opacity-90"
              style={{ backgroundColor: PURPLE }}
            >
              <Text className="text-sm font-semibold text-white">
                Criar conta grátis
              </Text>
            </Pressable>

            <Pressable
              onPress={() => router.push("/explorar")}
              className="items-center rounded-xl border-2 border-slate-200 px-6 py-3.5 active:bg-slate-100"
            >
              <Text className="text-sm font-semibold text-slate-700">
                Ver vagas sem cadastro
              </Text>
            </Pressable>
          </View>

          {/* Stats */}
          <View className="flex-row gap-3">
            <StatCard value="115" label="Vagas" />
            <StatCard value="4" label="Shoppings" />
            <StatCard value="1h 40" label="Tempo médio" />
          </View>
        </View>

        {/* Painel visual — só em telas largas */}
        {isWide && (
          <View
            className="flex-1 justify-between rounded-3xl p-8"
            style={{ backgroundColor: PURPLE }}
          >
            <Text className="text-xs font-medium text-violet-100">
              Shoppings parceiros
            </Text>
            <View className="gap-3">
              <PartnerRow nome="Amazonas Shopping" vagas="32 vagas livres" />
              <PartnerRow nome="Manauara Shopping" vagas="18 vagas livres" />
              <PartnerRow nome="Ponta Negra Shopping" vagas="41 vagas livres" />
              <PartnerRow nome="Sumaúma Park Shopping" vagas="24 vagas livres" />
            </View>
            <Text className="text-xs text-violet-100">
              Atualizado em tempo real
            </Text>
          </View>
        )}
      </View>

      {/* Rodapé */}
      <Text className="pb-5 text-center text-xs text-slate-400">
        © 2026 Smart Parking Shoppings · (92) 98123-0258 ·
        behsolutionsandautomations@gmail.com · Manaus, AM
      </Text>
    </View>
  );
}

function StatCard({ value, label }: { value: string; label: string }) {
  return (
    <View className="items-center rounded-xl bg-white px-4 py-3 shadow-sm">
      <Text className="text-lg font-bold text-slate-900">{value}</Text>
      <Text className="text-xs text-slate-500">{label}</Text>
    </View>
  );
}

function PartnerRow({ nome, vagas }: { nome: string; vagas: string }) {
  return (
    <View className="flex-row items-center justify-between rounded-xl bg-white/15 px-4 py-3">
      <Text className="text-sm font-medium text-white">{nome}</Text>
      <Text className="text-xs text-violet-100">{vagas}</Text>
    </View>
  );
}