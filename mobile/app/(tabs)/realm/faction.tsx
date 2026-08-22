import { Ionicons } from "@expo/vector-icons";
import { useLocalSearchParams } from "expo-router";
import { useCallback, useEffect, useState } from "react";
import { ScrollView, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { FACTIONS } from "@/constants/testIds";
import { Faction, FactionApi, FactionMember } from "@/src/api";
import { Button } from "@/src/components/Button";
import { Header } from "@/src/components/Header";
import { Pill } from "@/src/components/Pill";
import { ErrorView, Loading } from "@/src/components/StateViews";
import { useToast } from "@/src/components/Toast";
import { useActiveCharacter } from "@/src/hooks/useActiveCharacter";
import { colors, radius, spacing, typography } from "@/src/theme/theme";

export default function FactionDetailScreen() {
  const { slug, name } = useLocalSearchParams<{ slug: string; name: string }>();
  const toast = useToast();
  const { character, noHero } = useActiveCharacter();
  const [faction, setFaction] = useState<Faction | null>(null);
  const [members, setMembers] = useState<FactionMember[]>([]);
  const [myMemberships, setMyMemberships] = useState<FactionMember[]>([]);
  const [status, setStatus] = useState<"loading" | "error" | "ready">("loading");
  const [working, setWorking] = useState(false);

  const load = useCallback(async () => {
    if (!slug) return;
    setStatus("loading");
    try {
      const [f, mem, mine] = await Promise.all([
        FactionApi.get(slug),
        FactionApi.members(slug),
        FactionApi.myMembership(),
      ]);
      setFaction(f);
      setMembers(mem);
      setMyMemberships(mine);
      setStatus("ready");
    } catch {
      setStatus("error");
    }
  }, [slug]);

  useEffect(() => {
    load();
  }, [load]);

  // Membership for the active hero, if any.
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
  hint: { ...typography.small, color: colors.textMuted, marginTop: spacing.md, textAlign: "center" },
  sectionLabel: {
    ...typography.tiny,
    color: colors.gold,
    textTransform: "uppercase",
    letterSpacing: 1,
    alignSelf: "flex-start",
    marginTop: spacing.xl,
    marginBottom: spacing.md,
  },
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
});
