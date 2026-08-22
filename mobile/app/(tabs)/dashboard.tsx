import { Ionicons } from "@expo/vector-icons";
import { router, useFocusEffect } from "expo-router";
import { useCallback, useState } from "react";
import { StyleSheet, Text, TouchableOpacity, View } from "react-native";

import { DASHBOARD } from "@/constants/testIds";
import { Character, CharacterApi, WorldApi, WorldClock } from "@/src/api";
import { Card } from "@/src/components/Card";
import { Portrait, XpBar } from "@/src/components/CharacterBits";
import { EmptyState } from "@/src/components/StateViews";
import { Screen } from "@/src/components/Screen";
import { useAuth } from "@/src/context/AuthContext";
import { colors, radius, spacing, typography } from "@/src/theme/theme";

export default function DashboardScreen() {
  const { user, signOut, refresh } = useAuth();
  const [characters, setCharacters] = useState<Character[]>([]);
  const [clock, setClock] = useState<WorldClock | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    const [chars, wc] = await Promise.allSettled([
      CharacterApi.list(),
      WorldApi.clock(),
    ]);
    if (chars.status === "fulfilled") setCharacters(chars.value);
    if (wc.status === "fulfilled") setClock(wc.value);
    refresh();
  }, [refresh]);

  useFocusEffect(
    useCallback(() => {
      load();
    }, [load]),
  );

  const onRefresh = async () => {
    setRefreshing(true);
    await load();
    setRefreshing(false);
  };

  const hero = characters[0];
  const calendar = clock?.calendar;
  const phase = clock?.time_of_day?.phase;

  return (
    <Screen scroll refreshing={refreshing} onRefresh={onRefresh} testID={DASHBOARD.screen}>
      <View style={styles.topRow}>
        <View style={styles.flex}>
          <Text style={styles.hi}>Welcome back,</Text>
          <Text style={styles.name} numberOfLines={1}>
            {user?.username ?? "Traveler"}
          </Text>
        </View>
        <TouchableOpacity
          testID={DASHBOARD.logoutButton}
          style={styles.logout}
          onPress={signOut}
          hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
        >
          <Ionicons name="log-out-outline" size={22} color={colors.textSecondary} />
        </TouchableOpacity>
      </View>

      {calendar ? (
        <View style={styles.clockPill} testID={DASHBOARD.worldClock}>
          <Ionicons name="time-outline" size={15} color={colors.gold} />
          <Text style={styles.clockText}>
            {calendar.compact ?? calendar.formatted}
            {phase ? `  ·  ${phase[0].toUpperCase()}${phase.slice(1)}` : ""}
          </Text>
        </View>
      ) : null}

      <Card accent="gold" style={styles.walletCard}>
        <View>
          <Text style={styles.walletLabel}>Coin Purse</Text>
          <Text style={styles.walletValue}>{(user?.currency ?? 0).toLocaleString()} g</Text>
        </View>
        <View style={styles.coin}>
          <Ionicons name="cash-outline" size={26} color={colors.gold} />
        </View>
      </Card>

      <Text style={styles.sectionTitle}>Active Hero</Text>
      {hero ? (
        <TouchableOpacity
          testID={DASHBOARD.activeCharacterCard}
          activeOpacity={0.85}
          onPress={() =>
            router.push({ pathname: "/(tabs)/characters/[id]", params: { id: hero.id } })
          }
        >
          <Card>
            <View style={styles.heroRow}>
              <Portrait uri={hero.portrait_url} name={hero.name} size={64} />
              <View style={styles.heroInfo}>
                <Text style={styles.heroName} numberOfLines={1}>
                  {hero.name}
                </Text>
                <Text style={styles.heroMeta} numberOfLines={1}>
                  {hero.race} · {hero.character_class}
                </Text>
                <Text style={styles.heroNation}>{hero.nation}</Text>
              </View>
              <Ionicons name="chevron-forward" size={20} color={colors.textMuted} />
            </View>
            <XpBar level={hero.level} xp={hero.xp} xpToNext={hero.xp_to_next_level} />
          </Card>
        </TouchableOpacity>
      ) : (
        <Card>
          <EmptyState
            icon="add-circle-outline"
            title="No heroes yet"
            subtitle="Forge your first character to step into the realm."
            actionLabel="Create a hero"
            actionTestID={DASHBOARD.createCharacterLink}
            onAction={() => router.push("/(tabs)/characters/new")}
          />
        </Card>
      )}

      <Text style={styles.sectionTitle}>Explore</Text>
      <View style={styles.quickRow}>
        <QuickTile
          icon="people"
          label="Your Heroes"
          hint={`${characters.length} in your roster`}
          color={colors.violet}
          onPress={() => router.push("/(tabs)/characters")}
          testID={DASHBOARD.charactersLink}
        />
        <QuickTile
          icon="map"
          label="The World"
          hint="Roam the continents"
          color={colors.gold}
          onPress={() => router.push("/(tabs)/world")}
          testID={DASHBOARD.worldLink}
        />
      </View>
    </Screen>
  );
}

const QuickTile = ({
  icon,
  label,
  hint,
  color,
  onPress,
  testID,
}: {
  icon: keyof typeof Ionicons.glyphMap;
  label: string;
  hint: string;
  color: string;
  onPress: () => void;
  testID: string;
}) => (
  <TouchableOpacity style={styles.tile} activeOpacity={0.85} onPress={onPress} testID={testID}>
    <View style={[styles.tileIcon, { borderColor: color }]}>
      <Ionicons name={icon} size={22} color={color} />
    </View>
    <Text style={styles.tileLabel}>{label}</Text>
    <Text style={styles.tileHint}>{hint}</Text>
  </TouchableOpacity>
);

const styles = StyleSheet.create({
  flex: { flex: 1 },
  topRow: { flexDirection: "row", alignItems: "center", marginBottom: spacing.md },
  hi: { ...typography.small, color: colors.textSecondary },
  name: { ...typography.h1, color: colors.textPrimary },
  logout: {
    width: 42,
    height: 42,
    borderRadius: 21,
    borderWidth: 1,
    borderColor: colors.border,
    alignItems: "center",
    justifyContent: "center",
  },
  clockPill: {
    flexDirection: "row",
    alignItems: "center",
    alignSelf: "flex-start",
    gap: 6,
    paddingHorizontal: spacing.md,
    paddingVertical: 6,
    borderRadius: radius.pill,
    borderWidth: 1,
    borderColor: colors.goldBorder,
    backgroundColor: colors.goldDim,
    marginBottom: spacing.lg,
  },
  clockText: { ...typography.small, color: colors.goldSoft, fontWeight: "600" },
  walletCard: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  walletLabel: { ...typography.tiny, color: colors.textMuted, textTransform: "uppercase" },
  walletValue: { ...typography.display, color: colors.gold, marginTop: 2 },
  coin: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: colors.goldDim,
    alignItems: "center",
    justifyContent: "center",
  },
  sectionTitle: {
    ...typography.h3,
    color: colors.textPrimary,
    marginTop: spacing.xl,
    marginBottom: spacing.md,
  },
  heroRow: { flexDirection: "row", alignItems: "center" },
  heroInfo: { flex: 1, marginLeft: spacing.md },
  heroName: { ...typography.h2, color: colors.textPrimary },
  heroMeta: { ...typography.small, color: colors.textSecondary, marginTop: 2 },
  heroNation: { ...typography.tiny, color: colors.gold, marginTop: 4, textTransform: "uppercase" },
  quickRow: { flexDirection: "row", gap: spacing.md },
  tile: {
    flex: 1,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.lg,
    padding: spacing.md,
  },
  tileIcon: {
    width: 44,
    height: 44,
    borderRadius: 22,
    borderWidth: 1,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: spacing.sm,
  },
  tileLabel: { ...typography.bodyStrong, color: colors.textPrimary },
  tileHint: { ...typography.small, color: colors.textMuted, marginTop: 2 },
});
