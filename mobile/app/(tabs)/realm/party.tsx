import { Ionicons } from "@expo/vector-icons";
import { useLocalSearchParams } from "expo-router";
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

import { PARTIES } from "@/constants/testIds";
import { Party, PartyAction, PartyApi } from "@/src/api";
import { Button } from "@/src/components/Button";
import { Header } from "@/src/components/Header";
import { partyStatusColor, Pill } from "@/src/components/Pill";
import { ErrorView, Loading } from "@/src/components/StateViews";
import { useAuth } from "@/src/context/AuthContext";
import { useActiveCharacter } from "@/src/hooks/useActiveCharacter";
import { colors, radius, spacing, typography } from "@/src/theme/theme";

export default function PartyDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { user } = useAuth();
  const { character } = useActiveCharacter();
  const [party, setParty] = useState<Party | null>(null);
  const [actions, setActions] = useState<PartyAction[]>([]);
  const [status, setStatus] = useState<"loading" | "error" | "ready">("loading");
  const [working, setWorking] = useState(false);
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const scrollRef = useRef<ScrollView>(null);

  const load = useCallback(
    async (soft = false) => {
      if (!id) return;
      if (!soft) setStatus("loading");
      try {
        const [p, acts] = await Promise.all([PartyApi.get(id), PartyApi.actions(id)]);
        setParty(p);
        setActions(acts);
        setStatus("ready");
      } catch {
        if (!soft) setStatus("error");
      }
    },
    [id],
  );

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (status === "ready") setTimeout(() => scrollRef.current?.scrollToEnd({ animated: true }), 100);
  }, [actions, status]);

  if (status === "loading") {
    return (
      <SafeAreaView style={styles.safe} edges={["top"]} testID={PARTIES.detailScreen}>
        <Header title="Party" showBack />
        <Loading label="Joining the circle…" />
      </SafeAreaView>
    );
  }
  if (status === "error" || !party) {
    return (
      <SafeAreaView style={styles.safe} edges={["top"]} testID={PARTIES.detailScreen}>
        <Header title="Party" showBack />
        <ErrorView message="Could not load this party." onRetry={load} />
      </SafeAreaView>
    );
  }

  const isHost = user?.id === party.host_user_id;
  const myMember = party.members.find((m) => m.user_id === user?.id);
  const isMember = !!myMember;
  const isFull = party.members.length >= party.max_members;
  const currentActorCid = party.turn_order[party.current_turn_index];
  const currentActor = party.members.find((m) => m.character_id === currentActorCid);
  const isMyTurn = party.status === "active" && currentActor?.user_id === user?.id;

  const runLifecycle = async (fn: () => Promise<unknown>) => {
    setWorking(true);
    setNotice(null);
    try {
      await fn();
      await load(true);
    } catch (e) {
      setNotice(e instanceof Error ? e.message : "Action failed.");
    } finally {
      setWorking(false);
    }
  };

  const send = async () => {
    const action = text.trim();
    if (action.length < 3) {
      setNotice("Describe your action in a few words.");
      return;
    }
    setSending(true);
    setNotice(null);
    Keyboard.dismiss();
    try {
      await PartyApi.action(party.id, action);
      setText("");
      await load(true);
    } catch (e) {
      setNotice(e instanceof Error ? e.message : "The scene did not advance.");
    } finally {
      setSending(false);
    }
  };

  const showInput = party.status === "active" && isMember;

  return (
    <SafeAreaView style={styles.safe} edges={["top"]} testID={PARTIES.detailScreen}>
      <Header title={party.name} subtitle={party.location} showBack />
      <KeyboardAvoidingView
        style={styles.flex}
        behavior={Platform.OS === "ios" ? "padding" : undefined}
        keyboardVerticalOffset={Platform.OS === "ios" ? 8 : 0}
      >
        <ScrollView ref={scrollRef} contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
          <View style={styles.statusRow}>
            <Pill label={party.status} color={partyStatusColor(party.status)} />
            <Text style={styles.count}>
              {party.members.length}/{party.max_members} members
            </Text>
          </View>

          <View style={styles.sceneCard}>
            <Text style={styles.sceneLabel}>The Scene</Text>
            <Text style={styles.sceneText}>{party.scene_description}</Text>
          </View>

          <Text style={styles.sectionLabel}>Fellowship</Text>
          <View style={styles.members}>
            {party.members.map((m) => {
              const isUp = party.status === "active" && m.character_id === currentActorCid;
              return (
                <View key={m.character_id} style={[styles.memberRow, isUp && styles.memberUp]}>
                  <Ionicons
                    name={m.role === "host" ? "star" : "person-circle-outline"}
                    size={18}
                    color={m.role === "host" ? colors.gold : colors.textSecondary}
                  />
                  <Text style={styles.memberName} numberOfLines={1}>
                    {m.character_name}
                  </Text>
                  <Text style={styles.memberClass} numberOfLines={1}>
                    {m.character_class}
                  </Text>
                  {isUp ? <Pill label="Up" color={colors.green} /> : null}
                </View>
              );
            })}
          </View>

          {/* Lifecycle controls */}
          <View style={styles.controls}>
            {party.status === "recruiting" && isHost ? (
              <Button
                title="Start the scene"
                icon="play"
                onPress={() => runLifecycle(() => PartyApi.start(party.id))}
                loading={working}
                testID={PARTIES.startButton}
              />
            ) : null}
            {party.status === "recruiting" && !isMember && !isFull ? (
              <Button
                title={character ? `Join as ${character.name}` : "Join party"}
                icon="add-circle-outline"
                onPress={() => runLifecycle(() => PartyApi.join(party.id, character!.id))}
                loading={working}
                disabled={!character}
                testID={PARTIES.joinButton}
              />
            ) : null}
            {party.status === "recruiting" && isMember && !isHost ? (
              <Button
                title="Leave party"
                variant="danger"
                icon="exit-outline"
                onPress={() => runLifecycle(() => PartyApi.leave(party.id))}
                loading={working}
                testID={PARTIES.leaveButton}
              />
            ) : null}
            {party.status === "active" && isHost ? (
              <Button
                title="End party"
                variant="ghost"
                icon="flag-outline"
                onPress={() => runLifecycle(() => PartyApi.finish(party.id))}
                loading={working}
                testID={PARTIES.finishButton}
              />
            ) : null}
            {party.status === "recruiting" && !isMember && isFull ? (
              <Text style={styles.hint}>This party is full.</Text>
            ) : null}
            {party.status === "finished" ? (
              <View style={styles.endedBanner}>
                <Ionicons name="checkmark-done" size={16} color={colors.textMuted} />
                <Text style={styles.endedText}>This scene has ended.</Text>
              </View>
            ) : null}
          </View>

          {/* Scene log */}
          {actions.length > 0 ? <Text style={styles.sectionLabel}>Scene Log</Text> : null}
          {actions.map((a) => (
            <View key={a.id} style={styles.turn}>
              {a.actor_character_id !== "MOC" ? (
                <View style={styles.playerBubble}>
                  <Text style={styles.playerAuthor}>{a.actor_character_name}</Text>
                  <Text style={styles.playerText}>{a.action_text}</Text>
                </View>
              ) : null}
              {a.ai_response ? (
                <View style={styles.narration}>
                  <Text style={styles.narrationText}>{a.ai_response}</Text>
                </View>
              ) : null}
            </View>
          ))}

          {party.status === "active" && !isMyTurn && isMember ? (
            <Text style={styles.waiting}>
              Waiting for {currentActor?.character_name ?? "the next player"}…
            </Text>
          ) : null}
        </ScrollView>

        {notice ? (
          <View style={styles.notice}>
            <Ionicons name="alert-circle-outline" size={16} color={colors.rose} />
            <Text style={styles.noticeText}>{notice}</Text>
          </View>
        ) : null}

        {showInput ? (
          <View style={styles.inputBar}>
            <TextInput
              testID={PARTIES.actionInput}
              value={text}
              onChangeText={setText}
              placeholder={isMyTurn ? "It's your turn — what do you do?" : "Waiting for your turn…"}
              placeholderTextColor={colors.textMuted}
              style={styles.input}
              multiline
              editable={isMyTurn && !sending}
            />
            <TouchableOpacity
              testID={PARTIES.sendButton}
              style={[styles.sendBtn, (!isMyTurn || sending || text.trim().length < 3) && styles.sendDisabled]}
              onPress={send}
              disabled={!isMyTurn || sending || text.trim().length < 3}
            >
              {sending ? (
                <ActivityIndicator color="#1A1206" size="small" />
              ) : (
                <Ionicons name="send" size={18} color="#1A1206" />
              )}
            </TouchableOpacity>
          </View>
        ) : null}
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.bg },
  flex: { flex: 1 },
  content: { padding: spacing.md, paddingBottom: spacing.lg, gap: spacing.md },
  statusRow: { flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  count: { ...typography.small, color: colors.textSecondary },
  sceneCard: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.violetBorder,
    borderRadius: radius.lg,
    padding: spacing.md,
  },
  sceneLabel: {
    ...typography.tiny,
    color: colors.violetSoft,
    textTransform: "uppercase",
    letterSpacing: 1,
    marginBottom: 6,
  },
  sceneText: { ...typography.body, color: colors.textSecondary, lineHeight: 22 },
  sectionLabel: {
    ...typography.tiny,
    color: colors.gold,
    textTransform: "uppercase",
    letterSpacing: 1,
    marginTop: spacing.sm,
  },
  members: { gap: spacing.sm },
  memberRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.md,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
  },
  memberUp: { borderColor: colors.green },
  memberName: { ...typography.body, color: colors.textPrimary, flex: 1 },
  memberClass: { ...typography.tiny, color: colors.textMuted },
  controls: { gap: spacing.sm },
  hint: { ...typography.small, color: colors.textMuted, textAlign: "center" },
  endedBanner: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    padding: spacing.md,
    borderRadius: radius.md,
    backgroundColor: colors.surfaceAlt,
    borderWidth: 1,
    borderColor: colors.border,
  },
  endedText: { ...typography.small, color: colors.textMuted },
  turn: { gap: spacing.sm },
  playerBubble: {
    alignSelf: "flex-end",
    maxWidth: "88%",
    backgroundColor: colors.goldDim,
    borderWidth: 1,
    borderColor: colors.goldBorder,
    borderRadius: radius.lg,
    borderBottomRightRadius: 4,
    padding: spacing.md,
  },
  playerAuthor: { ...typography.tiny, color: colors.goldSoft, marginBottom: 4, textTransform: "uppercase" },
  playerText: { ...typography.body, color: colors.textPrimary, lineHeight: 21 },
  narration: {
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
  waiting: { ...typography.small, color: colors.textMuted, textAlign: "center", fontStyle: "italic" },
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
  sendDisabled: { opacity: 0.5 },
});
