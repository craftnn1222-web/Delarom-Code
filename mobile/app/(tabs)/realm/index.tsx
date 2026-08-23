import { Ionicons } from "@expo/vector-icons";
import { router } from "expo-router";
import { StyleSheet, Text, TouchableOpacity, View } from "react-native";

import { REALM } from "@/constants/testIds";
import { Header } from "@/src/components/Header";
import { Screen } from "@/src/components/Screen";
import { colors, radius, spacing, typography } from "@/src/theme/theme";

const ENTRIES = [
  {
    key: "marketplace",
    label: "Marketplace",
    hint: "Buy gear from player shops",
    icon: "storefront" as const,
    color: colors.gold,
    href: "/(tabs)/realm/marketplace" as const,
    testID: REALM.marketplaceLink,
  },
  {
    key: "my-shop",
    label: "My Shop",
    hint: "Open a shop & sell your gear",
    icon: "cube" as const,
    color: colors.green,
    href: "/(tabs)/realm/my-shop" as const,
    testID: REALM.myShopLink,
  },
  {
    key: "factions",
    label: "Factions",
    hint: "Pledge your blade to a cause",
    icon: "flag" as const,
    color: colors.rose,
    href: "/(tabs)/realm/factions" as const,
    testID: REALM.factionsLink,
  },
  {
    key: "parties",
    label: "Parties",
    hint: "Adventure together in shared scenes",
    icon: "people-circle" as const,
    color: colors.violet,
    href: "/(tabs)/realm/parties" as const,
    testID: REALM.partiesLink,
  },
];

export default function RealmHubScreen() {
  return (
    <Screen scroll={false} padded={false} testID={REALM.screen}>
      <Header title="The Realm" subtitle="Trade · Guilds · Fellowship" />
      <View style={styles.list}>
        {ENTRIES.map((e) => (
          <TouchableOpacity
            key={e.key}
            testID={e.testID}
            activeOpacity={0.85}
            style={styles.card}
            onPress={() => router.push(e.href)}
          >
            <View style={[styles.icon, { borderColor: e.color, backgroundColor: e.color + "1F" }]}>
              <Ionicons name={e.icon} size={26} color={e.color} />
            </View>
            <View style={styles.info}>
              <Text style={styles.label}>{e.label}</Text>
              <Text style={styles.hint}>{e.hint}</Text>
            </View>
            <Ionicons name="chevron-forward" size={20} color={colors.textMuted} />
          </TouchableOpacity>
        ))}
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
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
    width: 54,
    height: 54,
    borderRadius: 27,
    borderWidth: 1,
    alignItems: "center",
    justifyContent: "center",
  },
  info: { flex: 1, marginHorizontal: spacing.md },
  label: { ...typography.h3, color: colors.textPrimary },
  hint: { ...typography.small, color: colors.textSecondary, marginTop: 2 },
});
