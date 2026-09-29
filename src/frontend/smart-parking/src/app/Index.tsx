import "../../assets/Styles/global.css"; // Import Tailwind CSS styles | NativeWindCss

import Footer from "@/components/Footer";
import Header from "@/components/Header";
import { ScrollView, Text, View } from "react-native";

export default function Index() {
  return (
    <ScrollView className="flex-1 bg-white h-full">
      <Header />
      <View className="flex-1 items-center justify-center py-20">
        <Text className="text-lg font-bold text-slate-900">
          Welcome to Smart Parking
        </Text>
      </View>
      <Footer />
    </ScrollView>
  );
}
