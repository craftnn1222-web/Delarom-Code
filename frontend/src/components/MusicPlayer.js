import React, { useState, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useMusic } from '../contexts/MusicContext';
import { useAuth } from '../contexts/AuthContext';
import { toast } from 'sonner';
import {
  Play, Pause, Volume2, VolumeX, Music,
  ChevronUp, ChevronDown,
  SkipForward, SkipBack,
  Loader2, Settings, Upload, Check, AlertCircle,
  Folder, Trash2, ListMusic, X,
  Shuffle, Repeat1,
} from 'lucide-react';
import { Button } from './ui/button';
import { Slider } from './ui/slider';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const CHUNK_SIZE = 4 * 1024 * 1024;  // 4MB — matches backend CHUNK_LIMIT_BYTES
const DIRECT_LIMIT = 3 * 1024 * 1024; // files smaller than this go via direct POST

const trackDisplayNames = {
  global: 'Global Theme',
  ammeonon: 'Ammeonon',
  selindori: 'Selindori',
  'dhor-kuldor': 'Dhor-Kuldor',
  aigraels: 'Aigraels',
  'veiled-realms': 'Veiled Realms',
  tavern: 'Tavern',
};

const fmtSize = (n) => {
  if (!n) return '';
  if (n > 1024 * 1024) return `${(n / 1024 / 1024).toFixed(1)} MB`;
  return `${(n / 1024).toFixed(0)} KB`;
};

const authHeaders = () => {
  const token = localStorage.getItem('access_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
};

const AUDIO_EXT_RE = /\.(mp3|ogg|wav|m4a)$/i;

// Chunked upload for larger files. Returns the finalized track record.
async function chunkedUpload({ file, theme, onProgress }) {
  const initForm = new FormData();
  initForm.append('theme', theme);
  initForm.append('filename', file.name);
  initForm.append('size', String(file.size));
  const initResp = await fetch(`${BACKEND_URL}/api/admin/music/chunk/init`, {
    method: 'POST',
    headers: authHeaders(),
    body: initForm,
  });
  if (!initResp.ok) {
    const err = await initResp.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to start upload session.');
  }
  const { upload_id: uploadId } = await initResp.json();

  let sent = 0;
  const total = file.size;
  const chunks = Math.max(1, Math.ceil(total / CHUNK_SIZE));
  for (let i = 0; i < chunks; i++) {
    const start = i * CHUNK_SIZE;
    const end = Math.min(start + CHUNK_SIZE, total);
    const slice = file.slice(start, end);
    const form = new FormData();
    form.append('upload_id', uploadId);
    form.append('chunk', slice, `part-${i}`);
    const r = await fetch(`${BACKEND_URL}/api/admin/music/chunk/append`, {
      method: 'POST',
      headers: authHeaders(),
      body: form,
    });
    if (!r.ok) {
      const err = await r.json().catch(() => ({}));
      // Best-effort cleanup
      try {
        const abortForm = new FormData();
        abortForm.append('upload_id', uploadId);
        await fetch(`${BACKEND_URL}/api/admin/music/chunk/abort`, {
          method: 'POST', headers: authHeaders(), body: abortForm,
        });
      } catch (e) { /* swallow */ }
      throw new Error(err.detail || `Chunk ${i + 1}/${chunks} failed.`);
    }
    sent = end;
    onProgress?.(sent / total);
  }

  const finResp = await fetch(`${BACKEND_URL}/api/admin/music/chunk/finalize`, {
    method: 'POST',
    headers: { ...authHeaders(), 'Content-Type': 'application/json' },
    body: JSON.stringify({ upload_id: uploadId, theme, filename: file.name }),
  });
  if (!finResp.ok) {
    const err = await finResp.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to finalize upload.');
  }
  return finResp.json();
}

// Direct upload for small files (single-shot POST).
async function directUpload({ file, theme, onProgress }) {
  const form = new FormData();
  form.append('file', file);
  form.append('theme', theme);
  const resp = await fetch(`${BACKEND_URL}/api/admin/music/upload`, {
    method: 'POST',
    headers: authHeaders(),
    body: form,
  });
  onProgress?.(1);
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(err.detail || 'Upload failed');
  }
  return resp.json();
}

const MusicPlayer = () => {
  const { currentUser, loading, refreshUser } = useAuth();
  const {
    isPlaying, currentTrack, volume, isLoading, hasUserInteracted,
    showPlayer, currentTime, duration, error,
    togglePlay, setVolume, changeTrack,
    nextSong, prevSong, playSongAt,
    getCurrentTrackInfo, getAllTracks, refreshFromServer,
    getThemeMode, toggleShuffle, toggleRepeatOne,
  } = useMusic();

  const [isExpanded, setIsExpanded] = useState(false);
  const [showTrackList, setShowTrackList] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [editingTheme, setEditingTheme] = useState(null);
  const [uploads, setUploads] = useState([]);       // [{id, name, progress, status, error?}]
  const [isMuted, setIsMuted] = useState(false);
  const [prevVolume, setPrevVolume] = useState(volume);
  const [dragging, setDragging] = useState(false);

  const fileInputRef = useRef(null);
  const folderInputRef = useRef(null);
  const dropRef = useRef(null);
  const uidCounter = useRef(0);

  const trackInfo = getCurrentTrackInfo();
  const allTracks = getAllTracks();

  const isAdmin = currentUser?.role === 'admin';
  const isLoggedIn = !!currentUser;

  React.useEffect(() => {
    if (showSettings && !currentUser && !loading) {
      refreshUser();
    }
  }, [showSettings, currentUser, loading, refreshUser]);

  const formatTime = (time) => {
    if (isNaN(time)) return '0:00';
    const minutes = Math.floor(time / 60);
    const seconds = Math.floor(time % 60);
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  };

  const toggleMute = () => {
    if (isMuted) { setVolume(prevVolume); setIsMuted(false); }
    else { setPrevVolume(volume); setVolume(0); setIsMuted(true); }
  };

  const handleVolumeChange = (value) => {
    setVolume(value[0]);
    if (value[0] > 0) setIsMuted(false);
  };

  // Ingest a bag of files (from picker OR drag+drop) into the currently
  // editing theme, using chunked upload for anything ≥ DIRECT_LIMIT.
  const ingestFiles = useCallback(async (fileList) => {
    if (!editingTheme) {
      toast.error('Pick a theme first.');
      return;
    }
    const files = Array.from(fileList || []).filter((f) => AUDIO_EXT_RE.test(f.name));
    const rejected = Array.from(fileList || []).length - files.length;
    if (rejected > 0) {
      toast.warning(`${rejected} file(s) ignored — only .mp3, .ogg, .wav, .m4a are accepted.`);
    }
    if (!files.length) return;

    // Register progress rows
    const rows = files.map((f) => ({
      id: `u_${++uidCounter.current}`,
      name: f.name,
      size: f.size,
      progress: 0,
      status: 'queued',
    }));
    setUploads((prev) => [...prev, ...rows]);

    // Upload one at a time — keeps memory bounded and avoids swamping ingress.
    let succeeded = 0;
    let failed = 0;
    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      const rowId = rows[i].id;
      setUploads((prev) => prev.map((r) => r.id === rowId ? { ...r, status: 'uploading' } : r));
      try {
        const useChunked = file.size >= DIRECT_LIMIT;
        const onProgress = (p) => {
          setUploads((prev) => prev.map((r) => r.id === rowId ? { ...r, progress: p } : r));
        };
        if (useChunked) {
          await chunkedUpload({ file, theme: editingTheme, onProgress });
        } else {
          await directUpload({ file, theme: editingTheme, onProgress });
        }
        setUploads((prev) => prev.map((r) => r.id === rowId ? { ...r, progress: 1, status: 'done' } : r));
        succeeded += 1;
      } catch (e) {
        setUploads((prev) => prev.map((r) => r.id === rowId ? { ...r, status: 'failed', error: e.message } : r));
        toast.error(`${file.name}: ${e.message}`);
        failed += 1;
      }
    }
    await refreshFromServer();
    if (succeeded > 0) {
      toast.success(`Added ${succeeded} track${succeeded === 1 ? '' : 's'} to ${trackDisplayNames[editingTheme]}${failed ? ` (${failed} failed)` : ''}.`);
    } else if (failed > 0) {
      toast.error(`All ${failed} upload${failed === 1 ? '' : 's'} failed — see error rows above.`);
    }
  }, [editingTheme, refreshFromServer]);

  const onFilePickerChange = (e) => {
    ingestFiles(e.target.files);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };
  const onFolderPickerChange = (e) => {
    ingestFiles(e.target.files);
    if (folderInputRef.current) folderInputRef.current.value = '';
  };

  const onDrop = async (e) => {
    e.preventDefault();
    setDragging(false);
    if (!editingTheme) { toast.error('Pick a theme first.'); return; }
    const dt = e.dataTransfer;
    if (!dt) return;
    // Prefer webkit entries so folders are walked recursively.
    if (dt.items && dt.items.length && dt.items[0].webkitGetAsEntry) {
      const files = [];
      const walk = async (entry) => {
        if (entry.isFile) {
          const f = await new Promise((res) => entry.file(res));
          if (AUDIO_EXT_RE.test(f.name)) files.push(f);
        } else if (entry.isDirectory) {
          const reader = entry.createReader();
          const entries = await new Promise((res) => reader.readEntries(res));
          for (const child of entries) await walk(child);
        }
      };
      for (let i = 0; i < dt.items.length; i++) {
        const entry = dt.items[i].webkitGetAsEntry?.();
        if (entry) await walk(entry);
      }
      if (files.length) await ingestFiles(files);
      else toast.warning('No audio files found in the drop.');
    } else if (dt.files && dt.files.length) {
      await ingestFiles(dt.files);
    }
  };

  const onDragOver = (e) => { e.preventDefault(); setDragging(true); };
  const onDragLeave = (e) => { e.preventDefault(); setDragging(false); };

  const deleteTrack = async (theme, filename) => {
    if (!isAdmin) return;
    try {
      const resp = await fetch(`${BACKEND_URL}/api/admin/music/${theme}/${encodeURIComponent(filename)}`, {
        method: 'DELETE', headers: authHeaders(),
      });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error(err.detail || 'Delete failed');
      }
      toast.success('Track removed.');
      await refreshFromServer();
    } catch (e) {
      toast.error(e.message);
    }
  };

  const dismissUpload = (id) => setUploads((prev) => prev.filter((r) => r.id !== id));

  if (!showPlayer) return null;

  const currentPlaylist = allTracks[currentTrack]?.playlist || [];
  const currentIndex = allTracks[currentTrack]?.index || 0;
  const currentMode = getThemeMode(currentTrack);

  return (
    <AnimatePresence>
      <motion.div
        className="fixed bottom-4 left-4 z-50"
        initial={{ y: 100, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        exit={{ y: 100, opacity: 0 }}
        transition={{ type: 'spring', damping: 20 }}
        data-testid="music-player"
      >
        {!isExpanded ? (
          <motion.div className="flex items-center gap-2" layout>
            <Button
              onClick={togglePlay}
              className="w-12 h-12 rounded-full bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500 shadow-lg shadow-purple-500/30"
              data-testid="music-play-btn"
            >
              {isLoading ? <Loader2 className="w-5 h-5 animate-spin" />
                : isPlaying ? <Pause className="w-5 h-5" />
                : <Play className="w-5 h-5 ml-0.5" />}
            </Button>
            <Button
              onClick={() => setIsExpanded(true)}
              variant="ghost"
              className="w-8 h-8 rounded-full bg-black/60 hover:bg-black/80"
              data-testid="music-expand-btn"
            >
              <ChevronUp className="w-4 h-4" />
            </Button>
            {isPlaying && (
              <motion.div
                className="flex items-center gap-1 bg-black/60 px-3 py-1.5 rounded-full"
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
              >
                <Music className="w-3 h-3 text-purple-400" />
                <span className="text-xs text-gray-300 max-w-[140px] truncate">
                  {trackInfo.name || 'Nothing loaded'}
                </span>
                <div className="flex items-end gap-0.5 h-3 ml-1">
                  {[1, 2, 3].map((i) => (
                    <motion.div
                      key={i}
                      className="w-0.5 bg-purple-400 rounded-full"
                      animate={{ height: ['4px', '12px', '6px', '10px', '4px'] }}
                      transition={{ duration: 0.8, repeat: Infinity, delay: i * 0.1 }}
                    />
                  ))}
                </div>
              </motion.div>
            )}
          </motion.div>
        ) : (
          <motion.div
            className="bg-gray-900/95 border border-purple-500/30 rounded-2xl p-4 w-96 shadow-xl shadow-purple-500/10"
            layout
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            data-testid="music-player-expanded"
          >
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <Music className="w-5 h-5 text-purple-400" />
                <span className="text-sm font-semibold text-white">Music Player</span>
              </div>
              <Button
                onClick={() => setIsExpanded(false)}
                variant="ghost"
                size="sm"
                className="w-6 h-6 p-0 hover:bg-white/10"
                data-testid="music-collapse-btn"
              >
                <ChevronDown className="w-4 h-4" />
              </Button>
            </div>

            <div className="bg-black/40 rounded-lg p-3 mb-3">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-purple-600 to-pink-600 flex items-center justify-center">
                  {isPlaying ? (
                    <div className="flex items-end gap-0.5 h-6">
                      {[1, 2, 3, 4].map((i) => (
                        <motion.div
                          key={i}
                          className="w-1 bg-white rounded-full"
                          animate={{ height: ['8px', '24px', '12px', '20px', '8px'] }}
                          transition={{ duration: 0.6, repeat: Infinity, delay: i * 0.08 }}
                        />
                      ))}
                    </div>
                  ) : <Music className="w-6 h-6 text-white/80" />}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-white font-medium truncate" data-testid="music-song-name">
                    {trackInfo.songName || trackInfo.name || 'No song loaded'}
                  </p>
                  <p className="text-gray-400 text-xs truncate">{trackInfo.themeName || trackInfo.artist}</p>
                  {trackInfo.trackTotal ? (
                    <p className="text-purple-400 text-xs mt-0.5">
                      {trackDisplayNames[currentTrack] || 'Global'} · {trackInfo.trackIndex}/{trackInfo.trackTotal}
                    </p>
                  ) : (
                    <p className="text-purple-400 text-xs mt-0.5">
                      {trackDisplayNames[currentTrack] || 'Global'} · empty playlist
                    </p>
                  )}
                </div>
              </div>

              <div className="mt-3">
                <div className="h-1 bg-gray-700 rounded-full overflow-hidden">
                  <motion.div
                    className="h-full bg-gradient-to-r from-purple-500 to-pink-500"
                    style={{ width: duration > 0 ? `${(currentTime / duration) * 100}%` : '0%' }}
                  />
                </div>
                <div className="flex justify-between mt-1 text-xs text-gray-500">
                  <span>{formatTime(currentTime)}</span>
                  <span>{formatTime(duration)}</span>
                </div>
              </div>
            </div>

            {error && (
              <div className="mb-3 p-2 bg-red-500/20 rounded-lg flex items-center gap-2">
                <AlertCircle className="w-4 h-4 text-red-400" />
                <span className="text-xs text-red-300">{error}</span>
              </div>
            )}

            {/* Controls: shuffle / prev / play / next / repeat-one */}
            <div className="flex items-center justify-center gap-3 mb-3">
              <Button
                onClick={() => toggleShuffle()}
                variant="ghost"
                title={currentMode.shuffle ? 'Shuffle on — click to turn off' : 'Turn shuffle on'}
                className={`w-9 h-9 rounded-full transition ${
                  currentMode.shuffle
                    ? 'bg-purple-600/40 text-purple-100 ring-1 ring-purple-400/60'
                    : 'bg-white/5 hover:bg-white/10 text-gray-300'
                }`}
                disabled={!currentPlaylist.length}
                data-testid="music-shuffle-btn"
                aria-pressed={currentMode.shuffle}
              >
                <Shuffle className="w-4 h-4" />
              </Button>
              <Button
                onClick={prevSong}
                variant="ghost"
                className="w-10 h-10 rounded-full bg-white/5 hover:bg-white/10 text-white"
                disabled={!currentPlaylist.length}
                data-testid="music-prev-btn"
              >
                <SkipBack className="w-4 h-4" />
              </Button>
              <Button
                onClick={togglePlay}
                className="w-14 h-14 rounded-full bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500"
                data-testid="music-play-expanded-btn"
              >
                {isLoading ? <Loader2 className="w-5 h-5 animate-spin" />
                  : isPlaying ? <Pause className="w-6 h-6" />
                  : <Play className="w-6 h-6 ml-0.5" />}
              </Button>
              <Button
                onClick={nextSong}
                variant="ghost"
                className="w-10 h-10 rounded-full bg-white/5 hover:bg-white/10 text-white"
                disabled={!currentPlaylist.length}
                data-testid="music-next-btn"
              >
                <SkipForward className="w-4 h-4" />
              </Button>
              <Button
                onClick={() => toggleRepeatOne()}
                variant="ghost"
                title={currentMode.repeatOne ? 'Repeat-one on — click to turn off' : 'Repeat this track forever'}
                className={`w-9 h-9 rounded-full transition ${
                  currentMode.repeatOne
                    ? 'bg-pink-600/40 text-pink-100 ring-1 ring-pink-400/60'
                    : 'bg-white/5 hover:bg-white/10 text-gray-300'
                }`}
                disabled={!currentPlaylist.length}
                data-testid="music-repeat-one-btn"
                aria-pressed={currentMode.repeatOne}
              >
                <Repeat1 className="w-4 h-4" />
              </Button>
            </div>

            <div className="flex items-center gap-2 mb-3">
              <Button
                onClick={toggleMute}
                variant="ghost"
                size="sm"
                className="w-8 h-8 p-0 hover:bg-white/10"
                data-testid="music-mute-btn"
              >
                {isMuted || volume === 0 ? <VolumeX className="w-4 h-4 text-gray-400" /> : <Volume2 className="w-4 h-4 text-gray-400" />}
              </Button>
              <Slider
                value={[volume]}
                onValueChange={handleVolumeChange}
                max={1}
                step={0.01}
                className="flex-1"
              />
              <span className="text-xs text-gray-500 w-8">{Math.round(volume * 100)}%</span>
            </div>

            <div>
              <div className="flex gap-2 mb-2">
                <Button
                  onClick={() => { setShowTrackList(!showTrackList); setShowSettings(false); }}
                  variant="ghost"
                  className={`flex-1 justify-between text-sm hover:bg-white/10 ${showTrackList ? 'text-purple-400' : 'text-gray-400 hover:text-white'}`}
                  data-testid="music-themes-btn"
                >
                  <span>Themes &amp; Playlist</span>
                  <ListMusic className="w-4 h-4" />
                </Button>
                <Button
                  onClick={() => { setShowSettings(!showSettings); setShowTrackList(false); }}
                  variant="ghost"
                  className={`justify-center text-sm hover:bg-white/10 ${showSettings ? 'text-purple-400' : 'text-gray-400 hover:text-white'}`}
                  title="Upload Music"
                  data-testid="music-settings-btn"
                >
                  <Settings className="w-4 h-4" />
                </Button>
              </div>

              {/* Theme + playlist listing */}
              <AnimatePresence>
                {showTrackList && (
                  <motion.div
                    className="mt-2 space-y-2 max-h-72 overflow-y-auto"
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    data-testid="music-track-list"
                  >
                    {Object.entries(allTracks).map(([themeKey, theme]) => {
                      const isCurrent = currentTrack === themeKey;
                      const rowMode = getThemeMode(themeKey);
                      return (
                        <div
                          key={themeKey}
                          className={`rounded-lg border ${isCurrent ? 'border-purple-500/40 bg-purple-600/10' : 'border-white/5 bg-black/20'}`}
                          data-testid={`track-${themeKey}`}
                        >
                          <div className="flex items-stretch">
                            <button
                              onClick={() => {
                                if (theme.playlist?.length) changeTrack(themeKey);
                                else if (isAdmin) {
                                  setShowTrackList(false);
                                  setShowSettings(true);
                                  setEditingTheme(themeKey);
                                }
                              }}
                              className="flex-1 text-left px-3 py-2 text-sm"
                            >
                              <div className="flex items-center justify-between">
                                <span className={`font-medium ${isCurrent ? 'text-purple-200' : 'text-white'}`}>
                                  {trackDisplayNames[themeKey] || themeKey}
                                </span>
                                <span className="text-[10px] text-gray-500 uppercase tracking-widest">
                                  {theme.playlist?.length || 0} track{theme.playlist?.length === 1 ? '' : 's'}
                                </span>
                              </div>
                            </button>
                            <div className="flex items-center gap-1 pr-2">
                              <button
                                onClick={(e) => { e.stopPropagation(); toggleShuffle(themeKey); }}
                                title={rowMode.shuffle ? 'Shuffle on' : 'Turn shuffle on'}
                                className={`p-1.5 rounded transition ${
                                  rowMode.shuffle
                                    ? 'bg-purple-600/40 text-purple-100'
                                    : 'text-gray-500 hover:text-white hover:bg-white/5'
                                }`}
                                data-testid={`row-shuffle-${themeKey}`}
                                aria-pressed={rowMode.shuffle}
                              >
                                <Shuffle className="w-3.5 h-3.5" />
                              </button>
                              <button
                                onClick={(e) => { e.stopPropagation(); toggleRepeatOne(themeKey); }}
                                title={rowMode.repeatOne ? 'Repeat-one on' : 'Repeat this track forever'}
                                className={`p-1.5 rounded transition ${
                                  rowMode.repeatOne
                                    ? 'bg-pink-600/40 text-pink-100'
                                    : 'text-gray-500 hover:text-white hover:bg-white/5'
                                }`}
                                data-testid={`row-repeat-one-${themeKey}`}
                                aria-pressed={rowMode.repeatOne}
                              >
                                <Repeat1 className="w-3.5 h-3.5" />
                              </button>
                            </div>
                          </div>
                          {isCurrent && theme.playlist?.length ? (
                            <div className="border-t border-white/5 divide-y divide-white/5">
                              {theme.playlist.map((song, idx) => (
                                <div key={song.id + idx} className={`flex items-center gap-2 px-3 py-1.5 text-xs ${idx === currentIndex ? 'bg-purple-500/10' : ''}`}>
                                  <button
                                    onClick={() => playSongAt(themeKey, idx)}
                                    className="text-left flex-1 min-w-0"
                                    data-testid={`playlist-song-${themeKey}-${idx}`}
                                  >
                                    <div className={`truncate ${idx === currentIndex ? 'text-purple-100' : 'text-gray-300'}`}>
                                      {idx === currentIndex && isPlaying ? '♪ ' : ''}{song.name}
                                    </div>
                                    <div className="text-gray-500 text-[10px]">{fmtSize(song.size)}</div>
                                  </button>
                                  {isAdmin && (
                                    <button
                                      onClick={() => deleteTrack(themeKey, song.filename)}
                                      title="Delete track"
                                      className="p-1 rounded hover:bg-red-500/20 text-red-300"
                                      data-testid={`delete-song-${themeKey}-${idx}`}
                                    >
                                      <Trash2 className="w-3.5 h-3.5" />
                                    </button>
                                  )}
                                </div>
                              ))}
                            </div>
                          ) : null}
                        </div>
                      );
                    })}
                  </motion.div>
                )}
              </AnimatePresence>

              {/* Settings + upload panel */}
              <AnimatePresence>
                {showSettings && (
                  <motion.div
                    className="mt-2 space-y-2"
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    data-testid="music-settings-panel"
                  >
                    {loading ? (
                      <p className="text-xs text-gray-400 text-center py-2">Loading...</p>
                    ) : !isLoggedIn ? (
                      <p className="text-xs text-gray-400 text-center py-2">Please log in to upload music.</p>
                    ) : !isAdmin ? (
                      <p className="text-xs text-gray-400 text-center py-2">Only admins can upload music.</p>
                    ) : (
                      <>
                        <p className="text-xs text-gray-400 mb-2">
                          Pick a theme, then drop files or a folder to add tracks. Multiple tracks per theme are supported and will play back-to-back.
                        </p>
                        <div className="grid grid-cols-2 gap-1 mb-2">
                          {Object.keys(allTracks).map((k) => (
                            <button
                              key={k}
                              onClick={() => setEditingTheme(k)}
                              className={`text-xs px-2 py-1.5 rounded ${editingTheme === k ? 'bg-purple-600 text-white' : 'bg-white/5 text-gray-300 hover:bg-white/10'}`}
                              data-testid={`upload-theme-${k}`}
                            >
                              {trackDisplayNames[k]}
                              <span className="ml-1 text-[10px] opacity-70">({allTracks[k].playlist?.length || 0})</span>
                            </button>
                          ))}
                        </div>

                        {editingTheme && (
                          <>
                            <input
                              ref={fileInputRef}
                              type="file"
                              accept=".mp3,.ogg,.wav,.m4a,audio/*"
                              onChange={onFilePickerChange}
                              multiple
                              className="hidden"
                              data-testid="music-file-input"
                            />
                            <input
                              ref={folderInputRef}
                              type="file"
                              onChange={onFolderPickerChange}
                              multiple
                              className="hidden"
                              data-testid="music-folder-input"
                              {...{ webkitdirectory: '', directory: '' }}
                            />
                            <div
                              ref={dropRef}
                              onDrop={onDrop}
                              onDragOver={onDragOver}
                              onDragLeave={onDragLeave}
                              className={`rounded-lg border-2 border-dashed p-4 text-center transition ${dragging ? 'border-purple-400 bg-purple-500/10' : 'border-white/15 bg-black/20'}`}
                              data-testid="music-drop-zone"
                            >
                              <div className="text-xs text-white mb-2">
                                Drop audio files or a folder for
                                <span className="text-purple-300 font-semibold"> {trackDisplayNames[editingTheme]}</span>
                              </div>
                              <div className="flex gap-2 justify-center flex-wrap">
                                <Button
                                  size="sm"
                                  className="bg-purple-600 hover:bg-purple-500"
                                  onClick={() => fileInputRef.current?.click()}
                                  data-testid="music-choose-files-btn"
                                >
                                  <Upload className="w-3.5 h-3.5 mr-1" />
                                  Choose files
                                </Button>
                                <Button
                                  size="sm"
                                  className="bg-fuchsia-700 hover:bg-fuchsia-600"
                                  onClick={() => folderInputRef.current?.click()}
                                  data-testid="music-choose-folder-btn"
                                >
                                  <Folder className="w-3.5 h-3.5 mr-1" />
                                  Choose folder
                                </Button>
                              </div>
                              <div className="text-[10px] text-gray-500 mt-2">
                                .mp3 · .ogg · .wav · .m4a · files &gt; 3MB use chunked upload (up to 200MB each)
                              </div>
                            </div>
                          </>
                        )}

                        {/* Live upload progress rows */}
                        {uploads.length > 0 && (
                          <div className="mt-2 space-y-1 max-h-40 overflow-y-auto">
                            {uploads.map((u) => (
                              <div key={u.id} className="text-xs bg-black/30 rounded px-2 py-1.5" data-testid={`upload-row-${u.id}`}>
                                <div className="flex items-center gap-2">
                                  {u.status === 'done' ? <Check className="w-3.5 h-3.5 text-green-400" />
                                    : u.status === 'failed' ? <AlertCircle className="w-3.5 h-3.5 text-red-400" />
                                    : <Loader2 className="w-3.5 h-3.5 animate-spin text-purple-300" />}
                                  <div className="flex-1 min-w-0">
                                    <div className="truncate text-white">{u.name}</div>
                                    <div className="text-[10px] text-gray-500">
                                      {u.status === 'failed' ? u.error : `${fmtSize(u.size)} · ${(u.progress * 100).toFixed(0)}%`}
                                    </div>
                                  </div>
                                  <button onClick={() => dismissUpload(u.id)} className="p-1 hover:bg-white/10 rounded">
                                    <X className="w-3 h-3 text-gray-400" />
                                  </button>
                                </div>
                                {u.status !== 'failed' && (
                                  <div className="h-1 bg-gray-700 rounded-full mt-1 overflow-hidden">
                                    <div className="h-full bg-gradient-to-r from-purple-500 to-pink-500" style={{ width: `${u.progress * 100}%` }} />
                                  </div>
                                )}
                              </div>
                            ))}
                          </div>
                        )}
                      </>
                    )}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            {!hasUserInteracted && (
              <motion.div
                className="mt-3 p-2 bg-purple-500/20 rounded-lg text-center"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
              >
                <p className="text-xs text-purple-300">Click play to start the ambient music</p>
              </motion.div>
            )}
          </motion.div>
        )}
      </motion.div>
    </AnimatePresence>
  );
};

export default MusicPlayer;
