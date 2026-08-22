import { Ionicons } from "@expo/vector-icons";
import { Image } from "expo-image";
import React from "react";
import { StyleSheet, Text, View } from "react-native";

import { Character } from "@/src/api";
import { resolveImage } from "@/src/api/client";
import { colors, radius, spacing, typography } from "@/src/theme/theme";

const initialsOf = (name: string) =>
  name
    .split(" ")
    .map((w) => w[0])
    .filter(Boolean)
    .slice(0, 2)
    .join("")
    .toUpperCase();

export const Portrait = ({
  uri,
  name,
  size = 56,
}: {
  uri?: string | null;
  name: string;
  size?: number;
}) => {
  const resolved = resolveImage(uri);
  if (resolved) {
    return (
      <Image
        source={{ uri: resolved }}
        style={[styles.portrait, { width: size, height: size, borderRadius: size / 2 }]}
        contentFit="cover"
        transition={150}
      />
    );
  }
  return (
    <View
      style={[
        styles.portraitFallback,
        { width: size, height: size, borderRadius: size / 2 },
      ]}
    >
      <Text style={[styles.initials, { fontSize: size * 0.36 }]}>{initialsOf(name)}</Text>
    </View>
  );
};

const STATS: { key: keyof Character; label: string; icon: keyof typeof Ionicons.glyphMap }[] = [
  { key: "strength", label: "STR", icon: "barbell-outline" },
  { key: "magic", label: "MAG", icon: "flame-outline" },
  { key: "agility", label: "AGI", icon: "flash-outline" },
  { key: "endurance", label: "END", icon: "shield-outline" },
  { key: "charisma", label: "CHA", icon: "chatbubbles-outline" },
  { key: "luck", label: "LCK", icon: "sparkles-outline" },
];

export const StatGrid = ({ character }: { character: Character }) => (
  <View style={styles.statGrid}>
    {STATS.map((s) => (
      <View key={s.key} style={styles.statChip}>
        <Ionicons name={s.icon} size={16} color={colors.gold} />
        <Text style={styles.statValue}>{character[s.key] as number}</Text>
        <Text style={styles.statLabel}>{s.label}</Text>
      </View>
    ))}
  </View>
);

export const XpBar = ({
  level,
  xp,
  xpToNext,
}: {
  level: number;
  xp: number;
  xpToNext: number;
}) => {
  const pct = xpToNext > 0 ? Math.min(1, xp / xpToNext) : 0;
  return (
    <View style={styles.xpWrap}>
      <View style={styles.xpHeader}>
        <Text style={styles.levelText}>Level {level}</Text>
        <Text style={styles.xpText}>
          {xp} / {xpToNext} XP
        </Text>
      </View>
      <View style={styles.xpTrack}>
        <View style={[styles.xpFill, { width: `${pct * 100}%` }]} />
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  portrait: { borderWidth: 1, borderColor: colors.goldBorder, backgroundColor: colors.surfaceAlt },
  portraitFallback: {
    borderWidth: 1,
    borderColor: colors.goldBorder,
    backgroundColor: colors.goldDim,
    alignItems: "center",
    justifyContent: "center",
  },
  initials: { color: colors.gold, fontWeight: "800" },
  statGrid: { flexDirection: "row", flexWrap: "wrap", gap: spacing.sm },
  statChip: {
    flexBasis: "31%",
    flexGrow: 1,
    alignItems: "center",
    paddingVertical: spacing.sm,
    backgroundColor: colors.surfaceAlt,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
  },
  statValue: { ...typography.h3, color: colors.textPrimary, marginTop: 2 },
  statLabel: { ...typography.tiny, color: colors.textMuted },
  xpWrap: { marginTop: spacing.sm },
  xpHeader: { flexDirection: "row", justifyContent: "space-between", marginBottom: 6 },
  levelText: { ...typography.bodyStrong, color: colors.gold },
  xpText: { ...typography.small, color: colors.textSecondary },
  xpTrack: {
    height: 8,
    borderRadius: 4,
    backgroundColor: colors.surfaceAlt,
    overflow: "hidden",
  },
  xpFill: { height: "100%", backgroundColor: colors.gold, borderRadius: 4 },
});
