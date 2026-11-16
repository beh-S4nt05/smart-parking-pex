import { Pressable, Text, View } from "react-native";

export type ChipOption<T extends string> = { value: T; label: string };

export default function OptionChips<T extends string>({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: T;
  onChange: (value: T) => void;
  options: ChipOption<T>[];
}) {
  return (
    <View style={{ marginBottom: 17, gap: 9 }}>
      <Text style={{ fontSize: 14, fontWeight: "700", color: "#24344F" }}>{label}</Text>
      <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8 }}>
        {options.map((option) => {
          const selected = value === option.value;
          return (
            <Pressable
              key={option.value}
              onPress={() => onChange(option.value)}
              accessibilityRole="radio"
              accessibilityLabel={option.label}
              accessibilityState={{ selected, checked: selected }}
              style={{
                minHeight: 44,
                paddingHorizontal: 15,
                paddingVertical: 10,
                justifyContent: "center",
                borderRadius: 13,
                backgroundColor: selected ? "#EAF1FF" : "#F6F8FB",
                borderWidth: selected ? 1.5 : 1,
                borderColor: selected ? "#2563EB" : "#E0E6EF",
              }}
            >
              <Text style={{ color: selected ? "#1D4ED8" : "#53647B", fontWeight: selected ? "800" : "600", fontSize: 13 }}>
                {option.label}
              </Text>
            </Pressable>
          );
        })}
      </View>
    </View>
  );
}
