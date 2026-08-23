import { Ionicons } from "@expo/vector-icons";
import { useCallback, useEffect, useState } from "react";
import { ActivityIndicator, StyleSheet, Text, TextInput, TouchableOpacity, View } from "react-native";

import { BUYOFFERS } from "@/constants/testIds";
import { ShopApi, ShopBuyOffer } from "@/src/api";
import { Button } from "@/src/components/Button";
import { useToast } from "@/src/components/Toast";
import { useAuth } from "@/src/context/AuthContext";
import { colors, radius, spacing, typography } from "@/src/theme/theme";

type State = "loading" | "error" | "ready";

export function ShopBuyOffersSection({ shopId }: { shopId: string }) {
  const toast = useToast();
  const { refresh } = useAuth();
  const [treasury, setTreasury] = useState(0);
  const [offers, setOffers] = useState<ShopBuyOffer[]>([]);
  const [state, setState] = useState<State>("loading");
  const [amount, setAmount] = useState("");
  const [busy, setBusy] = useState("");

  const load = useCallback(async () => {
    setState("loading");
    try {
      const res = await ShopApi.buyOffers(shopId);
      setTreasury(res.treasury);
      setOffers(res.offers);
      setState("ready");
    } catch {
      setState("error");
    }
  }, [shopId]);

  useEffect(() => {
    load();
  }, [load]);

  const move = async (dir: "deposit" | "withdraw") => {
    const amt = parseInt(amount, 10);
    if (!amt || amt <= 0) {
      toast.show("Enter a positive amount.", "error");
      return;
    }
    setBusy(dir);
    try {
      const res = dir === "deposit"
        ? await ShopApi.treasuryDeposit(shopId, amt)
        : await ShopApi.treasuryWithdraw(shopId, amt);
      setTreasury(res.treasury);
      setAmount("");
      await refresh();
      toast.show(dir === "deposit" ? `Deposited ${amt} g` : `Withdrew ${amt} g`, "success");
    } catch (e) {
      toast.show(e instanceof Error ? e.message : "Could not move gold.", "error");
    } finally {
      setBusy("");
    }
  };

  const resolve = async (offer: ShopBuyOffer, action: "accept" | "decline") => {
    setBusy(offer.id);
    try {
      if (action === "accept") {
        const res = await ShopApi.acceptBuyOffer(shopId, offer.id);
        toast.show(`Bought ${offer.item.name} (paid from ${res.paid_from}).`, "success");
      } else {
        await ShopApi.declineBuyOffer(shopId, offer.id);
        toast.show(`Declined ${offer.item.name}.`, "info");
      }
      await refresh();
      await load();
    } catch (e) {
      toast.show(e instanceof Error ? e.message : "Action failed.", "error");
    } finally {
      setBusy("");
    }
  };

  return (
    <View testID={BUYOFFERS.section}>
      <Text style={styles.sectionLabel}>Buy Offers</Text>
      <Text style={styles.hint}>Players and NPCs bring wares. Accept to pay from treasury (then your purse) and re-list.</Text>

      <View style={styles.treasuryCard}>
        <View style={styles.treasuryHead}>
          <View style={styles.treasuryLabel}>
            <Ionicons name="wallet-outline" size={16} color={colors.gold} />
            <Text style={styles.treasuryText}>Treasury</Text>
          </View>
          <Text style={styles.treasuryBalance} testID={BUYOFFERS.treasuryBalance}>
            {treasury.toLocaleString()} g
          </Text>
        </View>
        <View style={styles.treasuryRow}>
          <TextInput
            style={styles.input}
            value={amount}
            onChangeText={setAmount}
            placeholder="Amount"
            placeholderTextColor={colors.textMuted}
            keyboardType="number-pad"
            testID={BUYOFFERS.amountInput}
          />
          <Button title="Deposit" variant="secondary" loading={busy === "deposit"} onPress={() => move("deposit")} testID={BUYOFFERS.deposit} style={styles.tBtn} />
          <Button title="Withdraw" variant="ghost" loading={busy === "withdraw"} onPress={() => move("withdraw")} testID={BUYOFFERS.withdraw} style={styles.tBtn} />
        </View>
      </View>

      {state === "loading" ? (
        <ActivityIndicator color={colors.gold} style={{ marginTop: spacing.md }} />
      ) : state === "error" ? (
        <TouchableOpacity style={styles.center} onPress={load}>
          <Text style={styles.retry}>Couldn&apos;t load offers. Tap to retry.</Text>
        </TouchableOpacity>
      ) : offers.length === 0 ? (
        <Text style={styles.hint} testID={BUYOFFERS.empty}>
          No one is selling right now. Offers appear here.
        </Text>
      ) : (
        offers.map((o) => (
          <View key={o.id} style={styles.offer} testID={BUYOFFERS.offer(o.id)}>
            <View style={styles.offerHead}>
              <Text style={styles.offerName} numberOfLines={1}>
                {o.item.name}
              </Text>
              <View style={[styles.kindTag, o.seller_type === "player" ? styles.kindPlayer : styles.kindNpc]}>
                <Text style={[styles.kindText, { color: o.seller_type === "player" ? colors.violetSoft : colors.textSecondary }]}>
                  {o.seller_type === "player" ? "Player" : "NPC"}
                </Text>
              </View>
              <Text style={styles.offerPrice}>{o.proposed_price} g</Text>
            </View>
            <Text style={styles.offerMeta} numberOfLines={1}>
              from {o.seller_name}
            </Text>
            <View style={styles.offerActions}>
              <Button title="Accept" icon="checkmark" loading={busy === o.id} onPress={() => resolve(o, "accept")} testID={BUYOFFERS.accept(o.id)} style={styles.offerBtn} />
              <Button title="Decline" variant="danger" loading={busy === o.id} onPress={() => resolve(o, "decline")} testID={BUYOFFERS.decline(o.id)} style={styles.offerBtn} />
            </View>
          </View>
        ))
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
  center: { alignItems: "center", paddingVertical: spacing.md },
  retry: { ...typography.small, color: colors.gold },
  treasuryCard: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.goldBorder,
    borderRadius: radius.lg,
    padding: spacing.md,
    marginBottom: spacing.md,
  },
  treasuryHead: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", marginBottom: spacing.sm },
  treasuryLabel: { flexDirection: "row", alignItems: "center", gap: 6 },
  treasuryText: { ...typography.bodyStrong, color: colors.textPrimary },
  treasuryBalance: { ...typography.h3, color: colors.gold },
  treasuryRow: { flexDirection: "row", alignItems: "center", gap: spacing.sm },
  input: {
    flex: 1,
    backgroundColor: colors.bg,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.md,
    paddingHorizontal: spacing.md,
    paddingVertical: 8,
    color: colors.textPrimary,
    ...typography.body,
  },
  tBtn: { minHeight: 40, paddingHorizontal: spacing.md },
  offer: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.md,
    padding: spacing.md,
    marginBottom: spacing.sm,
  },
  offerHead: { flexDirection: "row", alignItems: "center", gap: spacing.sm },
  offerName: { ...typography.bodyStrong, color: colors.textPrimary, flex: 1 },
  offerPrice: { ...typography.bodyStrong, color: colors.gold },
  kindTag: { paddingHorizontal: 6, paddingVertical: 2, borderRadius: radius.sm },
  kindNpc: { backgroundColor: colors.surfaceAlt },
  kindPlayer: { backgroundColor: colors.violetDim },
  kindText: { ...typography.tiny, textTransform: "uppercase" },
  offerMeta: { ...typography.small, color: colors.textSecondary, marginTop: 2 },
  offerActions: { flexDirection: "row", gap: spacing.sm, marginTop: spacing.sm },
  offerBtn: { flex: 1, minHeight: 40 },
});
