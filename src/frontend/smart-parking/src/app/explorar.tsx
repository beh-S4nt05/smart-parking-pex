// src/app/explorar.tsx
import { View, Text, Pressable, FlatList } from "react-native";
import { Link, useRouter } from "expo-router";

const PURPLE = "#6D28D9";

type Shopping = {
  id: string;
  nome: string;
  vagasLivres: number;
  vagasTotais: number;
};

const SHOPPINGS: Shopping[] = [
  { id: "1", nome: "Amazonas Shopping", vagasLivres: 32, vagasTotais: 60 },
  { id: "2", nome: "Manauara Shopping", vagasLivres: 18, vagasTotais: 50 },
  { id: "3", nome: "Ponta Negra Shopping", vagasLivres: 41, vagasTotais: 55 },
  { id: "4", nome: "Sumaúma Park Shopping", vagasLivres: 24, vagasTotais: 45 },
];

export default function Explorar() {
  const router = useRouter();

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

        <Link href="/" className="text-sm font-medium text-violet-700">
          ← Voltar ao início
        </Link>
      </View>

      {/* Título */}
      <View className="px-6 pb-4 md:px-12">
        <Text className="text-xl font-bold text-slate-900">
          Vagas disponíveis agora
        </Text>
        <Text className="mt-1 text-sm text-slate-500">
          Visualização pública — para reservar uma vaga, crie sua conta.
        </Text>
      </View>

      {/* Lista de shoppings */}
      <FlatList
        data={SHOPPINGS}
        keyExtractor={(item) => item.id}
        contentContainerStyle={{ paddingHorizontal: 24, paddingBottom: 24, gap: 12 }}
        renderItem={({ item }) => <ShoppingCard shopping={item} />}
      />

      {/* Rodapé fixo com CTA */}
      <View className="border-t border-slate-200 bg-white px-6 py-4">
        <Pressable
          onPress={() => router.push("/cadastro")}
          className="items-center rounded-xl py-3.5 active:opacity-90"
          style={{ backgroundColor: PURPLE }}
        >
          <Text className="text-sm font-semibold text-white">
            Criar conta para reservar
          </Text>
        </Pressable>
      </View>
    </View>
  );
}

function ShoppingCard({ shopping }: { shopping: Shopping }) {
  const ocupacao = Math.round(
    ((shopping.vagasTotais - shopping.vagasLivres) / shopping.vagasTotais) * 100,
  );

  return (
    <View className="rounded-2xl bg-white p-4 shadow-sm">
      <View className="flex-row items-center justify-between">
        <Text className="text-base font-semibold text-slate-900">
          {shopping.nome}
        </Text>
        <View className="rounded-full bg-emerald-100 px-3 py-1">
          <Text className="text-xs font-semibold text-emerald-700">
            {shopping.vagasLivres} livres
          </Text>
        </View>
      </View>

      <View className="mt-3 h-2 overflow-hidden rounded-full bg-slate-100">
        <View
          className="h-2 rounded-full bg-violet-600"
          style={{ width: `${ocupacao}%` }}
        />
      </View>

      <Text className="mt-2 text-xs text-slate-400">
        {shopping.vagasTotais - shopping.vagasLivres} de {shopping.vagasTotais} vagas ocupadas
      </Text>
    </View>
  );
}