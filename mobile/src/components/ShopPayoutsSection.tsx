import { Ionicons } from "@expo/vector-icons";
import { useCallback, useEffect, useState } from "react";
import { ActivityIndicator, StyleSheet, Text, TouchableOpacity, View } from "react-native";

import { PAYOUTS } from "@/constants/testIds";
import { ShopApi, ShopLedger } from "@/src/api";
import { colors, radius, spacing, typography } from "@/src/theme/theme";

type State = "loading" | "error" | "ready";
const fmt = (n: number) => (n || 0).toLocaleString();
const netColor = (n: number) => (n > 0 ? colors.green : n < 0 ? colors.rose : colors.textSecondary);
const fmtDate = (iso: string) => {
  try {
    return new Date(iso).toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
  } catch {
    return iso;
  }
};

function Stat({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <View style={styles.stat}>
      <Text style={styles.statLabel}>{label}</Text>
      <Text style={[styles.statValue, { color }]}>{value}</Text>
    </View>
  );
}

export function ShopPayoutsSection({ shopId }: { shopId: string }) {
  const [data, setData] = useState<ShopLedger | null>(null);
  const [state, setState] = useState<State>("loading");

  const load = useCallback(async () => {
    setState("loading");
    try {
      setData(await ShopApi.ledger(shopId));
      setState("ready");
    } catch {
      setState("error");
    }
  }, [shopId]);

  useEffect(() => {
    load();
  }, [load]);

  const totals = data?.totals;
  const entries = data?.entries ?? [];

  return (
    <View testID={PAYOUTS.section}>
      <Text style={styles.sectionLabel}>Owner Payouts</Text>
      <Text style={styles.hint}>Gold earned each ~6h cycle, minus wages and restocking.</Text>

      {state === "loading" ? (
        <View style={styles.center} testID={PAYOUTS.loading}>
          <ActivityIndicator color={colors.gold} />
        </View>
      ) : state === "error" ? (
        <TouchableOpacity style={styles.center} onPress={load}>
          <Ionicons name="refresh" size={18} color={colors.gold} />
          <Text style={styles.retry}>Couldn&apos;t load payouts. Tap to retry.</Text>
        </TouchableOpacity>
      ) : (
        <>
          <View style={styles.statGrid} testID={PAYOUTS.totals}>
            <Stat label="NPC sales" value={`${fmt(totals!.npc_sales)}g`} color={colors.goldSoft} />
            <Stat label="Player sales" value={`${fmt(totals!.player_sales)}g`} color={colors.goldSoft} />
            <Stat label="Wages" value={`${fmt(totals!.wages)}g`} color={colors.rose} />
            <Stat label="Restock" value={`${fmt(totals!.restock)}g`} color={colors.rose} />
            <Stat label="Net (all-time)" value={`${fmt(totals!.net)}g`} color={netColor(totals!.net)} />
          </View>

          <Text style={styles.subLabel}>Recent cycles</Text>
          {entries.length === 0 ? (
            <Text style={styles.hint} testID={PAYOUTS.empty}>
              No pay cycles yet. Earnings appear after the next economy cycle.
            </Text>
          ) : (
            entries.map((e) => (
              <View key={e.id} style={styles.entry} testID={PAYOUTS.entry(e.id)}>
                <View style={styles.entryHead}>
                  <Text style={styles.entryDate}>{fmtDate(e.at)}</Text>
                  <Text style={[styles.entryNet, { color: netColor(e.net) }]}>
                    {e.net >= 0 ? "+" : ""}
                    {fmt(e.net)}g net
                  </Text>
                </View>
                <Text style={styles.entryMeta}>
                  NPC {fmt(e.npc_sales_gold)}g · Players {fmt(e.player_sales_gold)}g ({e.player_sales_count}) · Wages -
                  {fmt(e.wages_paid)}g · Restock -{fmt(e.restock_cost)}g
                </Text>
              </View>
            ))
          )}
        </>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  sectionLabel: {
    ...typography.tiny,
    color: colors.gold,
    textTransform: "uppercase",
    letterSpacing: 1,
    marginTop: spacing.xl,
    marginBottom: spacing.xs,
  },
  hint: { ...typography.small, color: colors.textMuted, marginBottom: spacing.md },
  center: { alignItems: "center", justifyContent: "center", paddingVertical: spacing.lg, gap: spacing.xs },
  retry: { ...typography.small, color: colors.gold },
  statGrid: { flexDirection: "row", flexWrap: "wrap", gap: spacing.sm },
  stat: {
    flexGrow: 1,
    minWidth: "30%",
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.md,
    padding: spacing.sm,
  },
  statLabel: { ...typography.tiny, color: colors.textSecondary, textTransform: "uppercase" },
  statValue: { ...typography.h3, marginTop: 2 },
  subLabel: { ...typography.bodyStrong, color: colors.textSecondary, marginTop: spacing.lg, marginBottom: spacing.sm },
  entry: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.md,
    padding: spacing.md,
    marginBottom: spacing.sm,
  },
  entryHead: { flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  entryDate: { ...typography.small, color: colors.textSecondary },
  entryNet: { ...typography.bodyStrong },
  entryMeta: { ...typography.small, color: colors.textMuted, marginTop: spacing.xs },
});
