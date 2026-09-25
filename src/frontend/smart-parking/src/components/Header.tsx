import { View, ScrollView, Pressable, Text, } from 'react-native';
import { Link, LinkProps } from 'expo-router'

export default function Header() {
  return (
    <ScrollView className="sticky top-0 z-50 border-b border-slate-200 bg-white/90 backdrop-blur">
      <View className="mx-auto flex-row max-w items-stretch justify-between px-4 py-3 sm:px-6 lg:px-8 gap-[clamp(1rem,5vw,2rem)]">
        <View className="flex-row items-center gap-2.5">
          <View className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-blue-500 to-blue-700 shadow-md shadow-blue-200">
            <Text className="text-lg font-bold text-white">SP</Text>
          </View>
          <View className="leading-tight">
            <Text className="text-base font-bold text-slate-900">Smart Parking</Text>
            <Text className="text-[11px] font-medium text-slate-500">Shoppings</Text>
          </View>
        </View>

        <View className="items-center gap-1 md:flex-row">
          <Link href="/" className="rounded-lg px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100 hover:text-slate-900">
            Home
          </Link>
          <Link href="/#" className="rounded-lg px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100 hover:text-slate-900">
            Reservar Vaga
          </Link>
          <Link href="/#" className="rounded-lg px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100 hover:text-slate-900">
            Status do Estacionamento
          </Link>
          <Link href="/#" className="rounded-lg px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100 hover:text-slate-900">
            Lista de Shoppings
          </Link>
        </View>

        <View className="flex-row items-center gap-2">
          <Pressable className="hidden rounded-full px-4 py-2 text-sm font-semibold text-blue-700 hover:bg-blue-50 sm:block">
            <Text>Suporte</Text>
          </Pressable>
          <Pressable className="rounded-full bg-blue-600 px-5 py-2 text-sm font-semibold text-white shadow-sm shadow-blue-200 transition hover:bg-blue-700">
            <Text>Entrar</Text>
          </Pressable>
        </View>
      </View>

      <View className="flex items-center gap-1 overflow-x-auto border-t border-slate-100 px-4 py-2 md:hidden">
      </View>
    </ScrollView>
  );
}
