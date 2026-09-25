import { View, Text, Pressable } from 'react-native';

export default function Footer() {
  return (
    <View className="bg-slate-900 text-slate-300">
      <View className="mx-auto max-w-6xl px-4 py-14 sm:px-6 lg:px-8">
        <View className="grid gap-10 sm:grid-cols-2 lg:grid-cols-4">
          <View>
            <View className="flex items-center gap-2.5">
              <View className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-blue-500 to-blue-700">
              </View>
              <Text className="font-bold text-white">Smart Parking</Text>
            </View>
            <Text className="mt-4 text-sm text-slate-400">
              Monitoramento inteligente de vagas em estacionamentos de shoppings, em tempo real e por setor.
            </Text>
          </View>

          <View>
            <Text className="text-sm font-bold uppercase tracking-wide text-white">Integração</Text>
            <View className="mt-4 space-y-2.5 text-sm">
              <Text className="hover:text-white">Painel Administrativo</Text>
              <Text className="hover:text-white">Documentação Técnica</Text>
            </View>
          </View>

          <View>
            <Text className="text-sm font-bold uppercase tracking-wide text-white">Contato</Text>
            <View className="mt-4 space-y-2.5 text-sm">
              <Text className="flex items-center gap-2">📞 (92) 98123-0258</Text>
              <Text className="flex items-center gap-2">✉️ behsolutionsandautomations@gmail.com</Text>
              <Text className="flex items-center gap-2">📍 Manaus, AM</Text>
            </View>
          </View>
        </View>

        <View className="mt-10 flex flex-col items-center justify-between gap-4 border-t border-slate-800 pt-6 text-xs text-slate-500 sm:flex-row">
          <Text>© {new Date().getFullYear()} Smart Parking Shoppings. Todos os direitos reservados.</Text>
          <Text>Feito com 💙 para facilitar sua ida ao shopping.</Text>
        </View>
      </View>
    </View>
  );
}
