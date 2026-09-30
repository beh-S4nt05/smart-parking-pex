import { forwardRef, useState } from "react";
import { Pressable, Text, TextInput, TextInputProps, View } from "react-native";

interface FormFieldProps extends TextInputProps {
  label: string;
  error?: string;
  /** Campo de senha com botão mostrar/ocultar */
  password?: boolean;
  optional?: boolean;
}

const FormField = forwardRef<TextInput, FormFieldProps>(function FormField(
  { label, error, password, optional, onFocus, onBlur, ...inputProps },
  ref,
) {
  const [visible, setVisible] = useState(false);
  const [focused, setFocused] = useState(false);

  const borderColor = error
    ? "border-red-400"
    : focused
      ? "border-blue-500"
      : "border-slate-200";

  return (
    <View className="mb-4">
      <Text className="mb-1.5 text-sm font-semibold text-slate-700">
        {label}
        {optional ? <Text className="font-normal text-slate-400"> (opcional)</Text> : null}
      </Text>

      <View className={`flex-row items-center rounded-xl border-2 bg-white px-3 ${borderColor}`}>
        <TextInput
          ref={ref}
          accessibilityLabel={label}
          placeholderTextColor="#94a3b8"
          secureTextEntry={password && !visible}
          className="flex-1 py-3 text-base text-slate-900 outline-none"
          onFocus={(e) => {
            setFocused(true);
            onFocus?.(e);
          }}
          onBlur={(e) => {
            setFocused(false);
            onBlur?.(e);
          }}
          {...inputProps}
        />
        {password ? (
          <Pressable
            onPress={() => setVisible((v) => !v)}
            hitSlop={8}
            accessibilityRole="button"
            accessibilityLabel={visible ? "Ocultar senha" : "Mostrar senha"}
          >
            <Text className="pl-2 text-sm font-semibold text-blue-600">
              {visible ? "Ocultar" : "Mostrar"}
            </Text>
          </Pressable>
        ) : null}
      </View>

      {error ? (
        <Text accessibilityLiveRegion="polite" className="mt-1 text-xs font-medium text-red-600">
          {error}
        </Text>
      ) : null}
    </View>
  );
});

export default FormField;