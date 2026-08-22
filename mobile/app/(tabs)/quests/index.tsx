import { Ionicons } from "@expo/vector-icons";
import { router, useFocusEffect } from "expo-router";
import { useCallback, useState } from "react";
import { FlatList, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { QUESTS } from "@/constants/testIds";
import { AcceptedQuest, Quest, QuestApi } from "@/src/api";
import { Header } from "@/src/components/Header";
import { difficultyColor, Pill } from "@/src/components/Pill";
import { EmptyState, ErrorView, Loading } from "@/src/components/StateViews";
import { colors, radius, spacing, typography } from "@/src/theme/theme";

type Tab = "board" | "mine";

export default function QuestsScreen() {
  const [tab, setTab] = useState<Tab>("board");
  const [board, setBoard] = useState<Quest[]>([]);
  const [mine, setMine] = useState<AcceptedQuest[]>([]);
  const [status, setStatus] = useState<"loading" | "error" | "ready">("loading");

  const load = useCallback(async (which: Tab) => {
    setStatus("loading");
    try {
      if (which === "board") {
        setBoard(await QuestApi.list("open"));
      } else {
        setMine(await QuestApi.myAccepted());
      }
      setStatus("ready");
    } catch {
      setStatus("error");
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      load(tab);
    }, [load, tab]),
  );

  const switchTab = (next: Tab) => {
    setTab(next);
    load(next);
  };

  return (
    <SafeAreaView style={styles.safe} edges={["top"]} testID={QUESTS.screen}>
      <Header title="Quest Board" subtitle="Take up a calling" />

      <View style={styles.segment}>
        <SegBtn
          label="Open Quests"
          active={tab === "board"}
          onPress={() => switchTab("board")}
          testID={QUESTS.boardToggle}
        />
        <SegBtn
          label="My Quests"
          active={tab === "mine"}
          onPress={() => switchTab("mine")}
          testID={QUESTS.mineToggle}
        />
      </View>

      {status === "loading" ? (
        <Loading label="Consulting the board…" />
      ) : status === "error" ? (
        <ErrorView message="Could not load quests." onRetry={() => load(tab)} />
      ) : tab === "board" ? (
        board.length === 0 ? (
          <EmptyState icon="ribbon-outline" title="No open quests" subtitle="Check back soon." />
        ) : (
          <FlatList
            data={board}
            keyExtractor={(q) => q.id}
            contentContainerStyle={styles.list}
            showsVerticalScrollIndicator={false}
            renderItem={({ item }) => (
              <QuestCard quest={item} onPress={() => router.push({ pathname: "/(tabs)/quests/[id]", params: { id: item.id } })} />
            )}
          />
        )
      ) : mine.length === 0 ? (
        <EmptyState
          icon="bookmark-outline"
          title="No quests accepted"
          subtitle="Accept a quest from the board to see it here."
        />
      ) : (
        <FlatList
          data={mine}
          keyExtractor={(m) => m.acceptance.id}
          contentContainerStyle={styles.list}
          showsVerticalScrollIndicator={false}
          renderItem={({ item }) => (
            <QuestCard
              quest={item.quest}
              acceptanceStatus={item.acceptance.status}
              onPress={() =>
                router.push({ pathname: "/(tabs)/quests/[id]", params: { id: item.quest.id } })
              }
            />
          )}
        />
      )}
    </SafeAreaView>
  );
}

const SegBtn = ({
  label,
  active,
  onPress,
  testID,
}: {
  label: string;
  active: boolean;
  onPress: () => void;
  testID: string;
}) => (
  <TouchableOpacity
    testID={testID}
    style={[styles.segBtn, active && styles.segBtnActive]}
    onPress={onPress}
    activeOpacity={0.85}
  >
    <Text style={[styles.segText, active && styles.segTextActive]}>{label}</Text>
  </TouchableOpacity>
);

const QuestCard = ({
  quest,
  acceptanceStatus,
  onPress,
}: {
  quest: Quest;
  acceptanceStatus?: string;
  onPress: () => void;
}) => (
  <TouchableOpacity testID={QUESTS.card} style={styles.card} activeOpacity={0.85} onPress={onPress}>
    <View style={styles.cardHead}>
      <Text style={styles.title} numberOfLines={1}>
        {quest.title}
      </Text>
      <Ionicons name="chevron-forward" size={18} color={colors.textMuted} />
    </View>
    <Text style={styles.desc} numberOfLines={2}>
      {quest.description}
    </Text>
    <View style={styles.badges}>
      <Pill label={quest.difficulty} color={difficultyColor(quest.difficulty)} />
      <Pill label={quest.nation} color={colors.textMuted} />
      {acceptanceStatus ? (
        <Pill
          label={acceptanceStatus}
          color={acceptanceStatus === "completed" ? colors.green : colors.gold}
          icon={acceptanceStatus === "completed" ? "checkmark-circle" : "time"}
        />
      ) : null}
    </View>
    <View style={styles.rewards}>
      <View style={styles.reward}>
        <Ionicons name="cash-outline" size={14} color={colors.gold} />
        <Text style={styles.rewardText}>{quest.reward_currency} g</Text>
      </View>
      <View style={styles.reward}>
        <Ionicons name="star-outline" size={14} color={colors.violetSoft} />
        <Text style={styles.rewardText}>{quest.reward_xp} XP</Text>
      </View>
      <View style={styles.reward}>
        <Ionicons name="people-outline" size={14} color={colors.textSecondary} />
        <Text style={styles.rewardText}>
          {quest.current_acceptors}/{quest.max_acceptors}
        </Text>
      </View>
    </View>
  </TouchableOpacity>
);

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.bg },
  segment: {
    flexDirection: "row",
    margin: spacing.md,
    padding: 4,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.pill,
  },
  segBtn: { flex: 1, paddingVertical: 8, borderRadius: radius.pill, alignItems: "center" },
  segBtnActive: { backgroundColor: colors.goldDim },
  segText: { ...typography.small, color: colors.textSecondary, fontWeight: "600" },
  segTextActive: { color: colors.goldSoft },
  list: { paddingHorizontal: spacing.md, paddingBottom: spacing.xxl, gap: spacing.md },
  card: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.lg,
    padding: spacing.md,
  },
  cardHead: { flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  title: { ...typography.h3, color: colors.textPrimary, flex: 1, marginRight: spacing.sm },
  desc: { ...typography.small, color: colors.textSecondary, marginTop: 4 },
  badges: { flexDirection: "row", flexWrap: "wrap", gap: spacing.sm, marginTop: spacing.sm },
  rewards: {
    flexDirection: "row",
    gap: spacing.lg,
    marginTop: spacing.md,
    paddingTop: spacing.sm,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: colors.border,
  },
  reward: { flexDirection: "row", alignItems: "center", gap: 4 },
  rewardText: { ...typography.small, color: colors.textPrimary },
});
