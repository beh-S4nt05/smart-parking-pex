/**
 * Tela 404 própria — substitui a "Unmatched Route" padrão do Expo Router.
 *
 * A tela padrão exibia a URL crua em um link de 20px de altura: em 360px
 * isso estourava a viewport (documento com 367px) e oferecia alvos de toque
 * de 20/27px. Aqui o erro é explicado em linguagem do produto, com ações
 * de 44px, contraste AA e texto que quebra em qualquer largura.
 */
import { useRouter } from "expo-router";
import { ScrollView, Text, View } from "react-native";
import { Botao, Logo } from "../components/ui";

export default function NaoEncontrado() {
  const router = useRouter();

  return (
    <View className="flex-1 bg-slate-50">
      <ScrollView contentContainerStyle={{ flexGrow: 1, justifyContent: "center" }}>
        <View className="mx-auto w-full max-w-lg items-center gap-4 px-6 py-14">
          <Logo size={56} />
          <Text
            accessibilityRole="header"
            className="text-center text-3xl font-extrabold text-slate-900"
          >
            Página não encontrada
          </Text>
          <Text className="text-center text-base leading-6 text-slate-600">
            O endereço que você abriu não existe ou foi movido. Volte ao início
            para consultar os shoppings e as vagas disponíveis em tempo real.
          </Text>
          <View className="mt-2 w-full gap-3">
            <Botao
              label="Voltar ao Início"
              onPress={() => router.replace("/")}
              className="w-full"
            />
            <Botao
              label="Explorar shoppings"
              variant="contorno"
              onPress={() => router.replace("/explorar")}
              className="w-full"
            />
          </View>
          <Text className="mt-4 text-center text-xs text-slate-600">
            Se o problema persistir, fale com o HelpDesk do estacionamento.
          </Text>
        </View>
      </ScrollView>
    </View>
  );
}
