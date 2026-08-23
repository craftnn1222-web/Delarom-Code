import { Ionicons } from "@expo/vector-icons";
import { router, useFocusEffect } from "expo-router";
import { useCallback, useState } from "react";
import { Modal, Pressable, StyleSheet, Text, TouchableOpacity, View } from "react-native";

import { DASHBOARD } from "@/constants/testIds";
import { ContinueState, MeApi, WorldApi, WorldClock } from "@/src/api";
import { Card } from "@/src/components/Card";
import { Portrait, XpBar } from "@/src/components/CharacterBits";
import { EmptyState } from "@/src/components/StateViews";
import { Screen } from "@/src/components/Screen";
import { useActiveCharacter } from "@/src/hooks/useActiveCharacter";
import { useAuth } from "@/src/context/AuthContext";
import { colors, radius, spacing, typography } from "@/src/theme/theme";

export default function DashboardScreen() {
  const { user, signOut, refresh } = useAuth();
  const { character: hero, characters, reload: reloadChars, setActive } = useActiveCharacter();
  const [clock, setClock] = useState<WorldClock | null>(null);
  const [cont, setCont] = useState<ContinueState | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [switcherOpen, setSwitcherOpen] = useState(false);
  const [switchingId, setSwitchingId] = useState<string | null>(null);

  const load = useCallback(async () => {
    const [, wc, ct] = await Promise.allSettled([
      reloadChars(),
      WorldApi.clock(),
      MeApi.continueState(),
    ]);
    if (wc.status === "fulfilled") setClock(wc.value);
    if (ct.status === "fulfilled") setCont(ct.value);
    refresh();
  }, [refresh, reloadChars]);

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

  const onPickHero = async (id: string) => {
    if (id === hero?.id) {
      setSwitcherOpen(false);
      return;
    }
    setSwitchingId(id);
    try {
      await setActive(id);
    } finally {
      setSwitchingId(null);
      setSwitcherOpen(false);
    }
  };

  const calendar = clock?.calendar;
  const phase = clock?.time_of_day?.phase;
  const scene = cont?.last_scene ?? null;
  const party = cont?.active_party ?? null;

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

      <View style={styles.sectionHeader}>
        <Text style={styles.sectionHeaderTitle}>Active Hero</Text>
        {characters.length > 1 ? (
          <TouchableOpacity
            testID={DASHBOARD.switchHeroButton}
            style={styles.switchBtn}
            onPress={() => setSwitcherOpen(true)}
            hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
          >
            <Ionicons name="swap-horizontal" size={16} color={colors.violet} />
            <Text style={styles.switchBtnText}>Switch</Text>
          </TouchableOpacity>
        ) : null}
      </View>
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

      {scene || party ? (
        <>
          <Text style={styles.sectionTitle}>Continue</Text>
          <Card testID={DASHBOARD.continueCard}>
            {scene ? (
              <TouchableOpacity
                testID={DASHBOARD.continueRp}
                style={styles.continueRow}
                activeOpacity={0.85}
                onPress={() =>
                  router.push({
                    pathname: "/rp",
                    params: {
                      nation: scene.nation,
                      location: scene.location,
                      name: scene.location_name,
                    },
                  })
                }
              >
                <View style={[styles.continueIcon, { backgroundColor: colors.violetDim }]}>
                  <Ionicons name="chatbubbles-outline" size={20} color={colors.violet} />
                </View>
                <View style={styles.flex}>
                  <Text style={styles.continueLabel}>Last Scene</Text>
                  <Text style={styles.continueTitle} numberOfLines={1}>
                    {scene.location_name}
                  </Text>
                  <Text style={styles.continueMeta} numberOfLines={1}>
                    {scene.city ? `${scene.city} · ` : ""}as {scene.character_name}
                  </Text>
                </View>
                <Ionicons name="play-circle" size={26} color={colors.violet} />
              </TouchableOpacity>
            ) : null}
            {scene && party ? <View style={styles.continueDivider} /> : null}
            {party ? (
              <TouchableOpacity
                testID={DASHBOARD.continueParty}
                style={styles.continueRow}
                activeOpacity={0.85}
                onPress={() =>
                  router.push({ pathname: "/(tabs)/realm/party", params: { id: party.id } })
                }
              >
                <View style={[styles.continueIcon, { backgroundColor: "rgba(212,175,110,0.15)" }]}>
                  <Ionicons name="people" size={20} color={colors.gold} />
                </View>
                <View style={styles.flex}>
                  <Text style={styles.continueLabel}>Active Party</Text>
                  <Text style={styles.continueTitle} numberOfLines={1}>
                    {party.name}
                  </Text>
                  <Text style={[styles.continueMeta, styles.capitalize]} numberOfLines={1}>
                    {party.status} · {party.member_count} member{party.member_count === 1 ? "" : "s"}
                  </Text>
                </View>
                <Ionicons name="chevron-forward" size={20} color={colors.textMuted} />
              </TouchableOpacity>
            ) : null}
          </Card>
        </>
      ) : null}

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

      <Modal
        visible={switcherOpen}
        transparent
        animationType="fade"
        onRequestClose={() => setSwitcherOpen(false)}
      >
        <Pressable style={styles.modalBackdrop} onPress={() => setSwitcherOpen(false)}>
          <Pressable style={styles.sheet} testID={DASHBOARD.heroSwitcher}>
            <Text style={styles.sheetTitle}>Choose your hero</Text>
            <Text style={styles.sheetSub}>Switching changes who you play everywhere.</Text>
            {characters.map((c) => {
              const isActive = c.id === hero?.id;
              return (
                <TouchableOpacity
                  key={c.id}
                  testID={DASHBOARD.heroOption(c.id)}
                  style={[styles.heroOption, isActive && styles.heroOptionActive]}
                  activeOpacity={0.85}
                  disabled={switchingId === c.id}
                  onPress={() => onPickHero(c.id)}
                >
                  <Portrait uri={c.portrait_url} name={c.name} size={44} />
                  <View style={styles.heroOptionInfo}>
                    <Text style={styles.heroOptionName} numberOfLines={1}>
                      {c.name}
                    </Text>
                    <Text style={styles.heroOptionMeta} numberOfLines={1}>
                      {c.race} · {c.character_class}
                    </Text>
                  </View>
                  {isActive ? (
                    <Ionicons name="checkmark-circle" size={22} color={colors.violet} />
                  ) : null}
                </TouchableOpacity>
              );
            })}
          </Pressable>
        </Pressable>
      </Modal>
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
  sectionHeader: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginTop: spacing.xl,
    marginBottom: spacing.md,
  },
  sectionHeaderTitle: { ...typography.h3, color: colors.textPrimary },
  switchBtn: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    paddingHorizontal: spacing.md,
    paddingVertical: 6,
    borderRadius: radius.pill,
    borderWidth: 1,
    borderColor: colors.violetBorder,
    backgroundColor: colors.violetDim,
  },
  switchBtnText: { ...typography.small, color: colors.violetSoft, fontWeight: "700" },
  modalBackdrop: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.6)",
    justifyContent: "flex-end",
  },
  sheet: {
    backgroundColor: colors.surface,
    borderTopLeftRadius: radius.xl,
    borderTopRightRadius: radius.xl,
    padding: spacing.lg,
    paddingBottom: spacing.xl,
    borderWidth: 1,
    borderColor: colors.border,
    gap: spacing.sm,
  },
  sheetTitle: { ...typography.h2, color: colors.textPrimary },
  sheetSub: { ...typography.small, color: colors.textMuted, marginBottom: spacing.sm },
  heroOption: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.md,
    padding: spacing.md,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.bg,
  },
  heroOptionActive: { borderColor: colors.violet, backgroundColor: colors.violetDim },
  heroOptionInfo: { flex: 1 },
  heroOptionName: { ...typography.bodyStrong, color: colors.textPrimary },
  heroOptionMeta: { ...typography.small, color: colors.textSecondary, marginTop: 2 },
  continueRow: { flexDirection: "row", alignItems: "center", gap: spacing.md, paddingVertical: spacing.xs },
  continueIcon: {
    width: 40,
    height: 40,
    borderRadius: radius.md,
    alignItems: "center",
    justifyContent: "center",
  },
  continueLabel: {
    ...typography.small,
    color: colors.textMuted,
    textTransform: "uppercase",
    letterSpacing: 0.5,
  },
  continueTitle: { ...typography.bodyStrong, color: colors.textPrimary },
  continueMeta: { ...typography.small, color: colors.textSecondary, marginTop: 1 },
  continueDivider: { height: 1, backgroundColor: colors.border, marginVertical: spacing.sm },
  capitalize: { textTransform: "capitalize" },
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
