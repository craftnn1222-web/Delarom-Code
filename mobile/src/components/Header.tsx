import { Ionicons } from "@expo/vector-icons";
import { router } from "expo-router";
import React from "react";
import { StyleSheet, Text, TouchableOpacity, View } from "react-native";

import { colors, spacing, typography } from "@/src/theme/theme";

interface HeaderProps {
  title: string;
  subtitle?: string;
  showBack?: boolean;
  onBack?: () => void;
  right?: React.ReactNode;
}

export const Header = ({ title, subtitle, showBack, onBack, right }: HeaderProps) => (
  <View style={styles.wrap}>
    <View style={styles.side}>
      {showBack ? (
        <TouchableOpacity
          testID="header-back-button"
          hitSlop={{ top: 12, bottom: 12, left: 12, right: 12 }}
          onPress={() => (onBack ? onBack() : router.back())}
          style={styles.backBtn}
        >
          <Ionicons name="chevron-back" size={24} color={colors.gold} />
        </TouchableOpacity>
      ) : null}
    </View>

    <View style={styles.center}>
      <Text style={styles.title} numberOfLines={1}>
        {title}
      </Text>
      {subtitle ? (
        <Text style={styles.subtitle} numberOfLines={1}>
          {subtitle}
        </Text>
      ) : null}
    </View>

    <View style={[styles.side, styles.right]}>{right}</View>
  </View>
);

const styles = StyleSheet.create({
  wrap: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.border,
    backgroundColor: colors.bg,
  },
  side: { width: 48, justifyContent: "center" },
  right: { alignItems: "flex-end" },
  backBtn: { width: 40, height: 40, justifyContent: "center", alignItems: "flex-start" },
  center: { flex: 1, alignItems: "center" },
  title: { ...typography.h2, color: colors.textPrimary, textAlign: "center" },
  subtitle: {
    ...typography.tiny,
    color: colors.gold,
    textTransform: "uppercase",
    marginTop: 2,
  },
});
