import { Ionicons } from "@expo/vector-icons";
import { router, useLocalSearchParams } from "expo-router";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  ActivityIndicator,
  Keyboard,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { QUESTS } from "@/constants/testIds";
import { Quest, QuestAction, QuestApi } from "@/src/api";
import { Header } from "@/src/components/Header";
import { EmptyState, ErrorView, Loading } from "@/src/components/StateViews";
import { colors, radius, spacing, typography } from "@/src/theme/theme";

export default function QuestPlayScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();

  const [quest, setQuest] = useState<Quest | null>(null);
  const [actions, setActions] = useState<QuestAction[]>([]);
  const [heroName, setHeroName] = useState<string | null>(null);
  const [notAccepted, setNotAccepted] = useState(false);
  const [completed, setCompleted] = useState(false);
  const [status, setStatus] = useState<"loading" | "error" | "ready">("loading");
  const [text, setText] = useState("");
  const [pending, setPending] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  const scrollRef = useRef<ScrollView>(null);

  const load = useCallback(async () => {
    if (!id) return;
    setStatus("loading");
    const [q, hist, mine] = await Promise.allSettled([
      QuestApi.get(id),
      QuestApi.actions(id),
      QuestApi.myAccepted(),
    ]);
    if (q.status === "fulfilled") setQuest(q.value);
    if (hist.status === "fulfilled") setActions(hist.value);
    if (mine.status === "fulfilled") {
      const entry = mine.value.find((m) => m.quest.id === id);
      if (entry) {
        setHeroName(entry.character?.name ?? null);
        setNotAccepted(false);
        setCompleted(entry.acceptance?.status === "completed");
      } else {
        setNotAccepted(true);
      }
    }
    if (q.status === "rejected" && hist.status === "rejected") {
      setStatus("error");
    } else {
      setStatus("ready");
    }
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  const scrollToEnd = useCallback(() => {
    setTimeout(() => scrollRef.current?.scrollToEnd({ animated: true }), 80);
  }, []);

  useEffect(() => {
    if (status === "ready") scrollToEnd();
  }, [actions, pending, status, scrollToEnd]);

  const send = async () => {
    const action = text.trim();
    if (action.length < 3) {
      setNotice("Describe your action in a few words.");
      return;
    }
    setNotice(null);
    setSending(true);
    setPending(action);
    Keyboard.dismiss();
    try {
      await QuestApi.submitAction(id, action);
      const fresh = await QuestApi.actions(id);
      setActions(fresh);
      setText("");
      setPending(null);
    } catch (e) {
      setNotice(e instanceof Error ? e.message : "The Quest Master did not respond. Try again.");
      setPending(null);
    } finally {
      setSending(false);
    }
  };

  const visible = actions.filter((a) => a.action_text || a.ai_response);

  return (
    <SafeAreaView style={styles.safe} edges={["top"]} testID={QUESTS.playScreen}>
      <Header title={quest?.title ?? "Quest"} subtitle={quest ? String(quest.nation) : ""} showBack />

      {status === "loading" ? (
        <Loading label="Unrolling the contract…" />
      ) : status === "error" ? (
        <ErrorView message="Could not enter this quest." onRetry={load} />
      ) : notAccepted ? (
        <EmptyState
          icon="lock-closed-outline"
          title="Accept this quest first"
          subtitle="You need to accept this quest before you can play its scene."
          actionLabel="Back to quest"
          onAction={() => router.back()}
        />
      ) : (
        <KeyboardAvoidingView
          style={styles.flex}
          behavior={Platform.OS === "ios" ? "padding" : undefined}
          keyboardVerticalOffset={Platform.OS === "ios" ? 8 : 0}
        >
          {heroName ? (
            <View style={styles.playingBanner}>
              <Ionicons name="person-circle-outline" size={16} color={colors.gold} />
              <Text style={styles.playingText}>
                Playing as <Text style={styles.playingName}>{heroName}</Text>
              </Text>
            </View>
          ) : null}

          <ScrollView
            ref={scrollRef}
            contentContainerStyle={styles.log}
            showsVerticalScrollIndicator={false}
            onContentSizeChange={scrollToEnd}
          >
            {visible.length === 0 && !pending ? (
              <View style={styles.introWrap}>
                <Ionicons name="book-outline" size={26} color={colors.gold} />
                <Text style={styles.introText}>
                  The Quest Master awaits. Write your first action to begin the tale.
                </Text>
              </View>
            ) : null}

            {visible.map((a) => {
              const isOpening = a.action_text === "[Quest Opening]";
              return (
                <View key={a.id} testID={QUESTS.playLogEntry}>
                  {a.action_text && !isOpening ? (
                    <View style={styles.playerBubble}>
                      <Text style={styles.playerAuthor}>{a.character_name}</Text>
                      <Text style={styles.playerText}>{a.action_text}</Text>
                    </View>
                  ) : null}
                  {a.ai_response ? (
                    <View style={styles.narrationBubble}>
                      <Text style={styles.narrationAuthor}>Quest Master</Text>
                      <Text style={styles.narrationText}>{a.ai_response}</Text>
                    </View>
                  ) : null}
                </View>
              );
            })}

            {pending ? (
              <View>
                <View style={styles.playerBubble}>
                  <Text style={styles.playerAuthor}>{heroName}</Text>
                  <Text style={styles.playerText}>{pending}</Text>
                </View>
                <View style={[styles.narrationBubble, styles.pendingBubble]}>
                  <ActivityIndicator color={colors.violetSoft} size="small" />
                  <Text style={styles.pendingText}>The Quest Master responds…</Text>
                </View>
              </View>
            ) : null}
          </ScrollView>

          {notice ? (
            <View style={styles.notice}>
              <Ionicons name="alert-circle-outline" size={16} color={colors.rose} />
              <Text style={styles.noticeText}>{notice}</Text>
            </View>
          ) : null}

          <View style={styles.inputBar}>
            {completed ? (
              <View style={styles.completedBar}>
                <Ionicons name="checkmark-circle" size={16} color={colors.green} />
                <Text style={styles.completedText}>This quest is complete — the scene is preserved.</Text>
              </View>
            ) : (
              <>
                <TextInput
                  testID={QUESTS.playInput}
                  value={text}
                  onChangeText={setText}
                  placeholder="What do you do?"
                  placeholderTextColor={colors.textMuted}
                  style={styles.input}
                  multiline
                  editable={!sending}
                />
                <TouchableOpacity
                  testID={QUESTS.playSendButton}
                  style={[styles.sendBtn, (sending || text.trim().length < 3) && styles.sendBtnDisabled]}
                  onPress={send}
                  disabled={sending || text.trim().length < 3}
                >
                  {sending ? (
                    <ActivityIndicator color="#1A1206" size="small" />
                  ) : (
                    <Ionicons name="send" size={18} color="#1A1206" />
                  )}
                </TouchableOpacity>
              </>
            )}
          </View>
        </KeyboardAvoidingView>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.bg },
  flex: { flex: 1 },
  playingBanner: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    backgroundColor: colors.goldDim,
    borderBottomWidth: 1,
    borderBottomColor: colors.goldBorder,
  },
  playingText: { ...typography.small, color: colors.textSecondary },
  playingName: { color: colors.goldSoft, fontWeight: "700" },
  log: { padding: spacing.md, paddingBottom: spacing.lg, gap: spacing.md },
  introWrap: { alignItems: "center", padding: spacing.xl, gap: spacing.md },
  introText: { ...typography.body, color: colors.textSecondary, textAlign: "center", lineHeight: 22 },
  playerBubble: {
    alignSelf: "flex-end",
    maxWidth: "88%",
    backgroundColor: colors.goldDim,
    borderWidth: 1,
    borderColor: colors.goldBorder,
    borderRadius: radius.lg,
    borderBottomRightRadius: 4,
    padding: spacing.md,
    marginBottom: spacing.sm,
  },
  playerAuthor: { ...typography.tiny, color: colors.goldSoft, marginBottom: 4, textTransform: "uppercase" },
  playerText: { ...typography.body, color: colors.textPrimary, lineHeight: 21 },
  narrationBubble: {
    alignSelf: "flex-start",
    maxWidth: "94%",
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.lg,
    borderBottomLeftRadius: 4,
    padding: spacing.md,
  },
  narrationAuthor: {
    ...typography.tiny,
    color: colors.violetSoft,
    marginBottom: 4,
    textTransform: "uppercase",
  },
  narrationText: { ...typography.body, color: colors.textSecondary, lineHeight: 22 },
  pendingBubble: { flexDirection: "row", alignItems: "center", gap: spacing.sm },
  pendingText: { ...typography.small, color: colors.violetSoft, fontStyle: "italic" },
  notice: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    marginHorizontal: spacing.md,
    marginBottom: spacing.sm,
    padding: spacing.sm,
    borderRadius: radius.md,
    backgroundColor: colors.roseDim,
    borderWidth: 1,
    borderColor: colors.rose,
  },
  noticeText: { ...typography.small, color: colors.rose, flex: 1 },
  inputBar: {
    flexDirection: "row",
    alignItems: "flex-end",
    gap: spacing.sm,
    paddingHorizontal: spacing.md,
    paddingTop: spacing.sm,
    paddingBottom: Platform.OS === "ios" ? spacing.md : spacing.sm,
    borderTopWidth: 1,
    borderTopColor: colors.border,
    backgroundColor: colors.bgElevated,
  },
  input: {
    flex: 1,
    maxHeight: 120,
    minHeight: 46,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.lg,
    paddingHorizontal: spacing.md,
    paddingTop: 12,
    paddingBottom: 12,
    color: colors.textPrimary,
    fontSize: 15,
  },
  sendBtn: {
    width: 46,
    height: 46,
    borderRadius: 23,
    backgroundColor: colors.gold,
    alignItems: "center",
    justifyContent: "center",
  },
  sendBtnDisabled: { opacity: 0.5 },
  completedBar: { flexDirection: "row", alignItems: "center", gap: 6, flex: 1, paddingVertical: 8 },
  completedText: { ...typography.small, color: colors.green, flex: 1 },
});
