import { Ionicons } from "@expo/vector-icons";
import React from "react";
import {
  ActivityIndicator,
  StyleSheet,
  Text,
  TouchableOpacity,
  ViewStyle,
} from "react-native";

import { colors, radius, spacing, typography } from "@/src/theme/theme";

type Variant = "primary" | "secondary" | "ghost" | "danger";

interface ButtonProps {
  title: string;
  onPress: () => void;
  variant?: Variant;
  loading?: boolean;
  disabled?: boolean;
  icon?: keyof typeof Ionicons.glyphMap;
  style?: ViewStyle;
  testID?: string;
}

export const Button = ({
  title,
  onPress,
  variant = "primary",
  loading = false,
  disabled = false,
  icon,
  style,
  testID,
}: ButtonProps) => {
  const isDisabled = disabled || loading;
  const palette = VARIANTS[variant];

  return (
    <TouchableOpacity
      testID={testID}
      activeOpacity={0.85}
      disabled={isDisabled}
      onPress={onPress}
      style={[
        styles.base,
        { backgroundColor: palette.bg, borderColor: palette.border },
        isDisabled && styles.disabled,
        style,
      ]}
    >
      {loading ? (
        <ActivityIndicator color={palette.text} />
      ) : (
        <>
          {icon ? (
            <Ionicons name={icon} size={18} color={palette.text} style={styles.icon} />
          ) : null}
          <Text style={[styles.label, { color: palette.text }]}>{title}</Text>
        </>
      )}
    </TouchableOpacity>
  );
};

const VARIANTS: Record<Variant, { bg: string; border: string; text: string }> = {
  primary: { bg: colors.gold, border: colors.gold, text: "#1A1206" },
  secondary: { bg: colors.violetDim, border: colors.violetBorder, text: colors.violetSoft },
  ghost: { bg: "transparent", border: colors.borderStrong, text: colors.textPrimary },
  danger: { bg: colors.roseDim, border: colors.rose, text: colors.rose },
};

const styles = StyleSheet.create({
  base: {
    minHeight: 50,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    borderRadius: radius.md,
    borderWidth: 1,
    paddingHorizontal: spacing.lg,
  },
  disabled: { opacity: 0.5 },
  label: { ...typography.bodyStrong },
  icon: { marginRight: spacing.sm },
});
