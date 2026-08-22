// The global "active hero" — the character the player is currently playing.
// The choice is persisted SERVER-SIDE (on the user record) so it is shared
// between web and mobile. The backend uses it for quest accept, purchases,
// faction join/leave, party hosting and Location RP. `setActive` switches the
// hero; other screens pick up the change on their next focus/reload.

import { useCallback, useEffect, useState } from "react";

import { Character, CharacterApi } from "@/src/api";

export function useActiveCharacter() {
  const [character, setCharacter] = useState<Character | null>(null);
  const [characters, setCharacters] = useState<Character[]>([]);
  const [loading, setLoading] = useState(true);
  const [noHero, setNoHero] = useState(false);

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      const [roster, active] = await Promise.all([
        CharacterApi.list(),
        CharacterApi.active().catch(() => ({ character: null, active_character_id: null })),
      ]);
      setCharacters(roster);
      setCharacter(active.character ?? roster[0] ?? null);
      setNoHero(roster.length === 0);
    } catch {
      setCharacter(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    reload();
  }, [reload]);

  const setActive = useCallback(async (id: string) => {
    const res = await CharacterApi.setActive(id);
    setCharacter(res.character);
    return res.character;
  }, []);

  return { character, characters, loading, noHero, reload, setActive };
}
