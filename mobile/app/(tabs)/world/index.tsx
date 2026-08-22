import { Ionicons } from "@expo/vector-icons";
import { Image } from "expo-image";
import { router, useFocusEffect } from "expo-router";
import { useCallback, useState } from "react";
import { FlatList, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { WORLD } from "@/constants/testIds";
import { Nation, WorldApi } from "@/src/api";
import { resolveImage } from "@/src/api/client";
import { Header } from "@/src/components/Header";
import { ErrorView, Loading } from "@/src/components/StateViews";
import { colors, radius, spacing, typography } from "@/src/theme/theme";

export default function WorldScreen() {
  const [nations, setNations] = useState<Nation[]>([]);
  const [status, setStatus] = useState<"loading" | "error" | "ready">("loading");

  const load = useCallback(async () => {
    setStatus("loading");
    try {
      const data = await WorldApi.nations();
      setNations(data);
      setStatus("ready");
    } catch {
      setStatus("error");
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      if (nations.length === 0) load();
    }, [load, nations.length]),
  );

  return (
    <SafeAreaView style={styles.safe} edges={["top"]} testID={WORLD.screen}>
      <Header title="Continents of Delarom" subtitle="Choose a realm" />

      {status === "loading" ? (
        <Loading label="Unfurling the map…" />
      ) : status === "error" ? (
        <ErrorView message="Could not load the realms." onRetry={load} />
      ) : (
        <FlatList
          data={nations}
          keyExtractor={(n) => n.slug}
          contentContainerStyle={styles.list}
          showsVerticalScrollIndicator={false}
          renderItem={({ item }) => {
            const img = resolveImage(item.image_url);
            return (
              <TouchableOpacity
                testID={`${WORLD.nationCard}-${item.slug}`}
                activeOpacity={0.9}
                style={styles.card}
                onPress={() =>
                  router.push({
                    pathname: "/(tabs)/world/nation",
                    params: { slug: item.slug, name: item.name },
                  })
                }
              >
                {img ? (
                  <Image source={{ uri: img }} style={styles.banner} contentFit="cover" transition={200} />
                ) : (
                  <View style={[styles.banner, styles.bannerFallback]}>
                    <Ionicons name="map-outline" size={30} color={colors.gold} />
                  </View>
                )}
                <View style={styles.overlay} />
                <View style={styles.cardBody}>
                  <Text style={styles.nationName}>{item.name}</Text>
                  <View style={styles.enterRow}>
                    <Text style={styles.enterText}>Enter realm</Text>
                    <Ionicons name="arrow-forward" size={16} color={colors.goldSoft} />
                  </View>
                </View>
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
    height: 150,
    borderRadius: radius.lg,
    overflow: "hidden",
    borderWidth: 1,
    borderColor: colors.border,
    justifyContent: "flex-end",
  },
  banner: { ...StyleSheet.absoluteFillObject, width: "100%", height: "100%" },
  bannerFallback: {
    backgroundColor: colors.surfaceAlt,
    alignItems: "center",
    justifyContent: "center",
  },
  overlay: { ...StyleSheet.absoluteFillObject, backgroundColor: "rgba(8,8,12,0.45)" },
  cardBody: { padding: spacing.md },
  nationName: { ...typography.h1, color: colors.white },
  enterRow: { flexDirection: "row", alignItems: "center", gap: 6, marginTop: 4 },
  enterText: { ...typography.small, color: colors.goldSoft, fontWeight: "700" },
});
