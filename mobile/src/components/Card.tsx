import React from "react";
import { StyleSheet, View, ViewStyle } from "react-native";

import { colors, radius, spacing } from "@/src/theme/theme";

interface CardProps {
  children: React.ReactNode;
  style?: ViewStyle;
  accent?: "gold" | "violet" | "rose" | "none";
  testID?: string;
}

export const Card = ({ children, style, accent = "none", testID }: CardProps) => (
  <View
    testID={testID}
    style={[
      styles.card,
      accent === "gold" && { borderColor: colors.goldBorder },
      accent === "violet" && { borderColor: colors.violetBorder },
      accent === "rose" && { borderColor: colors.rose },
      style,
    ]}
  >
    {children}
  </View>
);

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.lg,
    padding: spacing.md,
  },
});
