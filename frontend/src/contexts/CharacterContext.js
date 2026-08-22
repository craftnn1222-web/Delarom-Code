import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { getMyCharacters, getActiveCharacter, setActiveCharacterApi } from '../utils/api';
import { useAuth } from './AuthContext';

/**
 * CharacterContext — the global "who am I playing" hero.
 *
 * The active character is persisted server-side (on the user record) so the
 * choice is the SAME across web and mobile. The backend uses it for Location
 * RP and scene state; the UI uses it as the default hero for actions.
 */

const CharacterContext = createContext();

export const useCharacter = () => {
  const ctx = useContext(CharacterContext);
  if (!ctx) throw new Error('useCharacter must be used within a CharacterProvider');
  return ctx;
};

export const CharacterProvider = ({ children }) => {
  const { currentUser } = useAuth();
  const [characters, setCharacters] = useState([]);
  const [activeCharacter, setActiveCharacterState] = useState(null);
  const [loading, setLoading] = useState(true);

  const reload = useCallback(async () => {
    if (!currentUser) {
      setCharacters([]);
      setActiveCharacterState(null);
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const [rosterRes, activeRes] = await Promise.allSettled([
        getMyCharacters(),
        getActiveCharacter(),
      ]);
      if (rosterRes.status === 'fulfilled') setCharacters(rosterRes.value.data || []);
      if (activeRes.status === 'fulfilled') {
        setActiveCharacterState(activeRes.value.data?.character || null);
      }
    } finally {
      setLoading(false);
    }
  }, [currentUser]);

  useEffect(() => {
    reload();
  }, [reload]);

  const switchCharacter = useCallback(async (characterId) => {
    const res = await setActiveCharacterApi(characterId);
    const chosen = res.data?.character || null;
    setActiveCharacterState(chosen);
    return chosen;
  }, []);

  const value = { characters, activeCharacter, switchCharacter, reload, loading };
  return <CharacterContext.Provider value={value}>{children}</CharacterContext.Provider>;
};
