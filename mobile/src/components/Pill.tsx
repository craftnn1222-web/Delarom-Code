import { Ionicons } from "@expo/vector-icons";
import React from "react";
import { StyleSheet, Text, View, ViewStyle } from "react-native";

import { colors, radius, spacing, typography } from "@/src/theme/theme";

interface PillProps {
  label: string;
  color?: string;
  icon?: keyof typeof Ionicons.glyphMap;
  style?: ViewStyle;
}

/** A small rounded status/reward chip used across quests, factions & parties. */
export const Pill = ({ label, color = colors.gold, icon, style }: PillProps) => (
  <View style={[styles.pill, { borderColor: color, backgroundColor: color + "22" }, style]}>
    {icon ? <Ionicons name={icon} size={12} color={color} style={styles.icon} /> : null}
    <Text style={[styles.text, { color }]}>{label}</Text>
  </View>
);

export const difficultyColor = (difficulty: string): string => {
  switch (difficulty?.toLowerCase()) {
    case "easy":
      return colors.green;
    case "hard":
      return "#F0883E";
    case "legendary":
      return colors.violet;
    default:
      return colors.gold;
  }
};

export const partyStatusColor = (status: string): string => {
  switch (status) {
    case "active":
      return colors.green;
    case "finished":
      return colors.textMuted;
    default:
      return colors.gold; // recruiting
  }
};

const styles = StyleSheet.create({
  pill: {
    flexDirection: "row",
    alignItems: "center",
    alignSelf: "flex-start",
    paddingHorizontal: spacing.sm,
    paddingVertical: 3,
    borderRadius: radius.pill,
    borderWidth: 1,
  },
  icon: { marginRight: 4 },
  text: { ...typography.tiny, textTransform: "uppercase" },
});
