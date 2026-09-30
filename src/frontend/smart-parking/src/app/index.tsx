import "../../assets/Styles/global.css"; // Import Tailwind CSS styles | NativeWindCss

import Footer from "@/components/Footer";
import Header from "@/components/Header";
import { ScrollView, Text, View, Pressable } from "react-native";
import { Link } from "expo-router";

export default function Index() {
  return (
    <ScrollView className="flex-1 items-center justify-center bg-slate-50 px-6">
      <Text className="mb-2 text-3xl font-bold text-slate-900">Bem-vindo</Text>
      <Text className="mb-10 text-center text-sm text-slate-500">
        Gerencie suas vagas de estacionamento de forma simples e rápida
      </Text>

      <Link href="/login" asChild>
        <Pressable className="mb-3 w-full items-center rounded-xl bg-blue-600 py-3 active:bg-blue-700">
          <Text className="text-base font-semibold text-white">Entrar</Text>
        </Pressable>
      </Link>

      <Link href="/cadastro" asChild>
        <Pressable className="w-full items-center rounded-xl border-2 border-blue-600 py-3 active:bg-blue-50">
          <Text className="text-base font-semibold text-blue-600">Criar conta</Text>
        </Pressable>
      </Link>
    </ScrollView>
  );
}
