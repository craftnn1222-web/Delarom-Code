import { Ionicons } from "@expo/vector-icons";
import { useCallback, useEffect, useState } from "react";
import { StyleSheet, Text, TouchableOpacity, View } from "react-native";

import { STAFF } from "@/constants/testIds";
import { ShopApi, ShopEmployee } from "@/src/api";
import { Button } from "@/src/components/Button";
import { PickerField } from "@/src/components/PickerField";
import { TextField } from "@/src/components/TextField";
import { useToast } from "@/src/components/Toast";
import { colors, radius, spacing, typography } from "@/src/theme/theme";

const WAGE = 50;
const ROLES: { value: "clerk" | "stocker" | "barker"; label: string; perk: string; icon: keyof typeof Ionicons.glyphMap }[] = [
  { value: "clerk", label: "Clerk", perk: "Draws more NPC customers", icon: "people-outline" },
  { value: "stocker", label: "Stocker", perk: "Waives restock wholesale fee", icon: "cube-outline" },
  { value: "barker", label: "Barker", perk: "Customers buy more per visit", icon: "megaphone-outline" },
];

export function ShopStaffSection({ shopId }: { shopId: string }) {
  const toast = useToast();
  const [employees, setEmployees] = useState<ShopEmployee[]>([]);
  const [busy, setBusy] = useState<string>("");
  const [playerRole, setPlayerRole] = useState<"clerk" | "stocker" | "barker">("clerk");
  const [playerName, setPlayerName] = useState("");

  const load = useCallback(async () => {
    try {
      setEmployees(await ShopApi.employees(shopId));
    } catch {
      /* owner-only; ignore */
    }
  }, [shopId]);

  useEffect(() => {
    load();
  }, [load]);

  const hireNpc = async (role: "clerk" | "stocker" | "barker") => {
    setBusy(role);
    try {
      await ShopApi.hireEmployee(shopId, { role, kind: "npc" });
      toast.show(`Hired an NPC ${role}`, "success");
      await load();
    } catch (e) {
      toast.show(e instanceof Error ? e.message : "Could not hire.", "error");
    } finally {
      setBusy("");
    }
  };

  const hirePlayer = async () => {
    const uname = playerName.trim();
    if (!uname) {
      toast.show("Enter the player's username.", "error");
      return;
    }
    setBusy("player");
    try {
      await ShopApi.hireEmployee(shopId, { role: playerRole, kind: "player", player_username: uname });
      toast.show(`Hired ${uname}.`, "success");
      setPlayerName("");
      await load();
    } catch (e) {
      toast.show(e instanceof Error ? e.message : "Could not hire player.", "error");
    } finally {
      setBusy("");
    }
  };

  const fire = async (emp: ShopEmployee) => {
    setBusy(emp.id);
    try {
      await ShopApi.fireEmployee(shopId, emp.id);
      toast.show(`${emp.name} was let go.`, "info");
      await load();
    } catch (e) {
      toast.show(e instanceof Error ? e.message : "Could not fire.", "error");
    } finally {
      setBusy("");
    }
  };

  return (
    <View testID={STAFF.section}>
      <Text style={styles.sectionLabel}>Employees ({employees.length})</Text>
      <Text style={styles.hint}>
        Each is paid {WAGE}g per cycle — unpaid staff go idle. Player staff pocket their wage.
      </Text>

      <View style={styles.roleGrid}>
        {ROLES.map((r) => (
          <View key={r.value} style={styles.roleCard}>
            <View style={styles.roleHead}>
              <Ionicons name={r.icon} size={16} color={colors.gold} />
              <Text style={styles.roleName}>{r.label}</Text>
            </View>
            <Text style={styles.rolePerk}>{r.perk}</Text>
            <Button
              title={`Hire NPC (${WAGE}g)`}
              variant="secondary"
              loading={busy === r.value}
              onPress={() => hireNpc(r.value)}
              testID={STAFF.hireNpc(r.value)}
              style={styles.roleBtn}
            />
          </View>
        ))}
      </View>

      <View style={styles.playerCard}>
        <Text style={styles.playerTitle}>Put a player on payroll</Text>
        <PickerField
          label="Role"
          value={playerRole}
          options={ROLES.map((r) => ({ label: r.label, value: r.value }))}
          onSelect={(v) => setPlayerRole(v as "clerk" | "stocker" | "barker")}
          testID={STAFF.playerRole}
        />
        <TextField
          label="Player username"
          value={playerName}
          onChangeText={setPlayerName}
          placeholder="e.g. Ausar Veltraus"
          testID={STAFF.playerName}
        />
        <Button
          title="Hire player"
          icon="person-add-outline"
          loading={busy === "player"}
          onPress={hirePlayer}
          testID={STAFF.hirePlayer}
          style={styles.playerBtn}
        />
      </View>

      {employees.length === 0 ? (
        <Text style={styles.hint} testID={STAFF.empty}>
          No staff yet. Hire someone to boost your shop.
        </Text>
      ) : (
        employees.map((emp) => (
          <View key={emp.id} style={styles.empRow} testID={STAFF.employeeRow(emp.id)}>
            <View style={styles.empInfo}>
              <View style={styles.empNameRow}>
                <Text style={styles.empName} numberOfLines={1}>
                  {emp.name}
                </Text>
                <View
                  style={[styles.kindTag, emp.player_user_id ? styles.kindPlayer : styles.kindNpc]}
                  testID={STAFF.employeeKind(emp.id)}
                >
                  <Text style={[styles.kindText, { color: emp.player_user_id ? colors.violetSoft : colors.textSecondary }]}>
                    {emp.player_user_id ? "Player" : "NPC"}
                  </Text>
                </View>
              </View>
              <Text style={styles.empMeta}>
                {emp.role} ·{" "}
                <Text style={{ color: emp.paid_this_cycle ? colors.green : colors.goldSoft }}>
                  {emp.paid_this_cycle ? "Working" : "Awaiting first pay"}
                </Text>{" "}
                · {emp.wage}g/cycle
              </Text>
            </View>
            <TouchableOpacity onPress={() => fire(emp)} disabled={busy === emp.id} testID={STAFF.fire(emp.id)} style={styles.fireBtn}>
              <Ionicons name="close" size={18} color={colors.rose} />
            </TouchableOpacity>
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
  roleGrid: { gap: spacing.sm },
  roleCard: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.goldBorder,
    borderRadius: radius.lg,
    padding: spacing.md,
  },
  roleHead: { flexDirection: "row", alignItems: "center", gap: 6 },
  roleName: { ...typography.bodyStrong, color: colors.textPrimary },
  rolePerk: { ...typography.small, color: colors.textSecondary, marginTop: 2, marginBottom: spacing.sm },
  roleBtn: { minHeight: 42 },
  playerCard: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.violetBorder,
    borderRadius: radius.lg,
    padding: spacing.md,
    marginTop: spacing.md,
    gap: spacing.sm,
  },
  playerTitle: { ...typography.bodyStrong, color: colors.textPrimary },
  playerBtn: { marginTop: spacing.xs },
  empRow: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.md,
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.md,
    marginTop: spacing.sm,
  },
  empInfo: { flex: 1 },
  empNameRow: { flexDirection: "row", alignItems: "center", gap: spacing.sm },
  empName: { ...typography.bodyStrong, color: colors.textPrimary, flexShrink: 1 },
  kindTag: { paddingHorizontal: 6, paddingVertical: 2, borderRadius: radius.sm },
  kindNpc: { backgroundColor: colors.surfaceAlt },
  kindPlayer: { backgroundColor: colors.violetDim },
  kindText: { ...typography.tiny, textTransform: "uppercase" },
  empMeta: { ...typography.small, color: colors.textSecondary, marginTop: 2 },
  fireBtn: { padding: spacing.sm },
});
