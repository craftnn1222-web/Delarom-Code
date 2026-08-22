import React, { createContext, useContext, useState, useRef, useEffect, useCallback } from 'react';

const MusicContext = createContext();

// Theme metadata (descriptive only — playlist arrays come from the backend).
const THEME_META = {
  global:          { name: 'Global Theme',        artist: 'Ambient',           description: 'Main ambient theme' },
  ammeonon:        { name: 'Ammeonon Theme',      artist: 'Human Kingdom',     description: 'Epic theme for the Human Kingdom' },
  selindori:       { name: 'Selindori Theme',     artist: 'Elven Realm',       description: 'Mystical bardcore for the Elven Realm' },
  'dhor-kuldor':   { name: 'Dhor-Kuldor Theme',   artist: 'Dwarven Mountains', description: 'Deep epic theme for the Dwarven Mountains' },
  aigraels:        { name: 'Aigraels Theme',      artist: 'Wartorn Nation',    description: 'Dark battle tension for the Wartorn Nation' },
  'veiled-realms': { name: 'Veiled Realms Theme', artist: 'Hidden Kingdoms',   description: 'Mysterious ambience for the Hidden Kingdoms' },
  tavern:          { name: 'Tavern Theme',        artist: 'Medieval Inn',      description: 'Lively tavern atmosphere' },
};

const emptyPlaylistState = () => Object.fromEntries(
  Object.entries(THEME_META).map(([k, v]) => [k, { ...v, playlist: [], index: 0 }])
);

// Persistence — only remember the index per theme (playlists themselves are
// authoritatively fetched from the backend on mount so they're always fresh).
const loadIndex = () => {
  try {
    const raw = localStorage.getItem('delarom_music_indexes');
    return raw ? JSON.parse(raw) : {};
  } catch (e) { return {}; }
};
const saveIndex = (indexes) => {
  try { localStorage.setItem('delarom_music_indexes', JSON.stringify(indexes)); }
  catch (e) { /* ignore quota errors */ }
};

// Per-theme playback modes: { [themeKey]: { shuffle: bool, repeatOne: bool } }
const loadModes = () => {
  try {
    const raw = localStorage.getItem('delarom_music_modes');
    return raw ? JSON.parse(raw) : {};
  } catch (e) { return {}; }
};
const saveModes = (modes) => {
  try { localStorage.setItem('delarom_music_modes', JSON.stringify(modes)); }
  catch (e) { /* ignore */ }
};

const emptyModes = () => Object.fromEntries(
  Object.keys(THEME_META).map((k) => [k, { shuffle: false, repeatOne: false }])
);

const buildInitialModes = () => {
  const state = emptyModes();
  const saved = loadModes();
  Object.keys(state).forEach((k) => {
    if (saved[k] && typeof saved[k] === 'object') {
      state[k] = {
        shuffle: !!saved[k].shuffle,
        repeatOne: !!saved[k].repeatOne,
      };
    }
  });
  return state;
};

// Pick a random index in [0, len) that is not `avoid` (if the playlist has ≥ 2 songs).
const pickShuffleIndex = (len, avoid) => {
  if (len <= 1) return 0;
  let n = Math.floor(Math.random() * len);
  if (n === avoid) n = (n + 1) % len;
  return n;
};

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const buildInitial = () => {
  const state = emptyPlaylistState();
  const saved = loadIndex();
  Object.keys(state).forEach((k) => {
    if (Number.isInteger(saved[k])) state[k].index = saved[k];
  });
  return state;
};

export const MusicProvider = ({ children }) => {
  const audioRef = useRef(null);
  const currentTrackRef = useRef('global');
  const themeModesRef = useRef(buildInitialModes());

  const [musicTracks, setMusicTracks] = useState(buildInitial);
  const [themeModes, setThemeModes] = useState(themeModesRef.current);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTrack, setCurrentTrack] = useState('global');
  const [volume, setVolume] = useState(0.3);
  const [isLoading, setIsLoading] = useState(false);
  const [hasUserInteracted, setHasUserInteracted] = useState(false);
  const [showPlayer, setShowPlayer] = useState(true);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [error, setError] = useState(null);

  // Keep a live ref of currentTrack so audio event handlers (bound once) can
  // read the up-to-date theme without being re-registered.
  useEffect(() => { currentTrackRef.current = currentTrack; }, [currentTrack]);

  // Fetch full playlists from backend on mount + whenever admin refreshes.
  const refreshFromServer = useCallback(async () => {
    try {
      const resp = await fetch(`${BACKEND_URL}/api/music/list`);
      if (!resp.ok) return;
      const data = await resp.json();
      const themes = data?.themes || {};
      setMusicTracks((prev) => {
        const next = { ...prev };
        Object.keys(THEME_META).forEach((theme) => {
          const backendTracks = (themes[theme] || []).map((t) => ({
            id: t.id,
            filename: t.filename,
            name: t.name || t.filename,
            url: `${BACKEND_URL}${t.url}`,
            size: t.size || 0,
            legacy: !!t.legacy,
          }));
          const prevIdx = prev[theme]?.index || 0;
          next[theme] = {
            ...THEME_META[theme],
            playlist: backendTracks,
            index: backendTracks.length ? Math.min(prevIdx, backendTracks.length - 1) : 0,
          };
        });
        return next;
      });
    } catch (e) {
      // Network hiccup — leave state alone
      console.debug('music refresh failed:', e);
    }
  }, []);

  useEffect(() => { refreshFromServer(); }, [refreshFromServer]);

  // Helpers ------------------------------------------------------

  const getCurrentTrackTheme = useCallback(() => (
    musicTracks[currentTrack] || musicTracks.global || null
  ), [musicTracks, currentTrack]);

  const getCurrentSong = useCallback(() => {
    const t = musicTracks[currentTrack];
    if (!t || !t.playlist?.length) return null;
    return t.playlist[Math.min(t.index || 0, t.playlist.length - 1)] || null;
  }, [musicTracks, currentTrack]);

  // Initialize audio element (one-time)
  useEffect(() => {
    if (audioRef.current) return;
    const a = new Audio();
    a.preload = 'auto';
    audioRef.current = a;

    a.addEventListener('loadstart', () => { setIsLoading(true); setError(null); });
    a.addEventListener('canplay', () => setIsLoading(false));
    a.addEventListener('timeupdate', () => setCurrentTime(a.currentTime));
    a.addEventListener('loadedmetadata', () => setDuration(a.duration));
    a.addEventListener('error', () => {
      setIsLoading(false);
      setError('Failed to load audio');
    });
    // Auto-advance on end — honours the current theme's shuffle / repeat-one modes
    a.addEventListener('ended', () => {
      const theme = currentTrackRef.current;
      const mode = themeModesRef.current[theme] || { shuffle: false, repeatOne: false };

      // Repeat-one wins outright — just re-play the current track.
      if (mode.repeatOne) {
        try { a.currentTime = 0; } catch (e) { /* some codecs disallow seek before ready */ }
        a.play().catch(() => { /* autoplay guard */ });
        return;
      }

      setMusicTracks((prev) => {
        const t = prev[theme];
        if (!t || !t.playlist?.length) return prev;
        const nextIdx = mode.shuffle
          ? pickShuffleIndex(t.playlist.length, t.index)
          : (t.index + 1) % t.playlist.length;
        const next = { ...prev, [theme]: { ...t, index: nextIdx } };
        // Persist
        const idxs = {}; Object.keys(next).forEach((k) => { idxs[k] = next[k].index; });
        saveIndex(idxs);
        // Kick the audio element to the new track.
        const song = t.playlist[nextIdx];
        if (song && audioRef.current) {
          requestAnimationFrame(() => {
            audioRef.current.src = song.url;
            audioRef.current.load();
            audioRef.current.play().catch(() => { /* autoplay guard */ });
          });
        }
        return next;
      });
    });

    return () => { a.pause(); a.src = ''; };
  }, []);

  // Apply volume
  useEffect(() => {
    if (audioRef.current) audioRef.current.volume = volume;
  }, [volume]);

  // When the current playlist/index changes and the audio has no src yet,
  // pre-load the current song so metadata is ready.
  useEffect(() => {
    const song = getCurrentSong();
    const a = audioRef.current;
    if (!a || !song) return;
    if (!a.src || !a.src.includes(encodeURI(song.filename))) {
      a.src = song.url;
      a.load();
    }
  }, [getCurrentSong]);

  // Persist index whenever a playlist advances via a caller.
  useEffect(() => {
    const idxs = {};
    Object.keys(musicTracks).forEach((k) => { idxs[k] = musicTracks[k].index || 0; });
    saveIndex(idxs);
  }, [musicTracks]);

  // Actions ------------------------------------------------------

  const _playAt = useCallback((theme, index, resumePlaying) => {
    const t = musicTracks[theme];
    if (!t || !t.playlist?.length) return;
    const bounded = ((index % t.playlist.length) + t.playlist.length) % t.playlist.length;
    setMusicTracks((prev) => ({ ...prev, [theme]: { ...prev[theme], index: bounded } }));
    const song = t.playlist[bounded];
    const a = audioRef.current;
    if (!a || !song) return;
    a.pause();
    a.src = song.url;
    a.load();
    setError(null);
    if (resumePlaying) {
      a.play().then(() => setIsPlaying(true)).catch(() => setError('Click play to start music'));
    }
  }, [musicTracks]);

  const togglePlay = useCallback(() => {
    const a = audioRef.current;
    if (!a) return;
    const song = getCurrentSong();
    if (!song) { setError('No tracks uploaded for this theme yet.'); return; }

    if (!a.src || !a.src.includes(encodeURI(song.filename))) {
      a.src = song.url;
      a.load();
    }
    if (!hasUserInteracted) setHasUserInteracted(true);

    if (isPlaying) {
      a.pause();
      setIsPlaying(false);
    } else {
      a.play()
        .then(() => { setIsPlaying(true); setError(null); })
        .catch(() => setError('Failed to play audio'));
    }
  }, [isPlaying, hasUserInteracted, getCurrentSong]);

  const changeTrack = useCallback((themeKey) => {
    if (!musicTracks[themeKey]) return;
    if (themeKey === currentTrack) return;
    setCurrentTrack(themeKey);
    const t = musicTracks[themeKey];
    const song = t.playlist?.[t.index || 0];
    const a = audioRef.current;
    if (a && song) {
      const wasPlaying = isPlaying;
      a.pause();
      a.src = song.url;
      a.load();
      if (wasPlaying && hasUserInteracted) {
        a.play().then(() => setIsPlaying(true)).catch(() => { /* autoplay guard */ });
      }
    } else if (a) {
      a.pause();
      a.src = '';
      setIsPlaying(false);
    }
    setError(null);
  }, [currentTrack, musicTracks, isPlaying, hasUserInteracted]);

  const nextSong = useCallback(() => {
    const t = musicTracks[currentTrack];
    if (!t || !t.playlist?.length) return;
    _playAt(currentTrack, (t.index || 0) + 1, isPlaying);
  }, [currentTrack, musicTracks, isPlaying, _playAt]);

  const prevSong = useCallback(() => {
    const t = musicTracks[currentTrack];
    if (!t || !t.playlist?.length) return;
    _playAt(currentTrack, (t.index || 0) - 1, isPlaying);
  }, [currentTrack, musicTracks, isPlaying, _playAt]);

  const playSongAt = useCallback((themeKey, index) => {
    if (!musicTracks[themeKey]) return;
    if (themeKey !== currentTrack) setCurrentTrack(themeKey);
    if (!hasUserInteracted) setHasUserInteracted(true);
    _playAt(themeKey, index, true);
  }, [musicTracks, currentTrack, hasUserInteracted, _playAt]);

  const seekTo = useCallback((time) => {
    if (audioRef.current) audioRef.current.currentTime = time;
  }, []);

  const getCurrentTrackInfo = useCallback(() => {
    const t = getCurrentTrackTheme();
    const song = getCurrentSong();
    if (!t) return { name: 'No theme', artist: '', description: '', url: '' };
    if (!song) {
      return {
        name: t.name,
        artist: t.artist,
        description: t.description,
        url: '',
        songName: '',
      };
    }
    return {
      name: song.name,
      artist: t.artist,
      description: t.description,
      url: song.url,
      songName: song.name,
      themeName: t.name,
      trackIndex: t.playlist.indexOf(song) + 1,
      trackTotal: t.playlist.length,
    };
  }, [getCurrentTrackTheme, getCurrentSong]);

  const getAllTracks = useCallback(() => musicTracks, [musicTracks]);

  // Per-theme playback mode helpers -----------------------------
  // Keep a ref in sync so the audio 'ended' handler (bound once) sees the
  // latest modes without needing to be re-registered.
  useEffect(() => {
    themeModesRef.current = themeModes;
    saveModes(themeModes);
  }, [themeModes]);

  const _updateMode = useCallback((themeKey, patch) => {
    setThemeModes((prev) => {
      if (!prev[themeKey]) return prev;
      return { ...prev, [themeKey]: { ...prev[themeKey], ...patch } };
    });
  }, []);

  const toggleShuffle = useCallback((themeKey) => {
    const key = themeKey || currentTrack;
    const cur = themeModesRef.current[key] || { shuffle: false, repeatOne: false };
    _updateMode(key, { shuffle: !cur.shuffle });
  }, [currentTrack, _updateMode]);

  const toggleRepeatOne = useCallback((themeKey) => {
    const key = themeKey || currentTrack;
    const cur = themeModesRef.current[key] || { shuffle: false, repeatOne: false };
    _updateMode(key, { repeatOne: !cur.repeatOne });
  }, [currentTrack, _updateMode]);

  const getThemeMode = useCallback((themeKey) => (
    themeModes[themeKey || currentTrack] || { shuffle: false, repeatOne: false }
  ), [themeModes, currentTrack]);

  // Compat shim so existing components that called `updateTrackUrl` still work,
  // but funnel through a refresh so newly-uploaded playlist entries appear.
  const updateTrackUrl = useCallback(async (_themeKey, _url, _name) => {
    await refreshFromServer();
  }, [refreshFromServer]);

  const value = {
    isPlaying,
    currentTrack,
    volume,
    isLoading,
    hasUserInteracted,
    showPlayer,
    currentTime,
    duration,
    error,
    togglePlay,
    setVolume,
    changeTrack,
    nextSong,
    prevSong,
    playSongAt,
    seekTo,
    getCurrentTrackInfo,
    getAllTracks,
    setShowPlayer,
    updateTrackUrl,
    refreshFromServer,
    musicTracks,
    themeModes,
    toggleShuffle,
    toggleRepeatOne,
    getThemeMode,
  };

  return (
    <MusicContext.Provider value={value}>
      {children}
    </MusicContext.Provider>
  );
};

export const useMusic = () => {
  const context = useContext(MusicContext);
  if (!context) {
    throw new Error('useMusic must be used within a MusicProvider');
  }
  return context;
};

export default MusicContext;
