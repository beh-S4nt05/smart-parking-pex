import { Link } from "expo-router";
import { Pressable, Text, View } from "react-native";
import { Logo } from "./ui";

/** Rodapé escuro — fiel ao template Home (WEB/MOBILE) do Figma */
export default function Footer() {
  return (
    <View className="bg-slate-900 px-4 py-10 sm:px-6">
      <View className="mx-auto w-full max-w-7xl">
        <View className="flex-row flex-wrap justify-between gap-8">
          <View className="min-w-[220px] flex-1">
            <View className="flex-row items-center gap-2.5">
              <Logo size={34} />
              <Text className="text-base font-bold text-white">Smart Parking</Text>
            </View>
            <Text className="mt-3 max-w-xs text-sm leading-5 text-slate-400">
              Monitoramento inteligente de vagas em estacionamentos de shoppings,
              em tempo real e por andar.
            </Text>
          </View>

          <View>
            <Text className="text-[11px] font-bold uppercase tracking-wider text-slate-300">
              Integração
            </Text>
            <View className="mt-3 gap-2">
              <Link href="/dashboard" asChild>
                <Pressable>
                  <Text className="text-sm text-slate-400 active:text-white">
                    Painel Administrativo
                  </Text>
                </Pressable>
              </Link>
              <Text className="text-sm text-slate-400">
                Documentação Técnica (/docs)
              </Text>
            </View>
          </View>

          <View>
            <Text className="text-[11px] font-bold uppercase tracking-wider text-slate-300">
              Contato
            </Text>
            <View className="mt-3 gap-2">
              <Text className="text-sm text-slate-400">
                behsolutionsandautomations@gmail.com
              </Text>
              <Text className="text-sm text-slate-400">Manaus, AM</Text>
            </View>
          </View>
        </View>

        <View className="mt-8 border-t border-slate-800 pt-5">
          <Text className="text-xs text-slate-500">
            © 2026 Smart Parking Shoppings. Todos os direitos reservados.
          </Text>
        </View>
      </View>
    </View>
  );
}
