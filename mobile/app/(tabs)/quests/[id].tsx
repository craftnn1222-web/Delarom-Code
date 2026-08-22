import { Ionicons } from "@expo/vector-icons";
import { useLocalSearchParams } from "expo-router";
import { useCallback, useEffect, useState } from "react";
import { ScrollView, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { QUESTS } from "@/constants/testIds";
import { Quest, QuestApi } from "@/src/api";
import { Button } from "@/src/components/Button";
import { Header } from "@/src/components/Header";
import { difficultyColor, Pill } from "@/src/components/Pill";
import { ErrorView, Loading } from "@/src/components/StateViews";
import { useToast } from "@/src/components/Toast";
import { useActiveCharacter } from "@/src/hooks/useActiveCharacter";
import { colors, radius, spacing, typography } from "@/src/theme/theme";

export default function QuestDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const toast = useToast();
  const { character, noHero } = useActiveCharacter();
  const [quest, setQuest] = useState<Quest | null>(null);
  const [accepted, setAccepted] = useState(false);
  const [status, setStatus] = useState<"loading" | "error" | "ready">("loading");
  const [accepting, setAccepting] = useState(false);

  const load = useCallback(async () => {
    if (!id) return;
    setStatus("loading");
    try {
      const [q, mine] = await Promise.all([QuestApi.get(id), QuestApi.myAccepted()]);
      setQuest(q);
      setAccepted(mine.some((m) => m.quest.id === id));
      setStatus("ready");
    } catch {
      setStatus("error");
    }
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  const accept = async () => {
    if (!quest || !character) return;
    setAccepting(true);
    try {
      await QuestApi.accept(quest.id, character.id);
      setAccepted(true);
      toast.show(`${character.name} accepted "${quest.title}"`, "success");
    } catch (e) {
      toast.show(e instanceof Error ? e.message : "Could not accept — try again.", "error");
    } finally {
      setAccepting(false);
    }
  };

  const isFull = quest ? quest.current_acceptors >= quest.max_acceptors : false;

  return (
    <SafeAreaView style={styles.safe} edges={["top"]} testID={QUESTS.detailScreen}>
      <Header title="Quest" showBack />
      {status === "loading" ? (
        <Loading label="Unrolling the contract…" />
      ) : status === "error" || !quest ? (
        <ErrorView message="Could not load this quest." onRetry={load} />
      ) : (
        <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
          <Text style={styles.title}>{quest.title}</Text>
          <View style={styles.badges}>
            <Pill label={quest.difficulty} color={difficultyColor(quest.difficulty)} />
            <Pill label={quest.nation} color={colors.textMuted} />
            {quest.category ? <Pill label={quest.category} color={colors.violetSoft} /> : null}
          </View>

          <Text style={styles.body}>{quest.description}</Text>

          <View style={styles.rewardCard}>
            <Text style={styles.sectionLabel}>Rewards</Text>
            <View style={styles.rewardRow}>
              <Ionicons name="cash-outline" size={18} color={colors.gold} />
              <Text style={styles.rewardText}>{quest.reward_currency} gold</Text>
            </View>
            <View style={styles.rewardRow}>
              <Ionicons name="star-outline" size={18} color={colors.violetSoft} />
              <Text style={styles.rewardText}>{quest.reward_xp} XP</Text>
            </View>
            {quest.reward_items?.map((it) => (
              <View key={it.name} style={styles.rewardRow}>
                <Ionicons name="cube-outline" size={18} color={colors.textSecondary} />
                <Text style={styles.rewardText}>{it.name}</Text>
              </View>
            ))}
          </View>

          <View style={styles.slots}>
            <Ionicons name="people-outline" size={16} color={colors.textSecondary} />
            <Text style={styles.slotsText}>
              {quest.current_acceptors} / {quest.max_acceptors} adventurers enrolled
            </Text>
          </View>

          {accepted ? (
            <View style={styles.acceptedBanner}>
              <Ionicons name="checkmark-circle" size={18} color={colors.green} />
              <Text style={styles.acceptedText}>You&apos;ve accepted this quest</Text>
            </View>
          ) : noHero ? (
            <Text style={styles.hint}>Create a hero before accepting quests.</Text>
          ) : isFull ? (
            <Text style={styles.hint}>This quest is full.</Text>
          ) : (
            <Button
              title={character ? `Accept as ${character.name}` : "Accept quest"}
              icon="hand-right-outline"
              onPress={accept}
              loading={accepting}
              disabled={!character}
              testID={QUESTS.acceptButton}
              style={styles.accept}
            />
          )}
        </ScrollView>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.bg },
  content: { padding: spacing.md, paddingBottom: spacing.xxl },
  title: { ...typography.h1, color: colors.textPrimary },
  badges: { flexDirection: "row", flexWrap: "wrap", gap: spacing.sm, marginTop: spacing.sm },
  body: { ...typography.body, color: colors.textSecondary, lineHeight: 22, marginTop: spacing.lg },
  rewardCard: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.goldBorder,
    borderRadius: radius.lg,
    padding: spacing.md,
    marginTop: spacing.lg,
    gap: spacing.sm,
  },
  sectionLabel: {
    ...typography.tiny,
    color: colors.gold,
    textTransform: "uppercase",
    letterSpacing: 1,
    marginBottom: 4,
  },
  rewardRow: { flexDirection: "row", alignItems: "center", gap: spacing.sm },
  rewardText: { ...typography.body, color: colors.textPrimary },
  slots: { flexDirection: "row", alignItems: "center", gap: 6, marginTop: spacing.lg },
  slotsText: { ...typography.small, color: colors.textSecondary },
  acceptedBanner: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    marginTop: spacing.xl,
    padding: spacing.md,
    borderRadius: radius.md,
    backgroundColor: colors.greenDim,
    borderWidth: 1,
    borderColor: colors.green,
  },
  acceptedText: { ...typography.bodyStrong, color: colors.green },
  hint: { ...typography.small, color: colors.textMuted, marginTop: spacing.xl, textAlign: "center" },
  accept: { marginTop: spacing.xl },
});
