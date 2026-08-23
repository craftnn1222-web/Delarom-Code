import { router, useLocalSearchParams } from "expo-router";
import { useState } from "react";
import { KeyboardAvoidingView, Platform, ScrollView, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { FACTIONS } from "@/constants/testIds";
import { FactionApi } from "@/src/api";
import { Button } from "@/src/components/Button";
import { Header } from "@/src/components/Header";
import { TextField } from "@/src/components/TextField";
import { useToast } from "@/src/components/Toast";
import { useActiveCharacter } from "@/src/hooks/useActiveCharacter";
import { colors, spacing, typography } from "@/src/theme/theme";

export default function NewFactionThreadScreen() {
  const { slug, name } = useLocalSearchParams<{ slug: string; name: string }>();
  const toast = useToast();
  const { character } = useActiveCharacter();

  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [saving, setSaving] = useState(false);

  const canSubmit = title.trim().length >= 2 && content.trim().length >= 1 && !!character;

  const submit = async () => {
    if (!character) {
      toast.show("You need an active hero in this faction to post.", "error");
      return;
    }
    if (!canSubmit) return;
    setSaving(true);
    try {
      await FactionApi.createThread(slug, {
        character_id: character.id,
        title: title.trim(),
        content: content.trim(),
      });
      toast.show("Thread posted to the hall.", "success");
      router.back();
    } catch (e) {
      toast.show(e instanceof Error ? e.message : "Could not post the thread.", "error");
    } finally {
      setSaving(false);
    }
  };

  return (
    <SafeAreaView style={styles.safe} edges={["top"]} testID={FACTIONS.newThreadScreen}>
      <Header title="New Thread" subtitle={name ?? "Faction hall"} showBack />
      <KeyboardAvoidingView
        style={styles.flex}
        behavior={Platform.OS === "ios" ? "padding" : undefined}
        keyboardVerticalOffset={Platform.OS === "ios" ? 8 : 0}
      >
        <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false} keyboardShouldPersistTaps="handled">
          {character ? (
            <View style={styles.asRow}>
              <Text style={styles.asText}>
                Posting as <Text style={styles.asName}>{character.name}</Text>
              </Text>
            </View>
          ) : (
            <Text style={styles.warn}>Set an active hero who belongs to this faction to post.</Text>
          )}

          <TextField
            testID={FACTIONS.threadTitleInput}
            label="Title"
            value={title}
            onChangeText={setTitle}
            placeholder="What is this about?"
            autoCapitalize="sentences"
          />
          <TextField
            testID={FACTIONS.threadContentInput}
            label="Message"
            value={content}
            onChangeText={setContent}
            placeholder="Share your plans, muster the ranks, or open a debate…"
            multiline
            numberOfLines={8}
          />

          <Button
            title="Post thread"
            icon="send"
            onPress={submit}
            loading={saving}
            disabled={!canSubmit}
            testID={FACTIONS.threadCreateSubmit}
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
  asRow: { marginBottom: spacing.md },
  asText: { ...typography.small, color: colors.textSecondary },
  asName: { color: colors.goldSoft, fontWeight: "700" },
  warn: { ...typography.small, color: colors.rose, marginBottom: spacing.md },
  submit: { marginTop: spacing.md },
});
