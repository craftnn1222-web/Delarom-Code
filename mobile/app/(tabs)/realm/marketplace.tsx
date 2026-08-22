import { Ionicons } from "@expo/vector-icons";
import { router, useFocusEffect } from "expo-router";
import { useCallback, useState } from "react";
import { FlatList, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { MARKET } from "@/constants/testIds";
import { Shop, ShopApi } from "@/src/api";
import { Header } from "@/src/components/Header";
import { EmptyState, ErrorView, Loading } from "@/src/components/StateViews";
import { colors, radius, spacing, typography } from "@/src/theme/theme";

export default function MarketplaceScreen() {
  const [shops, setShops] = useState<Shop[]>([]);
  const [status, setStatus] = useState<"loading" | "error" | "ready">("loading");

  const load = useCallback(async () => {
    setStatus("loading");
    try {
      setShops(await ShopApi.list());
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

  return (
    <SafeAreaView style={styles.safe} edges={["top"]} testID={MARKET.screen}>
      <Header title="Marketplace" subtitle="Player-run shops" showBack />
      {status === "loading" ? (
        <Loading label="Opening the bazaar…" />
      ) : status === "error" ? (
        <ErrorView message="Could not load shops." onRetry={load} />
      ) : shops.length === 0 ? (
        <EmptyState icon="storefront-outline" title="No shops open" subtitle="Merchants are restocking." />
      ) : (
        <FlatList
          data={shops}
          keyExtractor={(s) => s.id}
          contentContainerStyle={styles.list}
          showsVerticalScrollIndicator={false}
          renderItem={({ item }) => (
            <TouchableOpacity
              testID={MARKET.shopCard}
              style={styles.card}
              activeOpacity={0.85}
              onPress={() =>
                router.push({
                  pathname: "/(tabs)/realm/shop",
                  params: { shopId: item.id, name: item.name },
                })
              }
            >
              <View style={styles.icon}>
                <Ionicons name="storefront" size={22} color={colors.gold} />
              </View>
              <View style={styles.info}>
                <Text style={styles.name} numberOfLines={1}>
                  {item.name}
                </Text>
                <Text style={styles.owner}>by {item.owner_username}</Text>
                <Text style={styles.desc} numberOfLines={2}>
                  {item.description}
                </Text>
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
    alignItems: "center",
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.lg,
    padding: spacing.md,
  },
  icon: {
    width: 46,
    height: 46,
    borderRadius: 23,
    backgroundColor: colors.goldDim,
    borderWidth: 1,
    borderColor: colors.goldBorder,
    alignItems: "center",
    justifyContent: "center",
  },
  info: { flex: 1, marginHorizontal: spacing.md },
  name: { ...typography.h3, color: colors.textPrimary },
  owner: { ...typography.tiny, color: colors.gold, marginTop: 2, textTransform: "uppercase" },
  desc: { ...typography.small, color: colors.textSecondary, marginTop: 4 },
});
