import { useLocalSearchParams } from "expo-router";
import { useCallback, useEffect, useState } from "react";
import {
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { FACTIONS } from "@/constants/testIds";
import {
  EconomyApi,
  FactionApi,
  FactionSpecialty,
  TradeContract,
  WorldApi,
} from "@/src/api";
import { Button } from "@/src/components/Button";
import { Header } from "@/src/components/Header";
import { PickerField, PickerOption } from "@/src/components/PickerField";
import { EmptyState, ErrorView, Loading } from "@/src/components/StateViews";
import { Pill } from "@/src/components/Pill";
import { useToast } from "@/src/components/Toast";
import { useAuth } from "@/src/context/AuthContext";
import { colors, radius, spacing, typography } from "@/src/theme/theme";

const NATION_SLUGS = ["aigraels", "dhor-kuldor", "selindori", "ammeonon"];
const prettify = (slug: string) =>
  slug.split("-").map((w) => w.charAt(0).toUpperCase() + w.slice(1)).join(" ");
const delivered = (c: TradeContract) =>
  Math.round((c.base_cost_snapshot || 0) * (1 + (c.tariff_pct || 0) / 100));

export default function FactionRoutesScreen() {
  const { slug, name } = useLocalSearchParams<{ slug: string; name: string }>();
  const toast = useToast();
  const { user } = useAuth();

  const [contracts, setContracts] = useState<TradeContract[]>([]);
  const [specialties, setSpecialties] = useState<FactionSpecialty[]>([]);
  const [cityOptions, setCityOptions] = useState<PickerOption[]>([]);
  const [cityNation, setCityNation] = useState<Record<string, string>>({});
  const [canManage, setCanManage] = useState(false);
  const [status, setStatus] = useState<"loading" | "error" | "ready">("loading");

  const [createOpen, setCreateOpen] = useState(false);
  const [good, setGood] = useState("");
  const [citySlug, setCitySlug] = useState("");
  const [tariff, setTariff] = useState("25");
  const [qty, setQty] = useState("50");
  const [creating, setCreating] = useState(false);

  const [breakTarget, setBreakTarget] = useState<TradeContract | null>(null);
  const [breakReason, setBreakReason] = useState("");
  const [breaking, setBreaking] = useState(false);

  const load = useCallback(async () => {
    if (!slug) return;
    setStatus("loading");
    try {
      const [cts, specs, mine] = await Promise.all([
        EconomyApi.factionContracts(slug),
        EconomyApi.factionSpecialties(slug).catch(() => ({ specialties: [] as FactionSpecialty[] })),
        FactionApi.myMembership().catch(() => []),
      ]);
      setContracts(cts);
      setSpecialties(specs.specialties ?? []);
      const isAdmin = user?.role === "admin" || user?.role === "moderator";
      const isLeaderHere = mine.some((m) => m.faction_slug === slug && m.rank === "leader");
      setCanManage(Boolean(isAdmin || isLeaderHere));

      const cityLists = await Promise.all(
        NATION_SLUGS.map((n) => WorldApi.cities(n).catch(() => [])),
      );
      const opts: PickerOption[] = [];
      const natMap: Record<string, string> = {};
      cityLists.forEach((list, i) => {
        const nation = NATION_SLUGS[i];
        list.forEach((c) => {
          if (natMap[c.slug]) return;
          opts.push({ label: `${c.name} (${nation})`, value: c.slug });
          natMap[c.slug] = nation;
        });
      });
      setCityOptions(opts);
      setCityNation(natMap);
      setStatus("ready");
    } catch {
      setStatus("error");
    }
  }, [slug, user?.role]);

  useEffect(() => {
    load();
  }, [load]);

  const createRoute = async () => {
    if (!good || !citySlug) {
      toast.show("Pick a good and a destination city.", "error");
      return;
    }
    setCreating(true);
    try {
      await EconomyApi.createContract(slug, {
        from_faction_slug: slug,
        to_type: "city",
        good_slug: good,
        to_city_slug: citySlug,
        to_nation: cityNation[citySlug],
        tariff_pct: parseInt(tariff, 10) || 0,
        quantity_per_tick: parseInt(qty, 10) || 1,
      });
      toast.show("Trade route opened.", "success");
      setCreateOpen(false);
      setGood("");
      setCitySlug("");
      await load();
    } catch (e) {
      toast.show(e instanceof Error ? e.message : "Could not open route.", "error");
    } finally {
      setCreating(false);
    }
  };

  const doBreak = async () => {
    if (!breakTarget) return;
    setBreaking(true);
    try {
      await EconomyApi.breakContract(
        slug,
        breakTarget.id,
        breakReason.trim() || "Route closed by leadership",
      );
      toast.show("Route broken — prices will shift next cycle.", "info");
      setBreakTarget(null);
      setBreakReason("");
      await load();
    } catch (e) {
      toast.show(e instanceof Error ? e.message : "Could not break route.", "error");
    } finally {
      setBreaking(false);
    }
  };

  const active = contracts.filter((c) => c.status === "active");
  const broken = contracts.filter((c) => c.status !== "active");

  const renderCard = (c: TradeContract) => {
    const isActive = c.status === "active";
    const dest = c.to_type === "city" ? prettify(c.to_city_slug || "") : prettify(c.to_faction_slug || "");
    return (
      <View key={c.id} testID={`${FACTIONS.routeCard}-${c.id}`} style={styles.card}>
        <View style={styles.cardHead}>
          <Text style={styles.cardGood}>{prettify(c.good_slug)}</Text>
          <Pill label={isActive ? "Active" : "Broken"} color={isActive ? colors.green : colors.rose} />
        </View>
        <Text style={styles.cardDest}>→ {dest}</Text>
        <View style={styles.cardMeta}>
          <Text style={styles.metaText}>Tariff {c.tariff_pct}%</Text>
          <Text style={styles.metaText}>· {c.quantity_per_tick}/tick</Text>
          <Text style={styles.metaText}>· {c.base_cost_snapshot}g base</Text>
        </View>
        <Text style={styles.delivered}>Delivers at {delivered(c)}g</Text>
        {c.break_reason ? <Text style={styles.brokenReason}>&ldquo;{c.break_reason}&rdquo;</Text> : null}
        {canManage && isActive ? (
          <Button
            title="Break route"
            icon="close-circle-outline"
            variant="danger"
            onPress={() => setBreakTarget(c)}
            testID={`${FACTIONS.routeBreakButton}-${c.id}`}
            style={styles.breakBtn}
          />
        ) : null}
      </View>
    );
  };

  return (
    <SafeAreaView style={styles.safe} edges={["top"]} testID={FACTIONS.routesScreen}>
      <Header title="Trade Routes" subtitle={name ?? "Faction economy"} showBack />
      {status === "loading" ? (
        <Loading label="Reading the trade ledger…" />
      ) : status === "error" ? (
        <ErrorView message="Could not load trade routes." onRetry={load} />
      ) : (
        <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
          <Text style={styles.intro}>
            Standing contracts ship this faction&apos;s goods to cities. Each pays the source&apos;s
            base cost plus a tariff — the delivered price is what shops there can source at.
          </Text>

          {canManage ? (
            <Button
              title="Open new route"
              icon="add-circle-outline"
              onPress={() => setCreateOpen(true)}
              testID={FACTIONS.newRouteButton}
              style={styles.newBtn}
            />
          ) : (
            <Text style={styles.hint}>Only this faction&apos;s Leader can open or break routes.</Text>
          )}

          {active.length === 0 && broken.length === 0 ? (
            <EmptyState
              icon="git-network-outline"
              title="No trade routes yet"
              subtitle={canManage ? "Open one to start moving goods." : "This faction hasn't opened any routes."}
            />
          ) : null}

          {active.length > 0 ? <Text style={styles.sectionLabel}>Active ({active.length})</Text> : null}
          {active.map(renderCard)}

          {broken.length > 0 ? <Text style={styles.sectionLabel}>Broken ({broken.length})</Text> : null}
          {broken.map(renderCard)}
        </ScrollView>
      )}

      {/* Create route modal */}
      <Modal visible={createOpen} transparent animationType="fade" onRequestClose={() => setCreateOpen(false)}>
        <Pressable style={styles.backdrop} onPress={() => setCreateOpen(false)}>
          <Pressable style={styles.sheet} onPress={() => {}}>
            <Text style={styles.sheetTitle}>Open trade route</Text>
            <PickerField
              testID={FACTIONS.routeGood}
              label="Good"
              placeholder="Select a good you produce"
              value={good}
              onSelect={setGood}
              options={specialties.map((s) => ({ label: prettify(s.good_slug), value: s.good_slug }))}
            />
            <PickerField
              testID={FACTIONS.routeCity}
              label="Destination city"
              placeholder="Select a city"
              value={citySlug}
              onSelect={setCitySlug}
              options={cityOptions}
            />
            <View style={styles.row}>
              <View style={styles.half}>
                <Text style={styles.fieldLabel}>Tariff %</Text>
                <TextInput
                  testID={FACTIONS.routeTariff}
                  value={tariff}
                  onChangeText={setTariff}
                  keyboardType="number-pad"
                  style={styles.field}
                />
              </View>
              <View style={styles.half}>
                <Text style={styles.fieldLabel}>Qty / tick</Text>
                <TextInput
                  value={qty}
                  onChangeText={setQty}
                  keyboardType="number-pad"
                  style={styles.field}
                />
              </View>
            </View>
            <Button
              title="Open route"
              icon="checkmark"
              onPress={createRoute}
              loading={creating}
              testID={FACTIONS.routeCreateSubmit}
              style={styles.newBtn}
            />
          </Pressable>
        </Pressable>
      </Modal>

      {/* Break confirm modal */}
      <Modal visible={!!breakTarget} transparent animationType="fade" onRequestClose={() => setBreakTarget(null)}>
        <Pressable style={styles.backdrop} onPress={() => setBreakTarget(null)}>
          <Pressable style={styles.sheet} onPress={() => {}}>
            <Text style={styles.sheetTitle}>Break this route?</Text>
            <Text style={styles.breakInfo}>
              {breakTarget ? `${prettify(breakTarget.good_slug)} → ${prettify(breakTarget.to_city_slug || "")}` : ""}
            </Text>
            <TextInput
              value={breakReason}
              onChangeText={setBreakReason}
              placeholder="Reason (optional)"
              placeholderTextColor={colors.textMuted}
              style={styles.field}
            />
            <View style={styles.confirmRow}>
              <Button title="Cancel" variant="ghost" onPress={() => setBreakTarget(null)} style={styles.confirmBtn} />
              <Button title="Break" variant="danger" onPress={doBreak} loading={breaking} style={styles.confirmBtn} />
            </View>
          </Pressable>
        </Pressable>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.bg },
  content: { padding: spacing.md, paddingBottom: spacing.xxl },
  intro: { ...typography.small, color: colors.textSecondary, lineHeight: 20, marginBottom: spacing.md },
  newBtn: { marginTop: spacing.sm },
  hint: { ...typography.small, color: colors.textMuted, marginBottom: spacing.sm },
  sectionLabel: {
    ...typography.tiny,
    color: colors.gold,
    textTransform: "uppercase",
    letterSpacing: 1,
    marginTop: spacing.lg,
    marginBottom: spacing.sm,
  },
  card: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.lg,
    padding: spacing.md,
    marginBottom: spacing.md,
  },
  cardHead: { flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  cardGood: { ...typography.h3, color: colors.textPrimary },
  cardDest: { ...typography.body, color: colors.textSecondary, marginTop: 2 },
  cardMeta: { flexDirection: "row", flexWrap: "wrap", gap: 6, marginTop: spacing.sm },
  metaText: { ...typography.small, color: colors.textMuted },
  delivered: { ...typography.bodyStrong, color: colors.green, marginTop: spacing.sm },
  brokenReason: { ...typography.small, color: colors.rose, fontStyle: "italic", marginTop: 4 },
  breakBtn: { marginTop: spacing.md },
  backdrop: { flex: 1, backgroundColor: colors.overlay, justifyContent: "flex-end" },
  sheet: {
    backgroundColor: colors.bgElevated,
    borderTopLeftRadius: radius.xl,
    borderTopRightRadius: radius.xl,
    borderWidth: 1,
    borderColor: colors.border,
    padding: spacing.lg,
    paddingBottom: spacing.xl,
  },
  sheetTitle: { ...typography.h2, color: colors.textPrimary, marginBottom: spacing.md },
  row: { flexDirection: "row", justifyContent: "space-between" },
  half: { width: "48%" },
  fieldLabel: { ...typography.small, color: colors.textSecondary, fontWeight: "600", marginBottom: spacing.xs },
  field: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.md,
    paddingHorizontal: spacing.md,
    paddingVertical: 13,
    color: colors.textPrimary,
    fontSize: 15,
    marginBottom: spacing.md,
  },
  breakInfo: { ...typography.body, color: colors.textSecondary, marginBottom: spacing.md },
  confirmRow: { flexDirection: "row", gap: spacing.sm },
  confirmBtn: { flex: 1 },
});
