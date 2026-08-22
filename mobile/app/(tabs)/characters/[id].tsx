import { Ionicons } from "@expo/vector-icons";
import { router, useLocalSearchParams } from "expo-router";
import * as ImagePicker from "expo-image-picker";
import { useCallback, useEffect, useState } from "react";
import { Alert, Linking, ScrollView, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { CHARACTERS } from "@/constants/testIds";
import { Character, CharacterApi } from "@/src/api";
import { Button } from "@/src/components/Button";
import { Portrait, StatGrid, XpBar } from "@/src/components/CharacterBits";
import { Header } from "@/src/components/Header";
import { ErrorView, Loading } from "@/src/components/StateViews";
import { colors, radius, spacing, typography } from "@/src/theme/theme";

export default function CharacterDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const [character, setCharacter] = useState<Character | null>(null);
  const [status, setStatus] = useState<"loading" | "error" | "ready">("loading");
  const [uploading, setUploading] = useState(false);

  const load = useCallback(async () => {
    if (!id) return;
    setStatus("loading");
    try {
      const data = await CharacterApi.get(id);
      setCharacter(data);
      setStatus("ready");
    } catch {
      setStatus("error");
    }
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  const changePortrait = async () => {
    if (!id) return;
    const current = await ImagePicker.getMediaLibraryPermissionsAsync();
    let granted = current.granted;
    let canAskAgain = current.canAskAgain;

    if (!granted) {
      const req = await ImagePicker.requestMediaLibraryPermissionsAsync();
      granted = req.granted;
      canAskAgain = req.canAskAgain;
    }

    if (!granted) {
      if (!canAskAgain) {
        Alert.alert(
          "Photo access needed",
          "To set a portrait, enable photo access for Delarom in Settings.",
          [
            { text: "Not now", style: "cancel" },
            { text: "Open Settings", onPress: () => Linking.openSettings() },
          ],
        );
      } else {
        Alert.alert("Photo access needed", "We need access to your photos to set a portrait.");
      }
      return;
    }

    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ["images"],
      allowsEditing: true,
      aspect: [1, 1],
      quality: 0.7,
    });
    if (result.canceled) return;

    const asset = result.assets[0];
    const name = asset.uri.split("/").pop() || "portrait.jpg";
    const ext = /\.(\w+)$/.exec(name)?.[1]?.toLowerCase() || "jpg";
    const type = `image/${ext === "jpg" ? "jpeg" : ext}`;

    const form = new FormData();
    // React Native FormData file part
    form.append("file", { uri: asset.uri, name, type } as unknown as Blob);

    setUploading(true);
    try {
      const res = await CharacterApi.uploadImage(id, form);
      setCharacter((c) => (c ? { ...c, portrait_url: res.portrait_url } : c));
    } catch (e) {
      Alert.alert("Upload failed", e instanceof Error ? e.message : "Please try again.");
    } finally {
      setUploading(false);
    }
  };

  return (
    <SafeAreaView style={styles.safe} edges={["top"]} testID={CHARACTERS.detailScreen}>
      <Header title={character?.name ?? "Hero"} showBack subtitle={character?.nation} />

      {status === "loading" ? (
        <Loading label="Reading the annals…" />
      ) : status === "error" || !character ? (
        <ErrorView message="Could not load this hero." onRetry={load} />
      ) : (
        <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
          <View style={styles.hero}>
            <Portrait uri={character.portrait_url} name={character.name} size={112} />
            <Text style={styles.name}>{character.name}</Text>
            <Text style={styles.meta}>
              {character.race} · {character.character_class}
            </Text>
            <TouchableOpacity
              testID={CHARACTERS.changePortraitButton}
              style={styles.portraitBtn}
              onPress={changePortrait}
              disabled={uploading}
            >
              <Ionicons name="image-outline" size={16} color={colors.violetSoft} />
              <Text style={styles.portraitBtnText}>
                {uploading ? "Uploading…" : "Change portrait"}
              </Text>
            </TouchableOpacity>
          </View>

          <View style={styles.block}>
            <XpBar
              level={character.level}
              xp={character.xp}
              xpToNext={character.xp_to_next_level}
            />
          </View>

          <SectionLabel icon="stats-chart-outline" label="Attributes" />
          <View style={styles.block}>
            <StatGrid character={character} />
          </View>

          <Section title="Appearance" icon="eye-outline" body={character.appearance} />
          <Section title="Powers" icon="flame-outline" body={character.powers} />
          <Section title="Backstory" icon="book-outline" body={character.backstory} />

          <Button
            title="Enter the world to roleplay"
            icon="map-outline"
            onPress={() => router.push("/(tabs)/world")}
            style={styles.cta}
          />
        </ScrollView>
      )}
    </SafeAreaView>
  );
}

const SectionLabel = ({
  icon,
  label,
}: {
  icon: keyof typeof Ionicons.glyphMap;
  label: string;
}) => (
  <View style={styles.sectionLabel}>
    <Ionicons name={icon} size={16} color={colors.gold} />
    <Text style={styles.sectionLabelText}>{label}</Text>
  </View>
);

const Section = ({
  title,
  icon,
  body,
}: {
  title: string;
  icon: keyof typeof Ionicons.glyphMap;
  body?: string;
}) => {
  if (!body?.trim()) return null;
  return (
    <>
      <SectionLabel icon={icon} label={title} />
      <View style={styles.block}>
        <Text style={styles.bodyText}>{body}</Text>
      </View>
    </>
  );
};

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.bg },
  content: { padding: spacing.md, paddingBottom: spacing.xxl },
  hero: { alignItems: "center", marginBottom: spacing.lg },
  name: { ...typography.h1, color: colors.textPrimary, marginTop: spacing.md, textAlign: "center" },
  meta: { ...typography.body, color: colors.textSecondary, marginTop: 2 },
  portraitBtn: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    marginTop: spacing.md,
    paddingHorizontal: spacing.md,
    paddingVertical: 8,
    borderRadius: radius.pill,
    borderWidth: 1,
    borderColor: colors.violetBorder,
    backgroundColor: colors.violetDim,
  },
  portraitBtnText: { ...typography.small, color: colors.violetSoft, fontWeight: "600" },
  block: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.lg,
    padding: spacing.md,
    marginBottom: spacing.md,
  },
  sectionLabel: { flexDirection: "row", alignItems: "center", gap: 8, marginBottom: spacing.sm },
  sectionLabelText: {
    ...typography.tiny,
    color: colors.gold,
    textTransform: "uppercase",
    letterSpacing: 1,
  },
  bodyText: { ...typography.body, color: colors.textSecondary, lineHeight: 22 },
  cta: { marginTop: spacing.sm },
});
