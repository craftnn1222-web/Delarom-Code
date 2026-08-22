import { Ionicons } from "@expo/vector-icons";
import { router } from "expo-router";
import { useMemo, useState } from "react";
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

import { CHARACTERS } from "@/constants/testIds";
import { CharacterApi, CREATE_NATIONS } from "@/src/api";
import { Button } from "@/src/components/Button";
import { Header } from "@/src/components/Header";
import { TextField } from "@/src/components/TextField";
import { colors, radius, spacing, typography } from "@/src/theme/theme";

const STAT_KEYS = ["strength", "magic", "agility", "endurance", "charisma", "luck"] as const;
type StatKey = (typeof STAT_KEYS)[number];
const STAT_LABELS: Record<StatKey, string> = {
  strength: "Strength",
  magic: "Magic",
  agility: "Agility",
  endurance: "Endurance",
  charisma: "Charisma",
  luck: "Luck",
};
const TOTAL_POINTS = 60;

export default function NewCharacterScreen() {
  const [name, setName] = useState("");
  const [race, setRace] = useState("");
  const [charClass, setCharClass] = useState("");
  const [nation, setNation] = useState(CREATE_NATIONS[0]);
  const [appearance, setAppearance] = useState("");
  const [powers, setPowers] = useState("");
  const [backstory, setBackstory] = useState("");
  const [stats, setStats] = useState<Record<StatKey, number>>({
    strength: 10,
    magic: 10,
    agility: 10,
    endurance: 10,
    charisma: 10,
    luck: 10,
  });
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const used = useMemo(() => STAT_KEYS.reduce((sum, k) => sum + stats[k], 0), [stats]);
  const remaining = TOTAL_POINTS - used;

  const adjust = (key: StatKey, delta: number) => {
    setStats((prev) => {
      const next = prev[key] + delta;
      if (next < 1 || next > 20) return prev;
      if (delta > 0 && remaining <= 0) return prev;
      return { ...prev, [key]: next };
    });
  };

  const submit = async () => {
    if (!name.trim() || !race.trim() || !charClass.trim()) {
      setError("Name, race, and class are required.");
      return;
    }
    if (remaining !== 0) {
      setError(`Allocate all attribute points (${remaining} remaining).`);
      return;
    }
    setError(null);
    setSaving(true);
    try {
      await CharacterApi.create({
        name: name.trim(),
        race: race.trim(),
        character_class: charClass.trim(),
        nation,
        appearance: appearance.trim(),
        powers: powers.trim(),
        backstory: backstory.trim(),
        ...stats,
      });
      router.back();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not create hero.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <SafeAreaView style={styles.safe} edges={["top"]} testID={CHARACTERS.createScreen}>
      <Header title="Forge a Hero" showBack />
      <KeyboardAvoidingView
        style={styles.flex}
        behavior={Platform.OS === "ios" ? "padding" : undefined}
      >
        <ScrollView
          contentContainerStyle={styles.content}
          keyboardShouldPersistTaps="handled"
          showsVerticalScrollIndicator={false}
        >
          <TextField
            label="Name"
            value={name}
            onChangeText={setName}
            placeholder="Ausar Veltraus"
            autoCapitalize="words"
            testID={CHARACTERS.nameInput}
          />
          <TextField
            label="Race"
            value={race}
            onChangeText={setRace}
            placeholder="Sun Elf, Human, Dwarf…"
            testID={CHARACTERS.raceInput}
          />
          <TextField
            label="Class"
            value={charClass}
            onChangeText={setCharClass}
            placeholder="Battlemage, Ranger, Rogue…"
            testID={CHARACTERS.classInput}
          />

          <Text style={styles.fieldLabel}>Homeland</Text>
          <View style={styles.nationRow}>
            {CREATE_NATIONS.map((n) => {
              const active = n === nation;
              return (
                <TouchableOpacity
                  key={n}
                  testID={`${CHARACTERS.nationOption}-${n}`}
                  style={[styles.nationChip, active && styles.nationChipActive]}
                  onPress={() => setNation(n)}
                >
                  <Text style={[styles.nationChipText, active && styles.nationChipTextActive]}>
                    {n}
                  </Text>
                </TouchableOpacity>
              );
            })}
          </View>

          <View style={styles.pointsHeader}>
            <Text style={styles.fieldLabel}>Attributes</Text>
            <View style={[styles.pointsPill, remaining === 0 && styles.pointsPillDone]}>
              <Text style={[styles.pointsText, remaining === 0 && styles.pointsTextDone]}>
                {remaining} points left
              </Text>
            </View>
          </View>

          <View style={styles.statList}>
            {STAT_KEYS.map((key) => (
              <View key={key} style={styles.statRow}>
                <Text style={styles.statName}>{STAT_LABELS[key]}</Text>
                <View style={styles.stepper}>
                  <TouchableOpacity
                    testID={`${CHARACTERS.statDecrement}-${key}`}
                    style={styles.stepBtn}
                    onPress={() => adjust(key, -1)}
                  >
                    <Ionicons name="remove" size={18} color={colors.textPrimary} />
                  </TouchableOpacity>
                  <Text style={styles.statNum}>{stats[key]}</Text>
                  <TouchableOpacity
                    testID={`${CHARACTERS.statIncrement}-${key}`}
                    style={styles.stepBtn}
                    onPress={() => adjust(key, 1)}
                  >
                    <Ionicons name="add" size={18} color={colors.textPrimary} />
                  </TouchableOpacity>
                </View>
              </View>
            ))}
          </View>

          <TextField
            label="Appearance"
            value={appearance}
            onChangeText={setAppearance}
            placeholder="Describe how they look…"
            multiline
            testID={CHARACTERS.appearanceInput}
          />
          <TextField
            label="Powers"
            value={powers}
            onChangeText={setPowers}
            placeholder="Their abilities and magic…"
            multiline
            testID={CHARACTERS.powersInput}
          />
          <TextField
            label="Backstory"
            value={backstory}
            onChangeText={setBackstory}
            placeholder="Where do they come from?"
            multiline
            testID={CHARACTERS.backstoryInput}
            error={error}
          />

          <Button
            title="Forge hero"
            onPress={submit}
            loading={saving}
            testID={CHARACTERS.createSubmit}
            style={styles.submit}
          />
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.bg },
  flex: { flex: 1 },
  content: { padding: spacing.md, paddingBottom: spacing.xxl },
  fieldLabel: {
    ...typography.small,
    color: colors.textSecondary,
    fontWeight: "600",
    marginBottom: spacing.sm,
  },
  nationRow: { flexDirection: "row", flexWrap: "wrap", gap: spacing.sm, marginBottom: spacing.md },
  nationChip: {
    paddingHorizontal: spacing.md,
    paddingVertical: 8,
    borderRadius: radius.pill,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.surface,
  },
  nationChipActive: { borderColor: colors.goldBorder, backgroundColor: colors.goldDim },
  nationChipText: { ...typography.small, color: colors.textSecondary },
  nationChipTextActive: { color: colors.goldSoft, fontWeight: "700" },
  pointsHeader: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  pointsPill: {
    paddingHorizontal: spacing.md,
    paddingVertical: 4,
    borderRadius: radius.pill,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.surfaceAlt,
  },
  pointsPillDone: { borderColor: colors.greenDim, backgroundColor: colors.greenDim },
  pointsText: { ...typography.tiny, color: colors.textSecondary },
  pointsTextDone: { color: colors.green },
  statList: { marginBottom: spacing.md, gap: spacing.sm },
  statRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.md,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
  },
  statName: { ...typography.body, color: colors.textPrimary },
  stepper: { flexDirection: "row", alignItems: "center", gap: spacing.md },
  stepBtn: {
    width: 34,
    height: 34,
    borderRadius: 17,
    borderWidth: 1,
    borderColor: colors.borderStrong,
    alignItems: "center",
    justifyContent: "center",
  },
  statNum: { ...typography.h3, color: colors.gold, minWidth: 26, textAlign: "center" },
  submit: { marginTop: spacing.sm },
});
