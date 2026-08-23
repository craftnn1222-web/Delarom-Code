import { Ionicons } from "@expo/vector-icons";
import { useLocalSearchParams } from "expo-router";
import { useCallback, useEffect, useState } from "react";
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

import { FACTIONS } from "@/constants/testIds";
import { FactionApi, FactionThread, FactionThreadReply } from "@/src/api";
import { ApiError } from "@/src/api/client";
import { Header } from "@/src/components/Header";
import { EmptyState, ErrorView, Loading } from "@/src/components/StateViews";
import { Pill } from "@/src/components/Pill";
import { useActiveCharacter } from "@/src/hooks/useActiveCharacter";
import { colors, radius, spacing, typography } from "@/src/theme/theme";

const fmt = (iso?: string) => {
  if (!iso) return "";
  try {
    return new Date(iso).toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  } catch {
    return "";
  }
};

export default function FactionThreadScreen() {
  const { slug, threadId, name } = useLocalSearchParams<{
    slug: string;
    threadId: string;
    name: string;
  }>();
  const { character } = useActiveCharacter();

  const [thread, setThread] = useState<FactionThread | null>(null);
  const [replies, setReplies] = useState<FactionThreadReply[]>([]);
  const [isMemberHere, setIsMemberHere] = useState(false);
  const [status, setStatus] = useState<"loading" | "error" | "gated" | "ready">("loading");
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!slug || !threadId) return;
    setStatus("loading");
    // Membership check runs regardless of thread visibility.
    try {
      const mine = await FactionApi.myMembership();
      setIsMemberHere(mine.some((m) => m.faction_slug === slug));
    } catch {
      setIsMemberHere(false);
    }
    try {
      const res = await FactionApi.thread(slug, threadId);
      setThread(res.thread);
      setReplies(res.replies);
      setStatus("ready");
    } catch (e) {
      if (e instanceof ApiError && e.status === 403) {
        setStatus("gated");
      } else {
        setStatus("error");
      }
    }
  }, [slug, threadId]);

  useEffect(() => {
    load();
  }, [load]);

  const send = async () => {
    const content = text.trim();
    if (content.length < 1) return;
    if (!character) {
      setNotice("You need an active hero to reply.");
      return;
    }
    setNotice(null);
    setSending(true);
    Keyboard.dismiss();
    try {
      await FactionApi.reply(slug, threadId, { character_id: character.id, content });
      const res = await FactionApi.thread(slug, threadId);
      setThread(res.thread);
      setReplies(res.replies);
      setText("");
    } catch (e) {
      setNotice(e instanceof Error ? e.message : "Could not post your reply.");
    } finally {
      setSending(false);
    }
  };

  return (
    <SafeAreaView style={styles.safe} edges={["top"]} testID={FACTIONS.threadScreen}>
      <Header title={name ?? "Thread"} subtitle="Faction hall" showBack />

      {status === "loading" ? (
        <Loading label="Opening the thread…" />
      ) : status === "gated" ? (
        <EmptyState
          icon="lock-closed-outline"
          title="Members only"
          subtitle="This discussion is sealed to sworn members of the faction."
        />
      ) : status === "error" || !thread ? (
        <ErrorView message="Could not load this thread." onRetry={load} />
      ) : (
        <KeyboardAvoidingView
          style={styles.flex}
          behavior={Platform.OS === "ios" ? "padding" : undefined}
          keyboardVerticalOffset={Platform.OS === "ios" ? 8 : 0}
        >
          <ScrollView contentContainerStyle={styles.body} showsVerticalScrollIndicator={false}>
            <View style={styles.opCard}>
              <Text style={styles.title}>{thread.title}</Text>
              <View style={styles.authorRow}>
                <Ionicons name="person-circle-outline" size={16} color={colors.gold} />
                <Text style={styles.author}>{thread.character_name}</Text>
                <Pill label={thread.author_rank} color={colors.gold} />
                <Text style={styles.date}>{fmt(thread.created_at)}</Text>
              </View>
              <Text style={styles.opContent}>{thread.content}</Text>
            </View>

            <Text style={styles.repliesLabel}>
              {replies.length} {replies.length === 1 ? "reply" : "replies"}
            </Text>

            {replies.map((r) => (
              <View key={r.id} style={styles.reply}>
                <View style={styles.authorRow}>
                  <Ionicons name="person-circle-outline" size={15} color={colors.textSecondary} />
                  <Text style={styles.replyAuthor}>{r.character_name}</Text>
                  <Pill label={r.author_rank} color={colors.textMuted} />
                  <Text style={styles.date}>{fmt(r.created_at)}</Text>
                </View>
                <Text style={styles.replyContent}>{r.content}</Text>
              </View>
            ))}
          </ScrollView>

          {notice ? (
            <View style={styles.noticeBar}>
              <Ionicons name="alert-circle-outline" size={16} color={colors.rose} />
              <Text style={styles.noticeText}>{notice}</Text>
            </View>
          ) : null}

          {isMemberHere ? (
            <View style={styles.inputBar}>
              <TextInput
                testID={FACTIONS.replyInput}
                value={text}
                onChangeText={setText}
                placeholder="Add your voice…"
                placeholderTextColor={colors.textMuted}
                style={styles.input}
                multiline
                editable={!sending}
              />
              <TouchableOpacity
                testID={FACTIONS.replySubmit}
                style={[styles.sendBtn, (sending || text.trim().length < 1) && styles.sendBtnDisabled]}
                onPress={send}
                disabled={sending || text.trim().length < 1}
              >
                {sending ? (
                  <ActivityIndicator color="#1A1206" size="small" />
                ) : (
                  <Ionicons name="send" size={18} color="#1A1206" />
                )}
              </TouchableOpacity>
            </View>
          ) : (
            <View style={styles.readonlyBar}>
              <Ionicons name="lock-closed-outline" size={14} color={colors.textMuted} />
              <Text style={styles.readonlyText}>Join this faction to join the conversation.</Text>
            </View>
          )}
        </KeyboardAvoidingView>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.bg },
  flex: { flex: 1 },
  body: { padding: spacing.md, paddingBottom: spacing.lg, gap: spacing.md },
  opCard: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.goldBorder,
    borderRadius: radius.lg,
    padding: spacing.md,
  },
  title: { ...typography.h2, color: colors.textPrimary },
  authorRow: { flexDirection: "row", alignItems: "center", gap: 6, marginTop: spacing.sm, flexWrap: "wrap" },
  author: { ...typography.small, color: colors.goldSoft, fontWeight: "700" },
  replyAuthor: { ...typography.small, color: colors.textPrimary, fontWeight: "700" },
  date: { ...typography.tiny, color: colors.textMuted, textTransform: "none" },
  opContent: { ...typography.body, color: colors.textSecondary, lineHeight: 22, marginTop: spacing.md },
  repliesLabel: {
    ...typography.tiny,
    color: colors.gold,
    textTransform: "uppercase",
    letterSpacing: 1,
    marginTop: spacing.sm,
  },
  reply: {
    backgroundColor: colors.bgElevated,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.md,
    padding: spacing.md,
  },
  replyContent: { ...typography.body, color: colors.textSecondary, lineHeight: 21, marginTop: spacing.sm },
  noticeBar: {
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
  readonlyBar: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.md,
    borderTopWidth: 1,
    borderTopColor: colors.border,
    backgroundColor: colors.bgElevated,
  },
  readonlyText: { ...typography.small, color: colors.textMuted },
});
