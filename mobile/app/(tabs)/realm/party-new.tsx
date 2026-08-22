import { Ionicons } from "@expo/vector-icons";
import { router } from "expo-router";
import { useState } from "react";
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

import { PARTIES } from "@/constants/testIds";
import { PartyApi } from "@/src/api";
import { Button } from "@/src/components/Button";
import { Header } from "@/src/components/Header";
import { TextField } from "@/src/components/TextField";
import { useActiveCharacter } from "@/src/hooks/useActiveCharacter";
import { colors, radius, spacing, typography } from "@/src/theme/theme";

export default function NewPartyScreen() {
  const { character, noHero, loading } = useActiveCharacter();
  const [name, setName] = useState("");
  const [location, setLocation] = useState("");
  const [scene, setScene] = useState("");
  const [maxMembers, setMaxMembers] = useState(6);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const submit = async () => {
    if (!character) {
      setError("You need a hero to host a party.");
      return;
    }
    if (name.trim().length < 3) {
      setError("Give your party a name (3+ characters).");
      return;
    }
    if (location.trim().length < 2) {
      setError("Where does the scene take place?");
      return;
    }
    if (scene.trim().length < 20) {
      setError("Describe the opening scene (at least 20 characters).");
      return;
    }
    setError(null);
    setSaving(true);
    try {
      const party = await PartyApi.create({
        name: name.trim(),
        location: location.trim(),
        scene_description: scene.trim(),
        host_character_id: character.id,
        max_members: maxMembers,
      });
      router.replace({ pathname: "/(tabs)/realm/party", params: { id: party.id } });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not create party.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <SafeAreaView style={styles.safe} edges={["top"]} testID={PARTIES.createScreen}>
      <Header title="Host a Party" showBack />
      <KeyboardAvoidingView style={styles.flex} behavior={Platform.OS === "ios" ? "padding" : undefined}>
        <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled" showsVerticalScrollIndicator={false}>
          {!loading && noHero ? (
            <Text style={styles.warn}>Create a hero first — the host leads with a character.</Text>
          ) : character ? (
            <View style={styles.hostRow}>
              <Ionicons name="star" size={14} color={colors.gold} />
              <Text style={styles.hostText}>Hosting as {character.name}</Text>
            </View>
          ) : null}

          <TextField
            label="Party name"
            value={name}
            onChangeText={setName}
            placeholder="The Hunt for the Ember Crown"
            autoCapitalize="words"
            testID={PARTIES.nameInput}
          />
          <TextField
            label="Location"
            value={location}
            onChangeText={setLocation}
            placeholder="The Silver Moon Inn, Wymroost"
            testID={PARTIES.locationInput}
          />
          <TextField
            label="Opening scene"
            value={scene}
            onChangeText={setScene}
            placeholder="Set the stage for your fellowship…"
            multiline
            numberOfLines={5}
            testID={PARTIES.sceneInput}
            error={error}
          />

          <Text style={styles.fieldLabel}>Max members</Text>
          <View style={styles.stepper}>
            <TouchableOpacity
              style={styles.stepBtn}
              onPress={() => setMaxMembers((m) => Math.max(2, m - 1))}
            >
              <Ionicons name="remove" size={20} color={colors.textPrimary} />
            </TouchableOpacity>
            <Text style={styles.stepNum}>{maxMembers}</Text>
            <TouchableOpacity
              style={styles.stepBtn}
              onPress={() => setMaxMembers((m) => Math.min(8, m + 1))}
            >
              <Ionicons name="add" size={20} color={colors.textPrimary} />
            </TouchableOpacity>
          </View>

          <Button
            title="Create party"
            onPress={submit}
            loading={saving}
            disabled={noHero}
            testID={PARTIES.createSubmit}
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
  warn: { ...typography.small, color: colors.rose, marginBottom: spacing.md },
  hostRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    alignSelf: "flex-start",
    marginBottom: spacing.md,
    paddingHorizontal: spacing.md,
    paddingVertical: 6,
    borderRadius: radius.pill,
    backgroundColor: colors.goldDim,
    borderWidth: 1,
    borderColor: colors.goldBorder,
  },
  hostText: { ...typography.small, color: colors.goldSoft, fontWeight: "600" },
  fieldLabel: {
    ...typography.small,
    color: colors.textSecondary,
    fontWeight: "600",
    marginBottom: spacing.sm,
  },
  stepper: { flexDirection: "row", alignItems: "center", gap: spacing.lg, marginBottom: spacing.lg },
  stepBtn: {
    width: 40,
    height: 40,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: colors.borderStrong,
    alignItems: "center",
    justifyContent: "center",
  },
  stepNum: { ...typography.h2, color: colors.gold, minWidth: 30, textAlign: "center" },
  submit: { marginTop: spacing.sm },
});
