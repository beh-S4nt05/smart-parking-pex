import { useEffect, useRef, useState } from "react";
import { Text, View, TouchableOpacity, Pressable, ScrollView } from "react-native";
import Header from "@/components/Header";
import Hero from "@/components/Hero";
import Footer from "@/components/Footer";
import Reserve from "@/components/Reserve";
import ShoppingList from "@/components/ShoppingList";
import StatusPanel from "@/components/StatusPanel";

export default function Index() {
  return (
    <ScrollView className="flex-1 bg-white h-full">
      <Header/>
      <View className="flex-1 items-center justify-center py-20">
        <Text className="text-lg font-bold text-slate-900">Welcome to Smart Parking</Text>
      </View>
      <Footer/>
    </ScrollView>
  );
}