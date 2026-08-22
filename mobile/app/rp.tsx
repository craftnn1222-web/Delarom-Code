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

import { RP } from "@/constants/testIds";
import { Character, CharacterApi, RpApi, RpPost } from "@/src/api";
import { Header } from "@/src/components/Header";
import { EmptyState, ErrorView, Loading } from "@/src/components/StateViews";
import { colors, radius, spacing, typography } from "@/src/theme/theme";

export default function RoleplayScreen() {
  const { nation, location, name } = useLocalSearchParams<{
    nation: string;
    location: string;
    name: string;
  }>();

  const [posts, setPosts] = useState<RpPost[]>([]);
  const [hero, setHero] = useState<Character | null>(null);
  const [noHero, setNoHero] = useState(false);
  const [status, setStatus] = useState<"loading" | "error" | "ready">("loading");
  const [text, setText] = useState("");
  const [pending, setPending] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  const scrollRef = useRef<ScrollView>(null);

  const load = useCallback(async () => {
    if (!nation || !location) return;
    setStatus("loading");
    const [history, chars] = await Promise.allSettled([
      RpApi.history(nation, location),
      CharacterApi.list(),
    ]);
    if (history.status === "fulfilled") setPosts(history.value);
    if (chars.status === "fulfilled") {
      setHero(chars.value[0] ?? null);
      setNoHero(chars.value.length === 0);
    }
    if (history.status === "rejected" && chars.status === "rejected") {
      setStatus("error");
    } else {
      setStatus("ready");
    }
  }, [nation, location]);

  useEffect(() => {
    load();
  }, [load]);

  const scrollToEnd = useCallback(() => {
    setTimeout(() => scrollRef.current?.scrollToEnd({ animated: true }), 80);
  }, []);

  useEffect(() => {
    if (status === "ready") scrollToEnd();
  }, [posts, pending, status, scrollToEnd]);

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
      await RpApi.submit(nation, location, action);
      const fresh = await RpApi.history(nation, location);
      setPosts(fresh);
      setText("");
      setPending(null);
    } catch (e) {
      setNotice(e instanceof Error ? e.message : "The world did not respond. Try again.");
      setPending(null);
    } finally {
      setSending(false);
    }
  };

  return (
    <SafeAreaView style={styles.safe} edges={["top"]} testID={RP.screen}>
      <Header title={name ?? "Scene"} subtitle={String(nation ?? "")} showBack />

      {status === "loading" ? (
        <Loading label="Setting the scene…" />
      ) : status === "error" ? (
        <ErrorView message="Could not enter this scene." onRetry={load} />
      ) : noHero ? (
        <EmptyState
          icon="person-add-outline"
          title="You need a hero first"
          subtitle="Create a character before you step into the world."
          actionLabel="Create a hero"
          onAction={() => router.push("/(tabs)/characters/new")}
        />
      ) : (
        <KeyboardAvoidingView
          style={styles.flex}
          behavior={Platform.OS === "ios" ? "padding" : undefined}
          keyboardVerticalOffset={Platform.OS === "ios" ? 8 : 0}
        >
          {hero ? (
            <View style={styles.playingBanner}>
              <Ionicons name="person-circle-outline" size={16} color={colors.gold} />
              <Text style={styles.playingText}>
                Playing as <Text style={styles.playingName}>{hero.name}</Text>
              </Text>
            </View>
          ) : null}

          <ScrollView
            ref={scrollRef}
            contentContainerStyle={styles.log}
            showsVerticalScrollIndicator={false}
            onContentSizeChange={scrollToEnd}
          >
            {posts.length === 0 && !pending ? (
              <View style={styles.introWrap}>
                <Ionicons name="book-outline" size={26} color={colors.gold} />
                <Text style={styles.introText}>
                  The scene is quiet. Write your first action to bring {name} to life.
                </Text>
              </View>
            ) : null}

            {posts.map((post) => (
              <View key={post.id} testID={RP.logEntry}>
                {post.action_text ? (
                  <View style={styles.playerBubble}>
                    <Text style={styles.playerAuthor}>{post.character_name}</Text>
                    <Text style={styles.playerText}>{post.action_text}</Text>
                  </View>
                ) : null}
                {post.ai_response ? (
                  <View style={styles.narrationBubble}>
                    <Text style={styles.narrationText}>{post.ai_response}</Text>
                  </View>
                ) : null}
              </View>
            ))}

            {pending ? (
              <View>
                <View style={styles.playerBubble}>
                  <Text style={styles.playerAuthor}>{hero?.name}</Text>
                  <Text style={styles.playerText}>{pending}</Text>
                </View>
                <View style={[styles.narrationBubble, styles.pendingBubble]}>
                  <ActivityIndicator color={colors.violetSoft} size="small" />
                  <Text style={styles.pendingText}>The world responds…</Text>
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
            <TextInput
              testID={RP.input}
              value={text}
              onChangeText={setText}
              placeholder="What do you do?"
              placeholderTextColor={colors.textMuted}
              style={styles.input}
              multiline
              editable={!sending}
            />
            <TouchableOpacity
              testID={RP.sendButton}
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
});
