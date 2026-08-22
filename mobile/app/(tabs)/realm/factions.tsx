import { Ionicons } from "@expo/vector-icons";
import { router, useFocusEffect } from "expo-router";
import { useCallback, useState } from "react";
import { FlatList, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { FACTIONS } from "@/constants/testIds";
import { Faction, FactionApi, FactionMember } from "@/src/api";
import { Header } from "@/src/components/Header";
import { Pill } from "@/src/components/Pill";
import { EmptyState, ErrorView, Loading } from "@/src/components/StateViews";
import { colors, radius, spacing, typography } from "@/src/theme/theme";

export default function FactionsScreen() {
  const [factions, setFactions] = useState<Faction[]>([]);
  const [memberships, setMemberships] = useState<FactionMember[]>([]);
  const [status, setStatus] = useState<"loading" | "error" | "ready">("loading");

  const load = useCallback(async () => {
    setStatus("loading");
    try {
      const [list, mine] = await Promise.all([FactionApi.list(), FactionApi.myMembership()]);
      setFactions(list);
      setMemberships(mine);
      setStatus("ready");
    } catch {
      setStatus("error");
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      load();
    }, [load]),
  );

  const mySlugs = new Set(memberships.map((m) => m.faction_slug));

  return (
    <SafeAreaView style={styles.safe} edges={["top"]} testID={FACTIONS.screen}>
      <Header title="Factions" subtitle="Powers of the realm" showBack />
      {status === "loading" ? (
        <Loading label="Rallying the banners…" />
      ) : status === "error" ? (
        <ErrorView message="Could not load factions." onRetry={load} />
      ) : factions.length === 0 ? (
        <EmptyState icon="flag-outline" title="No factions yet" />
      ) : (
        <FlatList
          data={factions}
          keyExtractor={(f) => f.id}
          contentContainerStyle={styles.list}
          showsVerticalScrollIndicator={false}
          renderItem={({ item }) => {
            const color = item.color_hex || colors.gold;
            return (
              <TouchableOpacity
                testID={FACTIONS.card}
                activeOpacity={0.85}
                style={[styles.card, { borderColor: color + "66" }]}
                onPress={() =>
                  router.push({
                    pathname: "/(tabs)/realm/faction",
                    params: { slug: item.slug, name: item.name },
                  })
                }
              >
                <View style={[styles.sigil, { backgroundColor: color + "22", borderColor: color }]}>
                  <Ionicons name="shield-half" size={24} color={color} />
                </View>
                <View style={styles.info}>
                  <View style={styles.nameRow}>
                    <Text style={styles.name} numberOfLines={1}>
                      {item.name}
                    </Text>
                    {mySlugs.has(item.slug) ? (
                      <Pill label="Member" color={colors.green} icon="checkmark-circle" />
                    ) : null}
                  </View>
                  <Text style={[styles.motto, { color }]} numberOfLines={1}>
                    &ldquo;{item.motto}&rdquo;
                  </Text>
                  <View style={styles.metaRow}>
                    <Ionicons name="people-outline" size={13} color={colors.textMuted} />
                    <Text style={styles.meta}>{item.member_count} members</Text>
                    <Text style={styles.meta}>· {item.nation_home}</Text>
                  </View>
                </View>
                <Ionicons name="chevron-forward" size={20} color={colors.textMuted} />
              </TouchableOpacity>
            );
          }}
        />
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.bg },
  list: { padding: spacing.md, gap: spacing.md },
  card: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderRadius: radius.lg,
    padding: spacing.md,
  },
  sigil: {
    width: 50,
    height: 50,
    borderRadius: 25,
    borderWidth: 1,
    alignItems: "center",
    justifyContent: "center",
  },
  info: { flex: 1, marginHorizontal: spacing.md },
  nameRow: { flexDirection: "row", alignItems: "center", gap: spacing.sm },
  name: { ...typography.h3, color: colors.textPrimary, flexShrink: 1 },
  motto: { ...typography.small, fontStyle: "italic", marginTop: 2 },
  metaRow: { flexDirection: "row", alignItems: "center", gap: 4, marginTop: 6 },
  meta: { ...typography.tiny, color: colors.textMuted },
});
