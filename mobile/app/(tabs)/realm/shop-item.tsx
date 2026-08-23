import { Ionicons } from "@expo/vector-icons";
import { router, useLocalSearchParams } from "expo-router";
import { useEffect, useState } from "react";
import {
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { SHOP } from "@/constants/testIds";
import { EconomyApi, Good, ItemCreatePayload, ShopApi, WorldApi } from "@/src/api";
import { Button } from "@/src/components/Button";
import { Header } from "@/src/components/Header";
import { PickerField, PickerOption } from "@/src/components/PickerField";
import { Loading } from "@/src/components/StateViews";
import { TextField } from "@/src/components/TextField";
import { useToast } from "@/src/components/Toast";
import { colors, radius, spacing, typography } from "@/src/theme/theme";

const EQUIP_SLOTS: PickerOption[] = [
  { label: "Weapon", value: "weapon" },
  { label: "Helmet", value: "head" },
  { label: "Chest Armor", value: "chest" },
  { label: "Leg Armor", value: "legs" },
  { label: "Boots", value: "boots" },
  { label: "Gloves", value: "gloves" },
  { label: "Ring", value: "ring" },
  { label: "Necklace", value: "necklace" },
];
const STATS = ["strength", "magic", "agility", "endurance", "charisma", "luck"] as const;
const NATION_SLUGS = ["aigraels", "dhor-kuldor", "selindori", "ammeonon"];

const emptyStats = (): Record<string, string> =>
  STATS.reduce((acc, s) => ({ ...acc, [s]: "0" }), {} as Record<string, string>);

export default function ShopItemFormScreen() {
  const { shopId, itemId } = useLocalSearchParams<{ shopId: string; itemId?: string }>();
  const toast = useToast();
  const editing = !!itemId;

  const [status, setStatus] = useState<"loading" | "ready">("loading");
  const [saving, setSaving] = useState(false);

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [price, setPrice] = useState("10");
  const [stock, setStock] = useState("1");
  const [category, setCategory] = useState("Weapon");
  const [slot, setSlot] = useState("weapon");
  const [stats, setStats] = useState<Record<string, string>>(emptyStats());

  const [autoPriced, setAutoPriced] = useState(false);
  const [good, setGood] = useState("");
  const [citySlug, setCitySlug] = useState("");
  const [markup, setMarkup] = useState("30");

  const [goods, setGoods] = useState<Good[]>([]);
  const [cityOptions, setCityOptions] = useState<PickerOption[]>([]);
  const [cityNation, setCityNation] = useState<Record<string, string>>({});

  const [livePrice, setLivePrice] = useState<number | null>(null);
  const [livePriceErr, setLivePriceErr] = useState("");

  useEffect(() => {
    (async () => {
      const goodsRes = await EconomyApi.goods().catch(() => [] as Good[]);
      setGoods(goodsRes);

      const cityLists = await Promise.all(
        NATION_SLUGS.map((n) => WorldApi.cities(n).catch(() => [])),
      );
      const opts: PickerOption[] = [];
      const natMap: Record<string, string> = {};
      cityLists.forEach((list, i) => {
        const nation = NATION_SLUGS[i];
        list.forEach((c) => {
          opts.push({ label: `${c.name} (${nation})`, value: c.slug });
          natMap[c.slug] = nation;
        });
      });
      setCityOptions(opts);
      setCityNation(natMap);

      if (itemId && shopId) {
        const its = await ShopApi.items(shopId).catch(() => []);
        const it = its.find((x) => x.id === itemId);
        if (it) {
          setName(it.name);
          setDescription(it.description);
          setPrice(String(it.price));
          setStock(String(it.stock));
          setCategory(it.category ?? "Weapon");
          setSlot(it.equipment_slot ?? "weapon");
          const sb = emptyStats();
          Object.entries(it.stat_bonuses ?? {}).forEach(([k, v]) => {
            if (k in sb) sb[k] = String(v);
          });
          setStats(sb);
          setAutoPriced(Boolean(it.is_auto_priced));
          setGood(it.source_good_slug ?? "");
          setCitySlug(it.source_city_slug ?? "");
          setMarkup(String(it.markup_pct ?? 30));
        }
      }
      setStatus("ready");
    })();
  }, [itemId, shopId]);

  // Live retail preview — mirrors the backend price chain.
  useEffect(() => {
    if (!autoPriced || !good || !citySlug) {
      setLivePrice(null);
      setLivePriceErr("");
      return;
    }
    const nation = cityNation[citySlug];
    if (!nation) return;
    let cancelled = false;
    (async () => {
      try {
        const market = await EconomyApi.market(nation, citySlug);
        const row = market.find((p) => p.good_slug === good);
        if (!row || !row.is_available || row.import_price == null) {
          if (!cancelled) {
            setLivePrice(null);
            setLivePriceErr("No active trade contract supplies this good to that city yet.");
          }
          return;
        }
        const retail = Math.round(row.import_price * (1 + (parseInt(markup, 10) || 0) / 100));
        if (!cancelled) {
          setLivePrice(retail);
          setLivePriceErr("");
        }
      } catch {
        if (!cancelled) {
          setLivePrice(null);
          setLivePriceErr("Market preview failed.");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [autoPriced, good, citySlug, markup, cityNation]);

  const submit = async () => {
    if (name.trim().length < 2 || description.trim().length < 2) {
      toast.show("Give the item a name and description.", "error");
      return;
    }
    if (autoPriced && (!good || !citySlug)) {
      toast.show("Pick a good and a source city for auto-pricing.", "error");
      return;
    }
    if (!autoPriced && (parseInt(price, 10) || 0) < 1) {
      toast.show("Set a price of at least 1 gold.", "error");
      return;
    }

    const statBonuses: Record<string, number> = {};
    Object.entries(stats).forEach(([k, v]) => {
      const n = parseInt(v, 10) || 0;
      if (n > 0) statBonuses[k] = n;
    });

    const payload: ItemCreatePayload = {
      name: name.trim(),
      description: description.trim(),
      price: parseInt(price, 10) || 0,
      stock: parseInt(stock, 10) || 0,
      category: category.trim() || "Misc",
      item_type: "equipment",
      equipment_slot: slot,
      stat_bonuses: statBonuses,
      is_auto_priced: autoPriced,
      source_good_slug: autoPriced ? good : null,
      source_city_slug: autoPriced ? citySlug : null,
      source_nation: autoPriced ? cityNation[citySlug] : null,
      markup_pct: autoPriced ? parseInt(markup, 10) || 0 : null,
    };

    setSaving(true);
    try {
      if (editing && itemId) {
        await ShopApi.updateItem(itemId, payload);
        toast.show("Item updated.", "success");
      } else {
        await ShopApi.addItem(shopId, payload);
        toast.show("Item added to your shop.", "success");
      }
      router.back();
    } catch (e) {
      toast.show(e instanceof Error ? e.message : "Could not save the item.", "error");
    } finally {
      setSaving(false);
    }
  };

  return (
    <SafeAreaView style={styles.safe} edges={["top"]} testID={SHOP.itemFormScreen}>
      <Header title={editing ? "Edit Item" : "Add Item"} subtitle="Your shop" showBack />
      {status === "loading" ? (
        <Loading label="Preparing the counter…" />
      ) : (
        <KeyboardAvoidingView
          style={styles.flex}
          behavior={Platform.OS === "ios" ? "padding" : undefined}
        >
          <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
            <TextField
              testID={SHOP.itemName}
              label="Item name"
              value={name}
              onChangeText={setName}
              placeholder="e.g., Dragonbone Blade"
            />
            <TextField
              testID={SHOP.itemDescription}
              label="Description"
              value={description}
              onChangeText={setDescription}
              placeholder="Describe the item…"
              multiline
              numberOfLines={3}
            />

            <View style={styles.row}>
              <TextField
                testID={SHOP.itemPrice}
                label={autoPriced ? "Price (auto)" : "Price (gold)"}
                value={price}
                onChangeText={setPrice}
                keyboardType="number-pad"
                editable={!autoPriced}
                style={styles.half}
              />
              <TextField
                testID={SHOP.itemStock}
                label="Stock"
                value={stock}
                onChangeText={setStock}
                keyboardType="number-pad"
                style={styles.half}
              />
            </View>

            <TextField
              testID={SHOP.itemCategory}
              label="Category"
              value={category}
              onChangeText={setCategory}
              placeholder="Weapon, Armor, Potion…"
            />
            <PickerField
              testID={SHOP.itemSlot}
              label="Equipment slot"
              value={slot}
              onSelect={setSlot}
              options={EQUIP_SLOTS}
            />

            <Text style={styles.groupLabel}>Stat bonuses (optional)</Text>
            <View style={styles.statGrid}>
              {STATS.map((s) => (
                <TextField
                  key={s}
                  label={s.charAt(0).toUpperCase() + s.slice(1)}
                  value={stats[s]}
                  onChangeText={(v) => setStats({ ...stats, [s]: v })}
                  keyboardType="number-pad"
                  style={styles.statField}
                />
              ))}
            </View>

            {/* Auto-pricing */}
            <View style={styles.autoBox}>
              <TouchableOpacity
                testID={SHOP.autoPriceToggle}
                activeOpacity={0.85}
                style={styles.autoToggle}
                onPress={() => setAutoPriced((v) => !v)}
              >
                <Ionicons
                  name={autoPriced ? "checkbox" : "square-outline"}
                  size={20}
                  color={colors.gold}
                />
                <Ionicons name="sparkles" size={16} color={colors.goldSoft} />
                <Text style={styles.autoLabel}>Source from the goods market</Text>
              </TouchableOpacity>
              <Text style={styles.autoHint}>
                Live-link this item to a faction-produced good. Price moves with production cost,
                city tariffs, and your markup.
              </Text>

              {autoPriced ? (
                <View style={styles.autoFields}>
                  <PickerField
                    testID={SHOP.itemGood}
                    label="Good"
                    placeholder="Select a good"
                    value={good}
                    onSelect={setGood}
                    options={goods.map((g) => ({ label: g.name, value: g.slug }))}
                  />
                  <PickerField
                    testID={SHOP.itemCity}
                    label="Source city"
                    placeholder="Select a city"
                    value={citySlug}
                    onSelect={setCitySlug}
                    options={cityOptions}
                  />
                  <TextField
                    testID={SHOP.itemMarkup}
                    label="Your markup %"
                    value={markup}
                    onChangeText={setMarkup}
                    keyboardType="number-pad"
                  />
                  <View style={styles.previewRow}>
                    <Text style={styles.previewLabel}>Live retail price</Text>
                    {livePrice != null ? (
                      <Text style={styles.previewPrice}>{livePrice} g</Text>
                    ) : (
                      <Text style={styles.previewErr}>{livePriceErr || "Pick good + city."}</Text>
                    )}
                  </View>
                </View>
              ) : null}
            </View>

            <Button
              title={editing ? "Save changes" : "Add item"}
              icon="checkmark"
              onPress={submit}
              loading={saving}
              testID={SHOP.itemSubmit}
              style={styles.submit}
            />
          </ScrollView>
        </KeyboardAvoidingView>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.bg },
  flex: { flex: 1 },
  content: { padding: spacing.md, paddingBottom: spacing.xxl },
  row: { flexDirection: "row", justifyContent: "space-between" },
  half: { width: "48%" },
  groupLabel: {
    ...typography.small,
    color: colors.textSecondary,
    fontWeight: "600",
    marginBottom: spacing.sm,
  },
  statGrid: { flexDirection: "row", flexWrap: "wrap", justifyContent: "space-between" },
  statField: { width: "48%" },
  autoBox: {
    borderWidth: 1,
    borderColor: colors.goldBorder,
    backgroundColor: colors.goldDim,
    borderRadius: radius.md,
    padding: spacing.md,
    marginTop: spacing.sm,
  },
  autoToggle: { flexDirection: "row", alignItems: "center", gap: spacing.sm },
  autoLabel: { ...typography.bodyStrong, color: colors.goldSoft },
  autoHint: { ...typography.small, color: colors.textSecondary, marginTop: spacing.xs },
  autoFields: { marginTop: spacing.md },
  previewRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    padding: spacing.sm,
    borderRadius: radius.sm,
    backgroundColor: colors.bg,
    borderWidth: 1,
    borderColor: colors.goldBorder,
  },
  previewLabel: { ...typography.small, color: colors.textSecondary },
  previewPrice: { ...typography.bodyStrong, color: colors.gold },
  previewErr: { ...typography.tiny, color: colors.rose, textTransform: "none", flex: 1, textAlign: "right", marginLeft: spacing.sm },
  submit: { marginTop: spacing.lg },
});
