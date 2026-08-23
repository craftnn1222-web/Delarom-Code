import { Ionicons } from "@expo/vector-icons";
import { router, useFocusEffect } from "expo-router";
import { useCallback, useState } from "react";
import {
  KeyboardAvoidingView,
  Modal,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { SHOP } from "@/constants/testIds";
import { CREATE_NATIONS, Item, Shop, ShopApi, ShopCustomer } from "@/src/api";
import { ApiError } from "@/src/api/client";
import { Button } from "@/src/components/Button";
import { Header } from "@/src/components/Header";
import { PickerField } from "@/src/components/PickerField";
import { Pill } from "@/src/components/Pill";
import { ErrorView, Loading } from "@/src/components/StateViews";
import { TextField } from "@/src/components/TextField";
import { useToast } from "@/src/components/Toast";
import { colors, radius, spacing, typography } from "@/src/theme/theme";

type Status = "loading" | "error" | "none" | "ready";

export default function MyShopScreen() {
  const toast = useToast();
  const [shop, setShop] = useState<Shop | null>(null);
  const [items, setItems] = useState<Item[]>([]);
  const [customers, setCustomers] = useState<ShopCustomer[]>([]);
  const [status, setStatus] = useState<Status>("loading");

  const [form, setForm] = useState({ name: "", description: "", nation: "Ammeonon" });
  const [creating, setCreating] = useState(false);

  const [deleteTarget, setDeleteTarget] = useState<Item | null>(null);
  const [deleting, setDeleting] = useState(false);

  const load = useCallback(async () => {
    setStatus("loading");
    try {
      const s = await ShopApi.myShop();
      setShop(s);
      const [its, cust] = await Promise.all([
        ShopApi.items(s.id),
        ShopApi.customers(s.id).catch(() => [] as ShopCustomer[]),
      ]);
      setItems(its);
      setCustomers(cust);
      setStatus("ready");
    } catch (e) {
      if (e instanceof ApiError && e.status === 404) {
        setShop(null);
        setStatus("none");
      } else {
        setStatus("error");
      }
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      load();
    }, [load]),
  );

  const createShop = async () => {
    if (form.name.trim().length < 2 || form.description.trim().length < 2) {
      toast.show("Give your shop a name and description.", "error");
      return;
    }
    setCreating(true);
    try {
      await ShopApi.create({
        name: form.name.trim(),
        description: form.description.trim(),
        nation: form.nation,
      });
      toast.show("Your shop is open for business!", "success");
      await load();
    } catch (e) {
      toast.show(e instanceof Error ? e.message : "Could not create shop.", "error");
    } finally {
      setCreating(false);
    }
  };

  const confirmDelete = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await ShopApi.deleteItem(deleteTarget.id);
      toast.show(`"${deleteTarget.name}" removed.`, "info");
      setDeleteTarget(null);
      await load();
    } catch (e) {
      toast.show(e instanceof Error ? e.message : "Could not remove item.", "error");
    } finally {
      setDeleting(false);
    }
  };

  const openItemForm = (itemId?: string) => {
    if (!shop) return;
    router.push({
      pathname: "/(tabs)/realm/shop-item",
      params: itemId ? { shopId: shop.id, itemId } : { shopId: shop.id },
    });
  };

  return (
    <SafeAreaView style={styles.safe} edges={["top"]} testID={SHOP.manageScreen}>
      <Header title="My Shop" subtitle="Manage your wares" showBack />

      {status === "loading" ? (
        <Loading label="Opening the ledger…" />
      ) : status === "error" ? (
        <ErrorView message="Could not load your shop." onRetry={load} />
      ) : status === "none" ? (
        <KeyboardAvoidingView
          style={styles.flex}
          behavior={Platform.OS === "ios" ? "padding" : undefined}
        >
          <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
            <View style={styles.introCard} testID={SHOP.createForm}>
              <View style={styles.introIcon}>
                <Ionicons name="storefront" size={30} color={colors.gold} />
              </View>
              <Text style={styles.introTitle}>Open your own shop</Text>
              <Text style={styles.introSub}>
                Sell gear to fellow adventurers in the marketplace.
              </Text>

              <TextField
                testID={SHOP.createName}
                label="Shop name"
                value={form.name}
                onChangeText={(v) => setForm({ ...form, name: v })}
                placeholder="e.g., The Dragon's Hoard"
              />
              <TextField
                testID={SHOP.createDescription}
                label="Description"
                value={form.description}
                onChangeText={(v) => setForm({ ...form, description: v })}
                placeholder="Describe your shop…"
                multiline
                numberOfLines={4}
              />
              <PickerField
                testID={SHOP.createNation}
                label="Nation"
                value={form.nation}
                onSelect={(v) => setForm({ ...form, nation: v })}
                options={CREATE_NATIONS.map((n) => ({ label: n, value: n }))}
              />
              <Button
                title="Create shop"
                icon="add-circle-outline"
                onPress={createShop}
                loading={creating}
                testID={SHOP.createSubmit}
                style={styles.createBtn}
              />
            </View>
          </ScrollView>
        </KeyboardAvoidingView>
      ) : (
        <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
          <View style={styles.shopHeader}>
            <Text style={styles.shopName}>{shop?.name}</Text>
            <Text style={styles.shopDesc}>{shop?.description}</Text>
            <Pill label={shop?.nation ?? ""} color={colors.gold} style={styles.shopNation} />
          </View>

          <Button
            title="Add item"
            icon="add"
            onPress={() => openItemForm()}
            testID={SHOP.addItemButton}
            style={styles.addBtn}
          />

          <Text style={styles.sectionLabel}>Your items ({items.length})</Text>
          {items.length === 0 ? (
            <Text style={styles.hint}>No items yet. Add your first ware to start selling.</Text>
          ) : (
            items.map((item) => {
              const out = item.stock <= 0;
              return (
                <View key={item.id} testID={`${SHOP.itemCard}-${item.id}`} style={styles.itemCard}>
                  <View style={styles.itemHead}>
                    <Text style={styles.itemName} numberOfLines={1}>
                      {item.name}
                    </Text>
                    <Text style={styles.itemPrice}>{item.price} g</Text>
                  </View>
                  <Text style={styles.itemDesc} numberOfLines={2}>
                    {item.description}
                  </Text>
                  <View style={styles.itemMeta}>
                    {item.category ? <Pill label={item.category} color={colors.textMuted} /> : null}
                    <Pill
                      label={out ? "Out of stock" : `${item.stock} in stock`}
                      color={out ? colors.rose : colors.green}
                    />
                    {item.is_auto_priced ? (
                      <Pill label="Auto-priced" color={colors.gold} icon="sparkles" />
                    ) : null}
                  </View>
                  <View style={styles.itemActions}>
                    <Button
                      title="Edit"
                      icon="create-outline"
                      variant="secondary"
                      onPress={() => openItemForm(item.id)}
                      testID={`${SHOP.editItemButton}-${item.id}`}
                      style={styles.itemActionBtn}
                    />
                    <Button
                      title="Remove"
                      icon="trash-outline"
                      variant="danger"
                      onPress={() => setDeleteTarget(item)}
                      testID={`${SHOP.deleteItemButton}-${item.id}`}
                      style={styles.itemActionBtn}
                    />
                  </View>
                </View>
              );
            })
          )}

          {customers.length > 0 ? (
            <>
              <Text style={styles.sectionLabel}>Recent customers</Text>
              <View style={styles.customers}>
                {customers.slice(0, 8).map((c, idx) => (
                  <View key={`${c.customer_name}-${idx}`} style={styles.customerRow}>
                    <Ionicons name="person-outline" size={15} color={colors.textSecondary} />
                    <Text style={styles.customerText} numberOfLines={1}>
                      <Text style={styles.customerName}>{c.customer_name}</Text> bought {c.units}×{" "}
                      {c.item_name}
                    </Text>
                  </View>
                ))}
              </View>
            </>
          ) : null}
        </ScrollView>
      )}

      {/* Delete confirm */}
      <Modal
        visible={!!deleteTarget}
        transparent
        animationType="fade"
        onRequestClose={() => setDeleteTarget(null)}
      >
        <Pressable style={styles.backdrop} onPress={() => setDeleteTarget(null)}>
          <Pressable style={styles.confirmSheet} onPress={() => {}}>
            <Ionicons name="warning-outline" size={28} color={colors.rose} />
            <Text style={styles.confirmTitle}>Remove item</Text>
            <Text style={styles.confirmText}>
              Permanently remove &ldquo;{deleteTarget?.name}&rdquo; from your shop?
            </Text>
            <View style={styles.confirmActions}>
              <Button
                title="Cancel"
                variant="ghost"
                onPress={() => setDeleteTarget(null)}
                style={styles.confirmBtn}
                testID="shop-delete-cancel"
              />
              <Button
                title="Remove"
                variant="danger"
                onPress={confirmDelete}
                loading={deleting}
                style={styles.confirmBtn}
                testID="shop-delete-confirm"
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
  flex: { flex: 1 },
  content: { padding: spacing.md, paddingBottom: spacing.xxl },
  introCard: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.lg,
    padding: spacing.lg,
  },
  introIcon: {
    width: 60,
    height: 60,
    borderRadius: 30,
    alignSelf: "center",
    backgroundColor: colors.goldDim,
    borderWidth: 1,
    borderColor: colors.goldBorder,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: spacing.md,
  },
  introTitle: { ...typography.h1, color: colors.textPrimary, textAlign: "center" },
  introSub: {
    ...typography.small,
    color: colors.textSecondary,
    textAlign: "center",
    marginTop: spacing.xs,
    marginBottom: spacing.lg,
  },
  createBtn: { marginTop: spacing.sm },
  shopHeader: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.goldBorder,
    borderRadius: radius.lg,
    padding: spacing.md,
  },
  shopName: { ...typography.h1, color: colors.gold },
  shopDesc: { ...typography.body, color: colors.textSecondary, marginTop: spacing.xs },
  shopNation: { marginTop: spacing.sm },
  addBtn: { marginTop: spacing.md },
  sectionLabel: {
    ...typography.tiny,
    color: colors.gold,
    textTransform: "uppercase",
    letterSpacing: 1,
    marginTop: spacing.xl,
    marginBottom: spacing.md,
  },
  hint: { ...typography.small, color: colors.textMuted },
  itemCard: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.lg,
    padding: spacing.md,
    marginBottom: spacing.md,
  },
  itemHead: { flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  itemName: { ...typography.h3, color: colors.textPrimary, flex: 1, marginRight: spacing.sm },
  itemPrice: { ...typography.h3, color: colors.gold },
  itemDesc: { ...typography.small, color: colors.textSecondary, marginTop: 4 },
  itemMeta: { flexDirection: "row", flexWrap: "wrap", gap: spacing.sm, marginTop: spacing.sm },
  itemActions: { flexDirection: "row", gap: spacing.sm, marginTop: spacing.md },
  itemActionBtn: { flex: 1, minHeight: 42 },
  customers: { gap: spacing.sm },
  customerRow: { flexDirection: "row", alignItems: "center", gap: spacing.sm },
  customerText: { ...typography.small, color: colors.textSecondary, flex: 1 },
  customerName: { color: colors.textPrimary, fontWeight: "700" },
  backdrop: { flex: 1, backgroundColor: colors.overlay, justifyContent: "center", padding: spacing.lg },
  confirmSheet: {
    backgroundColor: colors.bgElevated,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.border,
    padding: spacing.lg,
    alignItems: "center",
  },
  confirmTitle: { ...typography.h2, color: colors.textPrimary, marginTop: spacing.sm },
  confirmText: {
    ...typography.body,
    color: colors.textSecondary,
    textAlign: "center",
    marginTop: spacing.xs,
  },
  confirmActions: { flexDirection: "row", gap: spacing.sm, marginTop: spacing.lg, alignSelf: "stretch" },
  confirmBtn: { flex: 1 },
});
