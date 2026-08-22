import { Ionicons } from "@expo/vector-icons";
import { router, useLocalSearchParams } from "expo-router";
import { useCallback, useEffect, useState } from "react";
import { FlatList, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { WORLD } from "@/constants/testIds";
import { City, WorldApi } from "@/src/api";
import { Header } from "@/src/components/Header";
import { EmptyState, ErrorView, Loading } from "@/src/components/StateViews";
import { colors, radius, spacing, typography } from "@/src/theme/theme";

export default function NationScreen() {
  const { slug, name } = useLocalSearchParams<{ slug: string; name: string }>();
  const [cities, setCities] = useState<City[]>([]);
  const [status, setStatus] = useState<"loading" | "error" | "ready">("loading");

  const load = useCallback(async () => {
    if (!slug) return;
    setStatus("loading");
    try {
      const data = await WorldApi.cities(slug);
      setCities(data);
      setStatus("ready");
    } catch {
      setStatus("error");
    }
  }, [slug]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <SafeAreaView style={styles.safe} edges={["top"]}>
      <Header title={name ?? "Realm"} subtitle="Cities & holds" showBack />

      {status === "loading" ? (
        <Loading label="Charting the roads…" />
      ) : status === "error" ? (
        <ErrorView message="Could not load cities." onRetry={load} />
      ) : cities.length === 0 ? (
        <EmptyState icon="business-outline" title="No cities here yet" />
      ) : (
        <FlatList
          data={cities}
          keyExtractor={(c) => c.id}
          contentContainerStyle={styles.list}
          showsVerticalScrollIndicator={false}
          renderItem={({ item }) => (
            <TouchableOpacity
              testID={`${WORLD.cityCard}-${item.slug}`}
              activeOpacity={0.85}
              style={styles.card}
              onPress={() =>
                router.push({
                  pathname: "/(tabs)/world/city",
                  params: { nation: slug, city: item.slug, name: item.name },
                })
              }
            >
              <View style={styles.iconWrap}>
                <Ionicons name="business" size={22} color={colors.gold} />
              </View>
              <View style={styles.info}>
                <Text style={styles.name} numberOfLines={1}>
                  {item.name}
                </Text>
                {item.region ? <Text style={styles.region}>{item.region}</Text> : null}
                <Text style={styles.desc} numberOfLines={2}>
                  {item.description}
                </Text>
                {item.faction ? (
                  <View style={styles.factionBadge}>
                    <Ionicons name="flag" size={11} color={colors.violetSoft} />
                    <Text style={styles.factionText}>{item.faction}</Text>
                  </View>
                ) : null}
              </View>
              <Ionicons name="chevron-forward" size={20} color={colors.textMuted} />
            </TouchableOpacity>
          )}
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
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.lg,
    padding: spacing.md,
    alignItems: "center",
  },
  iconWrap: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: colors.goldDim,
    borderWidth: 1,
    borderColor: colors.goldBorder,
    alignItems: "center",
    justifyContent: "center",
  },
  info: { flex: 1, marginHorizontal: spacing.md },
  name: { ...typography.h3, color: colors.textPrimary },
  region: { ...typography.tiny, color: colors.gold, marginTop: 2, textTransform: "uppercase" },
  desc: { ...typography.small, color: colors.textSecondary, marginTop: 4 },
  factionBadge: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    alignSelf: "flex-start",
    marginTop: spacing.sm,
    paddingHorizontal: spacing.sm,
    paddingVertical: 2,
    borderRadius: radius.sm,
    backgroundColor: colors.violetDim,
    borderWidth: 1,
    borderColor: colors.violetBorder,
  },
  factionText: { ...typography.tiny, color: colors.violetSoft },
});
