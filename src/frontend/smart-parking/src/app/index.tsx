import "../../assets/Styles/global.css"; // Import Tailwind CSS styles | NativeWindCss
import { useEffect, useRef, useState } from "react";
import { Text, View, TouchableOpacity, TouchableOpacityProps, } from "react-native";
import Header from "@/components/Header";
import Hero from "@/components/Hero";
import Footer from "@/components/Footer";
import Reserve from "@/components/Reserve";
import ShoppingList from "@/components/ShoppingList";
import StatusPanel from "@/components/StatusPanel";

export default function App() {
  return (
    <View className="flex-1 bg-white">
      <Header/>
      <View className="flex-1 items-center justify-center">
        <Text className="text-lg font-bold text-slate-900">Welcome to Smart Parking</Text>
      </View>
      <Footer/>
    </View>
  );
}