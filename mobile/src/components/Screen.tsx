import React from "react";
import {
  ScrollView,
  StyleSheet,
  View,
  ViewStyle,
  RefreshControl,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { colors, spacing } from "@/src/theme/theme";

interface ScreenProps {
  children: React.ReactNode;
  scroll?: boolean;
  padded?: boolean;
  style?: ViewStyle;
  contentStyle?: ViewStyle;
  edges?: ("top" | "bottom" | "left" | "right")[];
  refreshing?: boolean;
  onRefresh?: () => void;
  testID?: string;
}

export const Screen = ({
  children,
  scroll = false,
  padded = true,
  style,
  contentStyle,
  edges = ["top"],
  refreshing,
  onRefresh,
  testID,
}: ScreenProps) => {
  const inner = padded ? { padding: spacing.md } : undefined;

  if (scroll) {
    return (
      <SafeAreaView style={[styles.safe, style]} edges={edges} testID={testID}>
        <ScrollView
          contentContainerStyle={[styles.scrollContent, inner, contentStyle]}
          keyboardShouldPersistTaps="handled"
          showsVerticalScrollIndicator={false}
          refreshControl={
            onRefresh ? (
              <RefreshControl
                refreshing={!!refreshing}
                onRefresh={onRefresh}
                tintColor={colors.gold}
              />
            ) : undefined
          }
        >
          {children}
        </ScrollView>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={[styles.safe, style]} edges={edges} testID={testID}>
      <View style={[styles.flex, inner, contentStyle]}>{children}</View>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.bg },
  flex: { flex: 1 },
  scrollContent: { flexGrow: 1, paddingBottom: spacing.xxl },
});
