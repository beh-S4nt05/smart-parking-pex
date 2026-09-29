import Header from "@/components/Header";
import { ScrollView, Text, View } from "react-native";

export default function Login() {
  return (
    <ScrollView className="flex-1 bg-white h-full">
      <Header />
      <View className="flex-1 items-center justify-center py-20">
        <Text className="text-lg font-bold text-slate-900">Login</Text>
      </View>
    </ScrollView>
  );
}
