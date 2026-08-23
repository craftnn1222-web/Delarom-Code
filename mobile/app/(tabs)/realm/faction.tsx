import { Ionicons } from "@expo/vector-icons";
import { router, useFocusEffect, useLocalSearchParams } from "expo-router";
import { useCallback, useState } from "react";
import {
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { FACTIONS } from "@/constants/testIds";
import {
  Faction,
  FactionApi,
  FactionMember,
  FactionThread,
  FactionTreasury,
} from "@/src/api";
import { Button } from "@/src/components/Button";
import { Header } from "@/src/components/Header";
import { Pill } from "@/src/components/Pill";
import { ErrorView, Loading } from "@/src/components/StateViews";
import { useToast } from "@/src/components/Toast";
import { useAuth } from "@/src/context/AuthContext";
import { useActiveCharacter } from "@/src/hooks/useActiveCharacter";
import { colors, radius, spacing, typography } from "@/src/theme/theme";

const fmtDate = (iso?: string) => {
  if (!iso) return "";
  try {
    return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric" });
  } catch {
    return "";
  }
};

export default function FactionDetailScreen() {
  const { slug, name } = useLocalSearchParams<{ slug: string; name: string }>();
  const toast = useToast();
  const { user, refresh } = useAuth();
  const { character, noHero } = useActiveCharacter();
  const [faction, setFaction] = useState<Faction | null>(null);
  const [members, setMembers] = useState<FactionMember[]>([]);
  const [myMemberships, setMyMemberships] = useState<FactionMember[]>([]);
  const [threads, setThreads] = useState<FactionThread[]>([]);
  const [treasury, setTreasury] = useState<FactionTreasury | null>(null);
  const [status, setStatus] = useState<"loading" | "error" | "ready">("loading");
  const [working, setWorking] = useState(false);

  const [donateOpen, setDonateOpen] = useState(false);
  const [donateAmount, setDonateAmount] = useState("");
  const [donating, setDonating] = useState(false);

  const load = useCallback(async () => {
    if (!slug) return;
    setStatus("loading");
    try {
      const [f, mem, mine, thr, tre] = await Promise.all([
        FactionApi.get(slug),
        FactionApi.members(slug),
        FactionApi.myMembership(),
        FactionApi.threads(slug).catch(() => [] as FactionThread[]),
        FactionApi.treasury(slug).catch(() => null),
      ]);
      setFaction(f);
      setMembers(mem);
      setMyMemberships(mine);
      setThreads(thr);
      setTreasury(tre);
      setStatus("ready");
    } catch {
      setStatus("error");
    }
  }, [slug]);

  useFocusEffect(
    useCallback(() => {
      load();
    }, [load]),
  );

  const heroMembership = character
    ? myMemberships.find((m) => m.character_id === character.id)
    : undefined;
  const isMemberHere = heroMembership?.faction_slug === slug;
  const isMemberElsewhere = heroMembership && heroMembership.faction_slug !== slug;

  const join = async () => {
    if (!character || !slug) return;
    setWorking(true);
    try {
      await FactionApi.join(slug, character.id);
      toast.show(`${character.name} now serves ${name}`, "success");
      await load();
    } catch (e) {
      toast.show(e instanceof Error ? e.message : "Could not join — try again.", "error");
    } finally {
      setWorking(false);
    }
  };

  const leave = async () => {
    if (!character || !slug) return;
    setWorking(true);
    try {
      await FactionApi.leave(slug, character.id);
      toast.show(`${character.name} has left ${name}`, "info");
      await load();
    } catch (e) {
      toast.show(e instanceof Error ? e.message : "Could not leave — try again.", "error");
    } finally {
      setWorking(false);
    }
  };

  const donate = async () => {
    if (!character || !slug) return;
    const amount = parseInt(donateAmount, 10);
    if (!amount || amount < 1) {
      toast.show("Enter an amount of at least 1 gold.", "error");
      return;
    }
    setDonating(true);
    try {
      const res = await FactionApi.donate(slug, { character_id: character.id, amount });
      setTreasury(res.treasury);
      await refresh();
      toast.show(`Donated ${amount} gold to ${faction?.name}.`, "success");
      setDonateOpen(false);
      setDonateAmount("");
    } catch (e) {
      toast.show(e instanceof Error ? e.message : "Donation failed.", "error");
    } finally {
      setDonating(false);
    }
  };

  const color = faction?.color_hex || colors.gold;

  return (
    <SafeAreaView style={styles.safe} edges={["top"]} testID={FACTIONS.detailScreen}>
      <Header title={name ?? "Faction"} showBack />
      {status === "loading" ? (
        <Loading label="Reading the charter…" />
      ) : status === "error" || !faction ? (
        <ErrorView message="Could not load this faction." onRetry={load} />
      ) : (
        <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
          <View style={[styles.crest, { borderColor: color, backgroundColor: color + "1A" }]}>
            <Ionicons name="shield-half" size={40} color={color} />
          </View>
          <Text style={styles.name}>{faction.name}</Text>
          <Text style={[styles.motto, { color }]}>&ldquo;{faction.motto}&rdquo;</Text>
          <View style={styles.badges}>
            <Pill label={faction.nation_home} color={colors.textMuted} />
            <Pill label={`${faction.member_count} members`} color={color} icon="people" />
          </View>

          <Text style={styles.body}>{faction.description}</Text>

          {isMemberHere ? (
            <Button
              title={`Leave as ${character?.name}`}
              variant="danger"
              icon="exit-outline"
              onPress={leave}
              loading={working}
              testID={FACTIONS.leaveButton}
              style={styles.action}
            />
          ) : isMemberElsewhere ? (
            <View style={styles.noteBox}>
              <Ionicons name="information-circle-outline" size={16} color={colors.gold} />
              <Text style={styles.noteText}>
                {character?.name} already serves {heroMembership?.faction_name}. Leave there first
                to pledge here.
              </Text>
            </View>
          ) : noHero ? (
            <Text style={styles.hint}>Create a hero to pledge to a faction.</Text>
          ) : (
            <Button
              title={character ? `Join as ${character.name}` : "Join faction"}
              icon="add-circle-outline"
              onPress={join}
              loading={working}
              disabled={!character}
              testID={FACTIONS.joinButton}
              style={styles.action}
            />
          )}

          {/* Treasury */}
          <Text style={styles.sectionLabel}>Treasury</Text>
          <View style={[styles.treasuryCard, { borderColor: color + "55" }]} testID={FACTIONS.treasuryCard}>
            <View style={styles.treasuryRow}>
              <Ionicons name="cash" size={22} color={colors.gold} />
              <View style={styles.treasuryFigures}>
                <Text style={styles.treasuryBalance}>
                  {(treasury?.balance ?? 0).toLocaleString()} g
                </Text>
                <Text style={styles.treasurySub}>
                  {(treasury?.total_donated ?? 0).toLocaleString()} g donated all-time
                </Text>
              </View>
            </View>
            {isMemberHere ? (
              <Button
                title="Donate gold"
                icon="gift-outline"
                variant="secondary"
                onPress={() => setDonateOpen(true)}
                testID={FACTIONS.donateButton}
                style={styles.donateBtn}
              />
            ) : (
              <Text style={styles.treasuryHint}>Join the faction to contribute to its coffer.</Text>
            )}
          </View>

          {/* Trade Routes (Contract Manager) */}
          <Button
            title="Trade Routes"
            icon="git-network-outline"
            variant="secondary"
            onPress={() =>
              router.push({
                pathname: "/(tabs)/realm/faction-routes",
                params: { slug: String(slug), name: faction.name },
              })
            }
            testID={FACTIONS.routesButton}
            style={styles.routesBtn}
          />

          {/* Discussion */}
          <View style={styles.discussionHead}>
            <Text style={[styles.sectionLabel, styles.sectionLabelInline]}>Discussion</Text>
            {isMemberHere ? (
              <TouchableOpacity
                testID={FACTIONS.newThreadButton}
                style={styles.newThreadBtn}
                activeOpacity={0.85}
                onPress={() =>
                  router.push({
                    pathname: "/(tabs)/realm/faction-thread-new",
                    params: { slug: String(slug), name: faction.name },
                  })
                }
              >
                <Ionicons name="create-outline" size={16} color={colors.goldSoft} />
                <Text style={styles.newThreadText}>New</Text>
              </TouchableOpacity>
            ) : null}
          </View>

          <View style={styles.threads} testID={FACTIONS.threadsSection}>
            {threads.length === 0 ? (
              <Text style={styles.hint}>
                No threads yet.{isMemberHere ? " Start the first one." : ""}
              </Text>
            ) : (
              threads.map((t) => (
                <TouchableOpacity
                  key={t.id}
                  testID={`${FACTIONS.threadCard}-${t.id}`}
                  activeOpacity={0.85}
                  style={styles.threadCard}
                  onPress={() =>
                    router.push({
                      pathname: "/(tabs)/realm/faction-thread",
                      params: { slug: String(slug), threadId: t.id, name: faction.name },
                    })
                  }
                >
                  <View style={styles.threadInfo}>
                    <Text style={styles.threadTitle} numberOfLines={1}>
                      {t.title}
                    </Text>
                    <Text style={styles.threadMeta} numberOfLines={1}>
                      {t.character_name} · {fmtDate(t.created_at)}
                    </Text>
                  </View>
                  <View style={styles.threadReplies}>
                    <Ionicons name="chatbubble-outline" size={14} color={colors.textMuted} />
                    <Text style={styles.threadRepliesText}>{t.replies_count}</Text>
                  </View>
                </TouchableOpacity>
              ))
            )}
          </View>

          <Text style={styles.sectionLabel}>Roster</Text>
          {members.length === 0 ? (
            <Text style={styles.hint}>No sworn members yet — be the first.</Text>
          ) : (
            <View style={styles.roster}>
              {members.map((m) => (
                <View key={m.id} style={styles.memberRow}>
                  <Ionicons name="person-circle-outline" size={20} color={colors.textSecondary} />
                  <Text style={styles.memberName} numberOfLines={1}>
                    {m.character_name}
                  </Text>
                  <Pill label={m.rank} color={color} />
                </View>
              ))}
            </View>
          )}
        </ScrollView>
      )}

      {/* Donate modal */}
      <Modal visible={donateOpen} transparent animationType="fade" onRequestClose={() => setDonateOpen(false)}>
        <Pressable style={styles.backdrop} onPress={() => setDonateOpen(false)}>
          <Pressable style={styles.donateSheet} onPress={() => {}}>
            <Text style={styles.donateTitle}>Donate to {faction?.name}</Text>
            <Text style={styles.donateHint}>You hold {(user?.currency ?? 0).toLocaleString()} gold.</Text>
            <TextInput
              testID={FACTIONS.donateInput}
              value={donateAmount}
              onChangeText={setDonateAmount}
              placeholder="Amount in gold"
              placeholderTextColor={colors.textMuted}
              keyboardType="number-pad"
              style={styles.donateField}
              editable={!donating}
            />
            <Button
              title="Give gold"
              icon="gift-outline"
              onPress={donate}
              loading={donating}
              testID={FACTIONS.donateSubmit}
              style={styles.donateSubmitBtn}
            />
          </Pressable>
        </Pressable>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.bg },
  content: { padding: spacing.md, paddingBottom: spacing.xxl, alignItems: "center" },
  crest: {
    width: 84,
    height: 84,
    borderRadius: 42,
    borderWidth: 1,
    alignItems: "center",
    justifyContent: "center",
  },
  name: { ...typography.h1, color: colors.textPrimary, marginTop: spacing.md, textAlign: "center" },
  motto: { ...typography.body, fontStyle: "italic", marginTop: 4, textAlign: "center" },
  badges: { flexDirection: "row", gap: spacing.sm, marginTop: spacing.md },
  body: {
    ...typography.body,
    color: colors.textSecondary,
    lineHeight: 22,
    marginTop: spacing.lg,
    alignSelf: "stretch",
  },
  action: { alignSelf: "stretch", marginTop: spacing.xl },
  noteBox: {
    flexDirection: "row",
    gap: 8,
    alignItems: "center",
    alignSelf: "stretch",
    marginTop: spacing.xl,
    padding: spacing.md,
    borderRadius: radius.md,
    backgroundColor: colors.goldDim,
    borderWidth: 1,
    borderColor: colors.goldBorder,
  },
  noteText: { ...typography.small, color: colors.goldSoft, flex: 1 },
  hint: { ...typography.small, color: colors.textMuted, marginTop: spacing.md, textAlign: "center", alignSelf: "stretch" },
  sectionLabel: {
    ...typography.tiny,
    color: colors.gold,
    textTransform: "uppercase",
    letterSpacing: 1,
    alignSelf: "flex-start",
    marginTop: spacing.xl,
    marginBottom: spacing.md,
  },
  sectionLabelInline: { marginTop: 0, marginBottom: 0 },
  treasuryCard: {
    alignSelf: "stretch",
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderRadius: radius.lg,
    padding: spacing.md,
  },
  treasuryRow: { flexDirection: "row", alignItems: "center", gap: spacing.md },
  treasuryFigures: { flex: 1 },
  treasuryBalance: { ...typography.h1, color: colors.gold },
  treasurySub: { ...typography.small, color: colors.textSecondary, marginTop: 2 },
  treasuryHint: { ...typography.small, color: colors.textMuted, marginTop: spacing.md },
  donateBtn: { marginTop: spacing.md },
  routesBtn: { alignSelf: "stretch", marginTop: spacing.md },
  discussionHead: {
    alignSelf: "stretch",
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginTop: spacing.xl,
    marginBottom: spacing.md,
  },
  newThreadBtn: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    paddingHorizontal: spacing.md,
    paddingVertical: 6,
    borderRadius: radius.pill,
    backgroundColor: colors.goldDim,
    borderWidth: 1,
    borderColor: colors.goldBorder,
  },
  newThreadText: { ...typography.small, color: colors.goldSoft, fontWeight: "700" },
  threads: { alignSelf: "stretch", gap: spacing.sm },
  threadCard: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.md,
    padding: spacing.md,
  },
  threadInfo: { flex: 1, marginRight: spacing.sm },
  threadTitle: { ...typography.bodyStrong, color: colors.textPrimary },
  threadMeta: { ...typography.tiny, color: colors.textMuted, marginTop: 2, textTransform: "none" },
  threadReplies: { flexDirection: "row", alignItems: "center", gap: 4 },
  threadRepliesText: { ...typography.small, color: colors.textMuted },
  roster: { alignSelf: "stretch", gap: spacing.sm },
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
  memberName: { ...typography.body, color: colors.textPrimary, flex: 1 },
  backdrop: { flex: 1, backgroundColor: colors.overlay, justifyContent: "flex-end" },
  donateSheet: {
    backgroundColor: colors.bgElevated,
    borderTopLeftRadius: radius.xl,
    borderTopRightRadius: radius.xl,
    borderWidth: 1,
    borderColor: colors.border,
    padding: spacing.lg,
    paddingBottom: spacing.xl,
  },
  donateTitle: { ...typography.h2, color: colors.textPrimary },
  donateHint: { ...typography.small, color: colors.textSecondary, marginTop: spacing.xs },
  donateField: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.md,
    paddingHorizontal: spacing.md,
    paddingVertical: 13,
    color: colors.textPrimary,
    fontSize: 16,
    marginTop: spacing.md,
  },
  donateSubmitBtn: { marginTop: spacing.md },
});
