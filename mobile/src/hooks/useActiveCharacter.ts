// Fetches the current user's roster and exposes the "active hero" (first
// character), which the backend uses for quest accept, purchases, faction
// join/leave and party hosting. Mirrors how the RP screen picks characters[0].

import { useCallback, useEffect, useState } from "react";

import { Character, CharacterApi } from "@/src/api";

export function useActiveCharacter() {
  const [character, setCharacter] = useState<Character | null>(null);
  const [loading, setLoading] = useState(true);
  const [noHero, setNoHero] = useState(false);

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      const chars = await CharacterApi.list();
      setCharacter(chars[0] ?? null);
      setNoHero(chars.length === 0);
    } catch {
      setCharacter(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    reload();
  }, [reload]);

  return { character, loading, noHero, reload };
}
