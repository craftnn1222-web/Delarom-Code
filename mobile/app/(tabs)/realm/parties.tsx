import { Ionicons } from "@expo/vector-icons";
import { router, useFocusEffect } from "expo-router";
import { useCallback, useState } from "react";
import { FlatList, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { PARTIES } from "@/constants/testIds";
import { Party, PartyApi } from "@/src/api";
import { Header } from "@/src/components/Header";
import { partyStatusColor, Pill } from "@/src/components/Pill";
import { EmptyState, ErrorView, Loading } from "@/src/components/StateViews";
import { colors, radius, spacing, typography } from "@/src/theme/theme";

type Tab = "open" | "mine";

export default function PartiesScreen() {
  const [tab, setTab] = useState<Tab>("open");
  const [parties, setParties] = useState<Party[]>([]);
  const [status, setStatus] = useState<"loading" | "error" | "ready">("loading");

  const load = useCallback(async (which: Tab) => {
    setStatus("loading");
    try {
      setParties(which === "open" ? await PartyApi.list("recruiting") : await PartyApi.mine());
      setStatus("ready");
    } catch {
      setStatus("error");
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      load(tab);
    }, [load, tab]),
  );

  const switchTab = (next: Tab) => {
    setTab(next);
    load(next);
  };

  return (
    <SafeAreaView style={styles.safe} edges={["top"]} testID={PARTIES.screen}>
      <Header
        title="Parties"
        subtitle="Shared adventures"
        showBack
        right={
          <TouchableOpacity
            testID={PARTIES.newButton}
            onPress={() => router.push("/(tabs)/realm/party-new")}
            hitSlop={{ top: 12, bottom: 12, left: 12, right: 12 }}
          >
            <Ionicons name="add-circle" size={28} color={colors.gold} />
          </TouchableOpacity>
        }
      />

      <View style={styles.segment}>
        <SegBtn label="Recruiting" active={tab === "open"} onPress={() => switchTab("open")} />
        <SegBtn label="My Parties" active={tab === "mine"} onPress={() => switchTab("mine")} />
      </View>

      {status === "loading" ? (
        <Loading label="Gathering the fellowship…" />
      ) : status === "error" ? (
        <ErrorView message="Could not load parties." onRetry={() => load(tab)} />
      ) : parties.length === 0 ? (
        <EmptyState
          icon="people-circle-outline"
          title={tab === "open" ? "No parties recruiting" : "You're in no parties"}
          subtitle="Start one and invite the realm."
          actionLabel="Create a party"
          actionTestID={PARTIES.newButton}
          onAction={() => router.push("/(tabs)/realm/party-new")}
        />
      ) : (
        <FlatList
          data={parties}
          keyExtractor={(p) => p.id}
          contentContainerStyle={styles.list}
          showsVerticalScrollIndicator={false}
          renderItem={({ item }) => (
            <TouchableOpacity
              testID={PARTIES.card}
              activeOpacity={0.85}
              style={styles.card}
              onPress={() => router.push({ pathname: "/(tabs)/realm/party", params: { id: item.id } })}
            >
              <View style={styles.cardHead}>
                <Text style={styles.name} numberOfLines={1}>
                  {item.name}
                </Text>
                <Pill label={item.status} color={partyStatusColor(item.status)} />
              </View>
              <View style={styles.metaRow}>
                <Ionicons name="location-outline" size={13} color={colors.textMuted} />
                <Text style={styles.meta} numberOfLines={1}>
                  {item.location}
                </Text>
              </View>
              <Text style={styles.scene} numberOfLines={2}>
                {item.scene_description}
              </Text>
              <View style={styles.footRow}>
                <Ionicons name="people-outline" size={14} color={colors.textSecondary} />
                <Text style={styles.foot}>
                  {item.members.length}/{item.max_members} members
                </Text>
              </View>
            </TouchableOpacity>
          )}
        />
      )}
    </SafeAreaView>
  );
}

const SegBtn = ({
  label,
  active,
  onPress,
}: {
  label: string;
  active: boolean;
  onPress: () => void;
}) => (
  <TouchableOpacity style={[styles.segBtn, active && styles.segBtnActive]} onPress={onPress} activeOpacity={0.85}>
    <Text style={[styles.segText, active && styles.segTextActive]}>{label}</Text>
  </TouchableOpacity>
);

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.bg },
  segment: {
    flexDirection: "row",
    margin: spacing.md,
    padding: 4,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.pill,
  },
  segBtn: { flex: 1, paddingVertical: 8, borderRadius: radius.pill, alignItems: "center" },
  segBtnActive: { backgroundColor: colors.violetDim },
  segText: { ...typography.small, color: colors.textSecondary, fontWeight: "600" },
  segTextActive: { color: colors.violetSoft },
  list: { paddingHorizontal: spacing.md, paddingBottom: spacing.xxl, gap: spacing.md },
  card: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.lg,
    padding: spacing.md,
  },
  cardHead: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: spacing.sm },
  name: { ...typography.h3, color: colors.textPrimary, flex: 1 },
  metaRow: { flexDirection: "row", alignItems: "center", gap: 4, marginTop: 6 },
  meta: { ...typography.small, color: colors.textMuted, flex: 1 },
  scene: { ...typography.small, color: colors.textSecondary, marginTop: spacing.sm },
  footRow: { flexDirection: "row", alignItems: "center", gap: 6, marginTop: spacing.md },
  foot: { ...typography.small, color: colors.textSecondary },
});
