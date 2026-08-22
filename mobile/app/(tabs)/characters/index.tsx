import { Ionicons } from "@expo/vector-icons";
import { router, useFocusEffect } from "expo-router";
import { useCallback, useState } from "react";
import { FlatList, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { CHARACTERS } from "@/constants/testIds";
import { Character, CharacterApi } from "@/src/api";
import { Portrait } from "@/src/components/CharacterBits";
import { Header } from "@/src/components/Header";
import { EmptyState, ErrorView, Loading } from "@/src/components/StateViews";
import { colors, radius, spacing, typography } from "@/src/theme/theme";

export default function CharactersScreen() {
  const [characters, setCharacters] = useState<Character[]>([]);
  const [status, setStatus] = useState<"loading" | "error" | "ready">("loading");
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async (soft = false) => {
    if (!soft) setStatus("loading");
    try {
      const data = await CharacterApi.list();
      setCharacters(data);
      setStatus("ready");
    } catch {
      setStatus("error");
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      load(true);
    }, [load]),
  );

  const onRefresh = async () => {
    setRefreshing(true);
    await load(true);
    setRefreshing(false);
  };

  return (
    <SafeAreaView style={styles.safe} edges={["top"]} testID={CHARACTERS.screen}>
      <Header
        title="Your Heroes"
        right={
          <TouchableOpacity
            testID={CHARACTERS.newButton}
            onPress={() => router.push("/(tabs)/characters/new")}
            hitSlop={{ top: 12, bottom: 12, left: 12, right: 12 }}
          >
            <Ionicons name="add-circle" size={30} color={colors.gold} />
          </TouchableOpacity>
        }
      />

      {status === "loading" ? (
        <Loading label="Summoning your roster…" />
      ) : status === "error" ? (
        <ErrorView message="Could not load your heroes." onRetry={() => load()} />
      ) : characters.length === 0 ? (
        <EmptyState
          icon="add-circle-outline"
          title="No heroes yet"
          subtitle="Every legend starts somewhere. Forge your first hero."
          actionLabel="Create a hero"
          actionTestID={CHARACTERS.newButton}
          onAction={() => router.push("/(tabs)/characters/new")}
        />
      ) : (
        <FlatList
          data={characters}
          keyExtractor={(c) => c.id}
          contentContainerStyle={styles.list}
          showsVerticalScrollIndicator={false}
          refreshing={refreshing}
          onRefresh={onRefresh}
          renderItem={({ item }) => (
            <TouchableOpacity
              testID={CHARACTERS.card}
              activeOpacity={0.85}
              style={styles.row}
              onPress={() =>
                router.push({ pathname: "/(tabs)/characters/[id]", params: { id: item.id } })
              }
            >
              <Portrait uri={item.portrait_url} name={item.name} size={54} />
              <View style={styles.info}>
                <Text style={styles.name} numberOfLines={1}>
                  {item.name}
                </Text>
                <Text style={styles.meta} numberOfLines={1}>
                  {item.race} · {item.character_class}
                </Text>
                <View style={styles.badges}>
                  <View style={styles.levelBadge}>
                    <Text style={styles.levelText}>Lv {item.level}</Text>
                  </View>
                  <Text style={styles.nation}>{item.nation}</Text>
                </View>
              </View>
              <Ionicons name="chevron-forward" size={20} color={colors.textMuted} />
            </TouchableOpacity>
          )}
        />
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.bg },
  list: { padding: spacing.md, gap: spacing.md },
  row: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.lg,
    padding: spacing.md,
  },
  info: { flex: 1, marginLeft: spacing.md },
  name: { ...typography.h3, color: colors.textPrimary },
  meta: { ...typography.small, color: colors.textSecondary, marginTop: 2 },
  badges: { flexDirection: "row", alignItems: "center", marginTop: spacing.sm, gap: spacing.sm },
  levelBadge: {
    paddingHorizontal: spacing.sm,
    paddingVertical: 2,
    borderRadius: radius.sm,
    backgroundColor: colors.goldDim,
    borderWidth: 1,
    borderColor: colors.goldBorder,
  },
  levelText: { ...typography.tiny, color: colors.goldSoft },
  nation: { ...typography.tiny, color: colors.textMuted, textTransform: "uppercase" },
});
