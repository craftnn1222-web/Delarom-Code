import { Ionicons } from "@expo/vector-icons";
import { useLocalSearchParams } from "expo-router";
import { useCallback, useEffect, useState } from "react";
import { FlatList, Modal, Pressable, StyleSheet, Text, TextInput, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { MARKET, SELL } from "@/constants/testIds";
import { Item, Shop, ShopApi } from "@/src/api";
import { Button } from "@/src/components/Button";
import { Header } from "@/src/components/Header";
import { Pill } from "@/src/components/Pill";
import { EmptyState, ErrorView, Loading } from "@/src/components/StateViews";
import { useToast } from "@/src/components/Toast";
import { useAuth } from "@/src/context/AuthContext";
import { useActiveCharacter } from "@/src/hooks/useActiveCharacter";
import { colors, radius, spacing, typography } from "@/src/theme/theme";

export default function ShopScreen() {
  const { shopId, name } = useLocalSearchParams<{ shopId: string; name: string }>();
  const { refresh } = useAuth();
  const toast = useToast();
  const { character, noHero } = useActiveCharacter();
  const [shop, setShop] = useState<Shop | null>(null);
  const [items, setItems] = useState<Item[]>([]);
  const [status, setStatus] = useState<"loading" | "error" | "ready">("loading");
  const [buyingId, setBuyingId] = useState<string | null>(null);
  const [sellOpen, setSellOpen] = useState(false);
  const [sellItemId, setSellItemId] = useState<string | null>(null);
  const [sellPrice, setSellPrice] = useState("");
  const [sellBusy, setSellBusy] = useState(false);

  const load = useCallback(async () => {
    if (!shopId) return;
    setStatus("loading");
    try {
      const [s, its] = await Promise.all([ShopApi.get(shopId), ShopApi.items(shopId)]);
      setShop(s);
      setItems(its);
      setStatus("ready");
    } catch {
      setStatus("error");
    }
  }, [shopId]);

  useEffect(() => {
    load();
  }, [load]);

  const buy = async (item: Item) => {
    if (!character) {
      toast.show("Create a hero before buying.", "error");
      return;
    }
    setBuyingId(item.id);
    try {
      const res = await ShopApi.purchase(item.id, character.id);
      await refresh();
      await load();
      toast.show(
        `Bought ${item.name} · Paid ${res.price_paid} g · Balance ${res.new_balance} g`,
        "success",
      );
    } catch (e) {
      toast.show(e instanceof Error ? e.message : "Could not buy — try again.", "error");
    } finally {
      setBuyingId(null);
    }
  };

  const inventory = character?.inventory ?? [];

  const openSell = () => {
    setSellItemId(null);
    setSellPrice("");
    setSellOpen(true);
  };

  const submitSell = async () => {
    if (!character || !shopId || !sellItemId) {
      toast.show("Pick an item to sell.", "error");
      return;
    }
    const price = parseInt(sellPrice, 10);
    if (!price || price <= 0) {
      toast.show("Name a positive price.", "error");
      return;
    }
    setSellBusy(true);
    try {
      await ShopApi.createBuyOffer(shopId, {
        character_id: character.id,
        inventory_item_id: sellItemId,
        proposed_price: price,
      });
      toast.show("Offer sent — the shopkeeper will decide.", "success");
      setSellOpen(false);
    } catch (e) {
      toast.show(e instanceof Error ? e.message : "Could not send offer.", "error");
    } finally {
      setSellBusy(false);
    }
  };

  return (
    <SafeAreaView style={styles.safe} edges={["top"]} testID={MARKET.shopScreen}>
      <Header title={name ?? "Shop"} subtitle={shop?.owner_username ? `by ${shop.owner_username}` : undefined} showBack />
      {status === "loading" ? (
        <Loading label="Browsing the wares…" />
      ) : status === "error" || !shop ? (
        <ErrorView message="Could not load this shop." onRetry={load} />
      ) : (
        <FlatList
          data={items}
          keyExtractor={(i) => i.id}
          contentContainerStyle={styles.list}
          showsVerticalScrollIndicator={false}
          ListHeaderComponent={
            <View style={styles.shopHeader}>
              <Text style={styles.shopDesc}>{shop.description}</Text>
              {character ? (
                <View style={styles.buyingAs}>
                  <Ionicons name="bag-handle-outline" size={14} color={colors.gold} />
                  <Text style={styles.buyingAsText}>Buying for {character.name}</Text>
                </View>
              ) : noHero ? (
                <Text style={styles.warn}>Create a hero to purchase items.</Text>
              ) : null}
              {character ? (
                <Button
                  title="Sell an item"
                  icon="pricetag-outline"
                  variant="secondary"
                  onPress={openSell}
                  testID={SELL.button}
                  style={styles.sellBtn}
                />
              ) : null}
            </View>
          }
          ListEmptyComponent={<EmptyState icon="cube-outline" title="No items for sale" />}
          renderItem={({ item }) => {
            const out = item.stock <= 0;
            return (
              <View testID={MARKET.itemCard} style={styles.item}>
                <View style={styles.itemHead}>
                  <Text style={styles.itemName} numberOfLines={1}>
                    {item.name}
                  </Text>
                  <Text style={styles.price}>{item.price} g</Text>
                </View>
                <Text style={styles.itemDesc} numberOfLines={2}>
                  {item.description}
                </Text>
                <View style={styles.metaRow}>
                  {item.item_type ? <Pill label={item.item_type} color={colors.textMuted} /> : null}
                  {item.equipment_slot ? <Pill label={item.equipment_slot} color={colors.violetSoft} /> : null}
                  {item.stat_bonuses
                    ? Object.entries(item.stat_bonuses).map(([k, v]) => (
                        <Pill key={k} label={`${k} +${v}`} color={colors.green} />
                      ))
                    : null}
                </View>
                <View style={styles.itemFoot}>
                  <Text style={[styles.stock, out && styles.stockOut]}>
                    {out ? "Out of stock" : `${item.stock} in stock`}
                  </Text>
                  <Button
                    title={out ? "Sold out" : "Buy"}
                    icon={out ? undefined : "cart-outline"}
                    onPress={() => buy(item)}
                    loading={buyingId === item.id}
                    disabled={out || !character}
                    testID={`${MARKET.buyButton}-${item.id}`}
                    style={styles.buyBtn}
                  />
                </View>
              </View>
            );
          }}
        />
      )}

      <Modal visible={sellOpen} transparent animationType="fade" onRequestClose={() => setSellOpen(false)}>
        <Pressable style={styles.backdrop} onPress={() => setSellOpen(false)}>
          <Pressable style={styles.sheet} onPress={() => {}} testID={SELL.modal}>
            <Text style={styles.sheetTitle}>Sell to {shop?.name ?? "shop"}</Text>
            <Text style={styles.sheetSub}>
              Offer an item from {character?.name}. The owner accepts or declines.
            </Text>
            {inventory.length === 0 ? (
              <Text style={styles.warn} testID={SELL.empty}>
                {character?.name} has nothing to sell yet.
              </Text>
            ) : (
              <View style={styles.invList}>
                {inventory.map((inv) => {
                  const selected = sellItemId === inv.id;
                  return (
                    <Pressable
                      key={inv.id}
                      onPress={() => setSellItemId(inv.id)}
                      style={[styles.invRow, selected && styles.invRowActive]}
                      testID={SELL.itemOption(inv.id)}
                    >
                      <Ionicons
                        name={selected ? "radio-button-on" : "radio-button-off"}
                        size={18}
                        color={selected ? colors.gold : colors.textMuted}
                      />
                      <Text style={styles.invName} numberOfLines={1}>
                        {inv.name}
                      </Text>
                    </Pressable>
                  );
                })}
              </View>
            )}
            <TextInput
              style={styles.priceInput}
              value={sellPrice}
              onChangeText={setSellPrice}
              placeholder="Asking price (gold)"
              placeholderTextColor={colors.textMuted}
              keyboardType="number-pad"
              testID={SELL.priceInput}
            />
            <View style={styles.sheetActions}>
              <Button title="Cancel" variant="ghost" onPress={() => setSellOpen(false)} testID={SELL.cancel} style={styles.sheetBtn} />
              <Button
                title="Send offer"
                onPress={submitSell}
                loading={sellBusy}
                disabled={!sellItemId}
                testID={SELL.submit}
                style={styles.sheetBtn}
              />
            </View>
          </Pressable>
        </Pressable>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.bg },
  list: { padding: spacing.md, paddingBottom: spacing.xxl, gap: spacing.md },
  shopHeader: { marginBottom: spacing.sm },
  shopDesc: { ...typography.body, color: colors.textSecondary, lineHeight: 21 },
  buyingAs: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    alignSelf: "flex-start",
    marginTop: spacing.md,
    paddingHorizontal: spacing.md,
    paddingVertical: 6,
    borderRadius: radius.pill,
    backgroundColor: colors.goldDim,
    borderWidth: 1,
    borderColor: colors.goldBorder,
  },
  buyingAsText: { ...typography.small, color: colors.goldSoft, fontWeight: "600" },
  warn: { ...typography.small, color: colors.textMuted, marginTop: spacing.md },
  sellBtn: { alignSelf: "flex-start", marginTop: spacing.md, minHeight: 40 },
  item: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.lg,
    padding: spacing.md,
  },
  itemHead: { flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  itemName: { ...typography.h3, color: colors.textPrimary, flex: 1, marginRight: spacing.sm },
  price: { ...typography.h3, color: colors.gold },
  itemDesc: { ...typography.small, color: colors.textSecondary, marginTop: 4 },
  metaRow: { flexDirection: "row", flexWrap: "wrap", gap: spacing.sm, marginTop: spacing.sm },
  itemFoot: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginTop: spacing.md,
  },
  stock: { ...typography.small, color: colors.textSecondary },
  stockOut: { color: colors.rose },
  buyBtn: { minHeight: 40, paddingHorizontal: spacing.lg },
  backdrop: { flex: 1, backgroundColor: colors.overlay, justifyContent: "center", padding: spacing.lg },
  sheet: {
    backgroundColor: colors.bgElevated,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.border,
    padding: spacing.lg,
  },
  sheetTitle: { ...typography.h2, color: colors.textPrimary },
  sheetSub: { ...typography.small, color: colors.textSecondary, marginTop: spacing.xs, marginBottom: spacing.md },
  invList: { gap: spacing.xs, marginBottom: spacing.md },
  invRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.md,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
  },
  invRowActive: { borderColor: colors.goldBorder, backgroundColor: colors.goldDim },
  invName: { ...typography.body, color: colors.textPrimary, flex: 1 },
  priceInput: {
    backgroundColor: colors.bg,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.md,
    paddingHorizontal: spacing.md,
    paddingVertical: 10,
    color: colors.textPrimary,
    ...typography.body,
  },
  sheetActions: { flexDirection: "row", gap: spacing.sm, marginTop: spacing.md },
  sheetBtn: { flex: 1 },
});
