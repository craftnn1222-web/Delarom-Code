import { Ionicons } from "@expo/vector-icons";
import React from "react";
import { ActivityIndicator, StyleSheet, Text, View } from "react-native";

import { Button } from "./Button";
import { colors, spacing, typography } from "@/src/theme/theme";

export const Loading = ({ label }: { label?: string }) => (
  <View style={styles.center}>
    <ActivityIndicator size="large" color={colors.gold} />
    {label ? <Text style={styles.muted}>{label}</Text> : null}
  </View>
);

interface EmptyStateProps {
  icon?: keyof typeof Ionicons.glyphMap;
  title: string;
  subtitle?: string;
  actionLabel?: string;
  onAction?: () => void;
  actionTestID?: string;
}

export const EmptyState = ({
  icon = "sparkles-outline",
  title,
  subtitle,
  actionLabel,
  onAction,
  actionTestID,
}: EmptyStateProps) => (
  <View style={styles.center}>
    <View style={styles.iconCircle}>
      <Ionicons name={icon} size={30} color={colors.gold} />
    </View>
    <Text style={styles.title}>{title}</Text>
    {subtitle ? <Text style={styles.subtitle}>{subtitle}</Text> : null}
    {actionLabel && onAction ? (
      <Button
        title={actionLabel}
        onPress={onAction}
        style={styles.action}
        testID={actionTestID}
      />
    ) : null}
  </View>
);

interface ErrorViewProps {
  message: string;
  onRetry?: () => void;
}

export const ErrorView = ({ message, onRetry }: ErrorViewProps) => (
  <View style={styles.center}>
    <View style={[styles.iconCircle, { borderColor: colors.rose }]}>
      <Ionicons name="alert-circle-outline" size={30} color={colors.rose} />
    </View>
    <Text style={styles.title}>Something went awry</Text>
    <Text style={styles.subtitle}>{message}</Text>
    {onRetry ? <Button title="Try again" variant="ghost" onPress={onRetry} style={styles.action} /> : null}
  </View>
);

const styles = StyleSheet.create({
  center: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    padding: spacing.xl,
  },
  iconCircle: {
    width: 64,
    height: 64,
    borderRadius: 32,
    borderWidth: 1,
    borderColor: colors.goldBorder,
    backgroundColor: colors.goldDim,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: spacing.md,
  },
  title: { ...typography.h2, color: colors.textPrimary, textAlign: "center" },
  subtitle: {
    ...typography.body,
    color: colors.textSecondary,
    textAlign: "center",
    marginTop: spacing.xs,
  },
  muted: { ...typography.small, color: colors.textMuted, marginTop: spacing.md },
  action: { marginTop: spacing.lg, alignSelf: "stretch" },
});
