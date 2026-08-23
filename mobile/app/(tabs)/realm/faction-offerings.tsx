import { useLocalSearchParams } from "expo-router";
import { useCallback, useEffect, useState } from "react";
import { Modal, Pressable, ScrollView, StyleSheet, Text, TextInput, TouchableOpacity, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { OFFERINGS } from "@/constants/testIds";
import { EconomyApi, FactionApi, FactionSpecialty, Good } from "@/src/api";
import { Button } from "@/src/components/Button";
import { Header } from "@/src/components/Header";
import { PickerField, PickerOption } from "@/src/components/PickerField";
import { EmptyState, ErrorView, Loading } from "@/src/components/StateViews";
import { useToast } from "@/src/components/Toast";
import { useAuth } from "@/src/context/AuthContext";
import { colors, radius, spacing, typography } from "@/src/theme/theme";

export default function FactionOfferingsScreen() {
  const { slug, name } = useLocalSearchParams<{ slug: string; name: string }>();
  const toast = useToast();
  const { user } = useAuth();

  const [specialties, setSpecialties] = useState<FactionSpecialty[]>([]);
  const [goods, setGoods] = useState<Good[]>([]);
  const [canManage, setCanManage] = useState(false);
  const [status, setStatus] = useState<"loading" | "error" | "ready">("loading");

  const [open, setOpen] = useState(false);
  const [mode, setMode] = useState<"catalogue" | "custom">("catalogue");
  const [goodSlug, setGoodSlug] = useState("");
  const [name_, setName] = useState("");
  const [category, setCategory] = useState("");
  const [unit, setUnit] = useState("per unit");
  const [baseCost, setBaseCost] = useState("50");
  const [capacity, setCapacity] = useState("50");
  const [description, setDescription] = useState("");
  const [saving, setSaving] = useState(false);
  const [removing, setRemoving] = useState("");

  const load = useCallback(async () => {
    if (!slug) return;
    setStatus("loading");
    try {
      const [specs, cat, mine] = await Promise.all([
        EconomyApi.factionSpecialties(slug),
        EconomyApi.goods().catch(() => [] as Good[]),
        FactionApi.myMembership().catch(() => []),
      ]);
      setSpecialties(specs.specialties ?? []);
      setGoods(cat);
      const isAdmin = user?.role === "admin" || user?.role === "moderator";
      const isLeaderHere = mine.some((m) => m.faction_slug === slug && m.rank === "leader");
      setCanManage(Boolean(isAdmin || isLeaderHere));
      setStatus("ready");
    } catch {
      setStatus("error");
    }
  }, [slug, user?.role]);

  useEffect(() => {
    load();
  }, [load]);

  const openAdd = () => {
    setMode("catalogue");
    setGoodSlug(goods[0]?.slug ?? "");
    setName("");
    setCategory("");
    setUnit("per unit");
    setBaseCost("50");
    setCapacity("50");
    setDescription("");
    setOpen(true);
  };

  const save = async () => {
    const cost = parseInt(baseCost, 10);
    const cap = parseInt(capacity, 10) || 50;
    if (!cost || cost <= 0) {
      toast.show("Set a positive base cost.", "error");
      return;
    }
    setSaving(true);
    try {
      if (mode === "custom") {
        if (!name_.trim()) {
          toast.show("Name your product.", "error");
          setSaving(false);
          return;
        }
        await EconomyApi.addCustomOffering(slug, {
          name: name_.trim(),
          category: category.trim() || "custom",
          unit: unit.trim() || "per unit",
          base_cost: cost,
          capacity: cap,
          description: description.trim(),
        });
        toast.show("Custom offering coined.", "success");
      } else {
        if (!goodSlug) {
          toast.show("Pick a good.", "error");
          setSaving(false);
          return;
        }
        await EconomyApi.upsertSpecialty(slug, {
          good_slug: goodSlug,
          base_cost: cost,
          capacity: cap,
          description: description.trim(),
        });
        toast.show("Offering added.", "success");
      }
      setOpen(false);
      await load();
    } catch (e) {
      toast.show(e instanceof Error ? e.message : "Could not save offering.", "error");
    } finally {
      setSaving(false);
    }
  };

  const remove = async (s: FactionSpecialty) => {
    setRemoving(s.good_slug);
    try {
      await EconomyApi.removeSpecialty(slug, s.good_slug);
      toast.show("Offering removed.", "info");
      await load();
    } catch (e) {
      toast.show(e instanceof Error ? e.message : "Could not remove.", "error");
    } finally {
      setRemoving("");
    }
  };

  const goodOptions: PickerOption[] = goods.map((g) => ({
    label: `${g.name}${g.category ? ` (${g.category})` : ""}`,
    value: g.slug,
  }));

  return (
    <SafeAreaView style={styles.safe} edges={["top"]} testID={OFFERINGS.screen}>
      <Header title="Offerings" subtitle={name ? String(name) : "What this faction produces"} showBack />
      {status === "loading" ? (
        <Loading label="Reading the ledger…" />
      ) : status === "error" ? (
        <ErrorView message="Could not load offerings." onRetry={load} />
      ) : (
        <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
          {canManage ? (
            <Button title="Add offering" icon="add" onPress={openAdd} testID={OFFERINGS.addButton} style={styles.addBtn} />
          ) : null}

          {specialties.length === 0 ? (
            <EmptyState
              icon="cube-outline"
              title="No offerings yet"
              subtitle={canManage ? "Add what your faction produces." : "This faction hasn't declared its wares."}
            />
          ) : (
            specialties.map((s) => (
              <View key={s.id || s.good_slug} style={styles.card} testID={OFFERINGS.card(s.good_slug)}>
                <View style={styles.cardHead}>
                  <View style={styles.cardInfo}>
                    <Text style={styles.goodName}>{s.good_name || s.good_slug}</Text>
                    {s.good_category ? (
                      <Text style={styles.goodMeta}>
                        {s.good_category}
                        {s.good_unit ? ` · ${s.good_unit}` : ""}
                      </Text>
                    ) : null}
                  </View>
                  <View style={styles.cardRight}>
                    <Text style={styles.cost}>{s.base_cost} g</Text>
                    <Text style={styles.cap}>cap {s.capacity ?? 0}</Text>
                  </View>
                </View>
                {s.description ? <Text style={styles.desc}>{s.description}</Text> : null}
                {canManage ? (
                  <TouchableOpacity
                    onPress={() => remove(s)}
                    disabled={removing === s.good_slug}
                    style={styles.removeBtn}
                    testID={OFFERINGS.remove(s.good_slug)}
                  >
                    <Text style={styles.removeText}>{removing === s.good_slug ? "Removing…" : "Remove"}</Text>
                  </TouchableOpacity>
                ) : null}
              </View>
            ))
          )}
        </ScrollView>
      )}

      <Modal visible={open} transparent animationType="fade" onRequestClose={() => setOpen(false)}>
        <Pressable style={styles.backdrop} onPress={() => setOpen(false)}>
          <Pressable style={styles.sheet} onPress={() => {}}>
            <ScrollView showsVerticalScrollIndicator={false}>
              <Text style={styles.sheetTitle}>Add offering</Text>
              <View style={styles.modeRow}>
                <TouchableOpacity
                  onPress={() => setMode("catalogue")}
                  style={[styles.modeBtn, mode === "catalogue" && styles.modeActive]}
                  testID={OFFERINGS.modeCatalogue}
                >
                  <Text style={[styles.modeText, mode === "catalogue" && styles.modeTextActive]}>From catalogue</Text>
                </TouchableOpacity>
                <TouchableOpacity
                  onPress={() => setMode("custom")}
                  style={[styles.modeBtn, mode === "custom" && styles.modeActive]}
                  testID={OFFERINGS.modeCustom}
                >
                  <Text style={[styles.modeText, mode === "custom" && styles.modeTextActive]}>Type your own</Text>
                </TouchableOpacity>
              </View>

              {mode === "custom" ? (
                <>
                  <Text style={styles.label}>Product name</Text>
                  <TextInput style={styles.input} value={name_} onChangeText={setName} placeholder="e.g. Moonsteel Blades" placeholderTextColor={colors.textMuted} testID={OFFERINGS.customName} />
                  <Text style={styles.label}>Category</Text>
                  <TextInput style={styles.input} value={category} onChangeText={setCategory} placeholder="e.g. weapon" placeholderTextColor={colors.textMuted} testID={OFFERINGS.customCategory} />
                  <Text style={styles.label}>Unit</Text>
                  <TextInput style={styles.input} value={unit} onChangeText={setUnit} placeholder="e.g. per blade" placeholderTextColor={colors.textMuted} testID={OFFERINGS.customUnit} />
                </>
              ) : (
                <PickerField label="Good" value={goodSlug} options={goodOptions} onSelect={setGoodSlug} testID={OFFERINGS.goodPicker} />
              )}

              <Text style={styles.label}>Base cost (g/unit)</Text>
              <TextInput style={styles.input} value={baseCost} onChangeText={setBaseCost} keyboardType="number-pad" placeholderTextColor={colors.textMuted} testID={OFFERINGS.baseCost} />
              <Text style={styles.label}>Capacity / tick</Text>
              <TextInput style={styles.input} value={capacity} onChangeText={setCapacity} keyboardType="number-pad" placeholderTextColor={colors.textMuted} testID={OFFERINGS.capacity} />
              <Text style={styles.label}>Description (optional)</Text>
              <TextInput style={[styles.input, styles.multiline]} value={description} onChangeText={setDescription} multiline placeholder="How your faction makes this" placeholderTextColor={colors.textMuted} testID={OFFERINGS.description} />

              <View style={styles.sheetActions}>
                <Button title="Cancel" variant="ghost" onPress={() => setOpen(false)} testID={OFFERINGS.cancel} style={styles.sheetBtn} />
                <Button title="Save" onPress={save} loading={saving} testID={OFFERINGS.save} style={styles.sheetBtn} />
              </View>
            </ScrollView>
          </Pressable>
        </Pressable>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.bg },
  content: { padding: spacing.md, paddingBottom: spacing.xxl },
  addBtn: { marginBottom: spacing.md },
  card: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.goldBorder,
    borderRadius: radius.lg,
    padding: spacing.md,
    marginBottom: spacing.sm,
  },
  cardHead: { flexDirection: "row", alignItems: "flex-start", justifyContent: "space-between" },
  cardInfo: { flex: 1, marginRight: spacing.sm },
  goodName: { ...typography.h3, color: colors.goldSoft },
  goodMeta: { ...typography.tiny, color: colors.textMuted, textTransform: "uppercase", marginTop: 2 },
  cardRight: { alignItems: "flex-end" },
  cost: { ...typography.h3, color: colors.gold },
  cap: { ...typography.tiny, color: colors.textMuted },
  desc: { ...typography.small, color: colors.textSecondary, fontStyle: "italic", marginTop: spacing.sm },
  removeBtn: { alignSelf: "flex-start", marginTop: spacing.sm },
  removeText: { ...typography.small, color: colors.rose, fontWeight: "700" },
  backdrop: { flex: 1, backgroundColor: colors.overlay, justifyContent: "center", padding: spacing.lg },
  sheet: {
    backgroundColor: colors.bgElevated,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.border,
    padding: spacing.lg,
    maxHeight: "85%",
  },
  sheetTitle: { ...typography.h2, color: colors.textPrimary, marginBottom: spacing.md },
  modeRow: { flexDirection: "row", gap: spacing.sm, marginBottom: spacing.md },
  modeBtn: {
    flex: 1,
    paddingVertical: spacing.sm,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.goldBorder,
    alignItems: "center",
  },
  modeActive: { backgroundColor: colors.gold, borderColor: colors.gold },
  modeText: { ...typography.small, color: colors.goldSoft, fontWeight: "700" },
  modeTextActive: { color: colors.bg },
  label: { ...typography.tiny, color: colors.textSecondary, textTransform: "uppercase", marginTop: spacing.sm, marginBottom: 4 },
  input: {
    backgroundColor: colors.bg,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.md,
    paddingHorizontal: spacing.md,
    paddingVertical: 10,
    color: colors.textPrimary,
    ...typography.body,
  },
  multiline: { minHeight: 64, textAlignVertical: "top" },
  sheetActions: { flexDirection: "row", gap: spacing.sm, marginTop: spacing.lg },
  sheetBtn: { flex: 1 },
});
