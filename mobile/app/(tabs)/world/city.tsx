import { Ionicons } from "@expo/vector-icons";
import { router, useLocalSearchParams } from "expo-router";
import { useCallback, useEffect, useState } from "react";
import { FlatList, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { WORLD } from "@/constants/testIds";
import { LocationItem, WorldApi } from "@/src/api";
import { Header } from "@/src/components/Header";
import { EmptyState, ErrorView, Loading } from "@/src/components/StateViews";
import { colors, radius, spacing, typography } from "@/src/theme/theme";

export default function CityScreen() {
  const { nation, city, name } = useLocalSearchParams<{
    nation: string;
    city: string;
    name: string;
  }>();
  const [locations, setLocations] = useState<LocationItem[]>([]);
  const [status, setStatus] = useState<"loading" | "error" | "ready">("loading");

  const load = useCallback(async () => {
    if (!nation || !city) return;
    setStatus("loading");
    try {
      const data = await WorldApi.locationsByCity(nation, city);
      setLocations(data);
      setStatus("ready");
    } catch {
      setStatus("error");
    }
  }, [nation, city]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <SafeAreaView style={styles.safe} edges={["top"]}>
      <Header title={name ?? "City"} subtitle="Places to roleplay" showBack />

      {status === "loading" ? (
        <Loading label="Wandering the streets…" />
      ) : status === "error" ? (
        <ErrorView message="Could not load locations." onRetry={load} />
      ) : locations.length === 0 ? (
        <EmptyState icon="location-outline" title="No open locations here" subtitle="Try another city." />
      ) : (
        <FlatList
          data={locations}
          keyExtractor={(l) => l.id}
          contentContainerStyle={styles.list}
          showsVerticalScrollIndicator={false}
          renderItem={({ item }) => {
            const canRp = item.is_rp_enabled;
            return (
              <TouchableOpacity
                testID={`${WORLD.locationCard}-${item.slug}`}
                activeOpacity={canRp ? 0.85 : 1}
                disabled={!canRp}
                style={[styles.card, !canRp && styles.cardDisabled]}
                onPress={() =>
                  router.push({
                    pathname: "/rp",
                    params: { nation, location: item.slug, name: item.name },
                  })
                }
              >
                <View style={styles.iconWrap}>
                  <Ionicons name="location" size={20} color={colors.violetSoft} />
                </View>
                <View style={styles.info}>
                  <Text style={styles.name} numberOfLines={1}>
                    {item.name}
                  </Text>
                  {item.location_type ? (
                    <Text style={styles.type}>{item.location_type}</Text>
                  ) : null}
                  <Text style={styles.desc} numberOfLines={2}>
                    {item.description}
                  </Text>
                  {item.controlling_faction_name ? (
                    <Text style={styles.held}>Held by {item.controlling_faction_name}</Text>
                  ) : null}
                </View>
                {canRp ? (
                  <Ionicons name="chatbubbles" size={20} color={colors.gold} />
                ) : (
                  <Text style={styles.locked}>Closed</Text>
                )}
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
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.lg,
    padding: spacing.md,
    alignItems: "center",
  },
  cardDisabled: { opacity: 0.5 },
  iconWrap: {
    width: 42,
    height: 42,
    borderRadius: 21,
    backgroundColor: colors.violetDim,
    borderWidth: 1,
    borderColor: colors.violetBorder,
    alignItems: "center",
    justifyContent: "center",
  },
  info: { flex: 1, marginHorizontal: spacing.md },
  name: { ...typography.h3, color: colors.textPrimary },
  type: { ...typography.tiny, color: colors.violetSoft, marginTop: 2, textTransform: "uppercase" },
  desc: { ...typography.small, color: colors.textSecondary, marginTop: 4 },
  held: { ...typography.tiny, color: colors.gold, marginTop: 6 },
  locked: { ...typography.tiny, color: colors.textMuted },
});
