import React, { useEffect, useState, useCallback } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import api from '../utils/api';
import { toast } from 'sonner';
import AnimatedBackground from '../components/AnimatedBackground';
import Navbar from '../components/Navbar';
import WorldClock from '../components/WorldClock';
import TavernBoard from '../components/TavernBoard';
import { Button } from '../components/ui/button';
import { Textarea } from '../components/ui/textarea';
import { ArrowLeft, Dice6, Sparkles, Trash2, Users, Flame, Heart, UserMinus, Scale, Lock, ShieldAlert, Swords } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import FactionBadge from '../components/factions/FactionBadge';
import useFactionBadges from '../hooks/useFactionBadges';
import TrialPanel from '../components/TrialPanel';

const LocationRP = () => {
  const params = useParams();
  const navigate = useNavigate();
  const { currentUser: user } = useAuth();
  
  // Support both old route (/nations/:nationName/:locationName) and new route (/roleplay/:nation/:locationSlug)
  const nation = params.nation || params.nationName;
  const locationSlug = params.locationSlug || params.locationName;
  
  const [actions, setActions] = useState([]);
  const [actionText, setActionText] = useState('');
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [deletingId, setDeletingId] = useState(null);
  const [sceneState, setSceneState] = useState({ npcs: [], events: [] });
  // The character_id used by the backend for scene-state (always the user's first character).
  // Needed so we can call companion bond/dismiss endpoints on behalf of that same character.
  const [primaryCharacterId, setPrimaryCharacterId] = useState(null);
  const [dismissingCompanionId, setDismissingCompanionId] = useState(null);

  // ---------- Law system ----------
  const [rapSheet, setRapSheet] = useState(null);
  const [escapeText, setEscapeText] = useState('');
  const [surrendering, setSurrendering] = useState(false);
  const [escaping, setEscaping] = useState(false);
  const [trialResult, setTrialResult] = useState(null); // { trial, imprisonment }
  const [activeTrial, setActiveTrial] = useState(null);

  const imprisonment = rapSheet?.imprisonment || null;
  const isImprisonedHere =
    imprisonment &&
    imprisonment.jail_location === locationSlug &&
    imprisonment.nation === nation;
  const isOnTrialHere =
    activeTrial &&
    activeTrial.courthouse_location === locationSlug &&
    activeTrial.nation === nation;
  const bountyHere = (rapSheet?.bounties || []).find((b) => b.nation === nation);

  const fetchActiveTrial = useCallback(async () => {
    if (!primaryCharacterId) return;
    try {
      const res = await api.get(`/characters/${primaryCharacterId}/trial`);
      setActiveTrial(res.data?.trial || null);
    } catch (err) {
      console.error('Failed to load trial state:', err);
      setActiveTrial(null);
    }
  }, [primaryCharacterId]);

  useEffect(() => {
    fetchActiveTrial();
  }, [fetchActiveTrial, locationSlug]);

  // Faction badge lookups for action authors in the scene feed.
  const actionCharIds = actions.map((a) => a.character_id).filter(Boolean);
  const factionsByChar = useFactionBadges(actionCharIds);

  // Rival territory cue: any active rivalry whose rival_home == current nation.
  const rivalsHere = (sceneState.faction_rivalries || []).filter((r) => r.in_their_territory);
  const sceneRivalToast = rivalsHere[0] || null;

  // One-time toast per nation/location entry telling the player they're in rival turf.
  // Reads/writes a session marker so leaving and returning re-fires the alert.
  useEffect(() => {
    if (!sceneRivalToast) return;
    const key = `rp_rival_warn::${nation}::${locationSlug}::${sceneRivalToast.slug}`;
    if (sessionStorage.getItem(key)) return;
    sessionStorage.setItem(key, '1');
    toast.warning(
      `You walk in ${sceneRivalToast.name}'s home soil. Watch your tongue — your colours are not yet known.`,
      { duration: 7000 },
    );
  }, [sceneRivalToast, nation, locationSlug]);

  const locationDisplayName = locationSlug ? locationSlug.split('-').map(word => 
    word.charAt(0).toUpperCase() + word.slice(1)
  ).join(' ') : 'Location';

  // Check if user can delete a specific post
  const canDelete = (action) => {
    if (!user) return false;
    const isAdminOrMod = user.role === 'admin' || user.role === 'moderator';
    const isOwner = action.user_id === user.id;
    return isAdminOrMod || isOwner;
  };

  const fetchActions = useCallback(async () => {
    try {
      const response = await api.get(`/locations/${nation}/${locationSlug}/roleplay`);
      setActions(response.data);
    } catch (error) {
      console.error('Failed to load roleplay history:', error);
    } finally {
      setLoading(false);
    }
  }, [nation, locationSlug]);

  const fetchSceneState = useCallback(async () => {
    try {
      const response = await api.get(`/locations/${nation}/${locationSlug}/scene-state`);
      setSceneState(response.data || { npcs: [], events: [] });
    } catch (error) {
      // Non-critical — log for debugging, leave previous scene state intact so
      // the UI doesn't flicker when the scene-state endpoint is unavailable.
      console.error('Failed to refresh scene state:', error);
    }
  }, [nation, locationSlug]);

  // Pull the user's primary character so we can dismiss companions on their behalf.
  // The backend scene-state endpoint always uses the first character of the user;
  // we mirror that selection here so the IDs match.
  useEffect(() => {
    let cancelled = false;
    const loadChar = async () => {
      try {
        const res = await api.get('/characters');
        if (!cancelled && Array.isArray(res.data) && res.data.length > 0) {
          setPrimaryCharacterId(res.data[0].id);
        }
      } catch (err) {
        console.error('Failed to load characters for companion control:', err);
      }
    };
    loadChar();
    return () => { cancelled = true; };
  }, []);

  const handleDismissCompanion = async (npc) => {
    if (!primaryCharacterId) {
      toast.error('No character available to dismiss this companion.');
      return;
    }
    if (!window.confirm(`Dismiss ${npc.name}? They will return to their original location.`)) {
      return;
    }
    setDismissingCompanionId(npc.id);
    try {
      const res = await api.post(`/npcs/${npc.id}/companion/dismiss`, {
        character_id: primaryCharacterId,
      });
      toast.success(res.data?.message || `${npc.name} parts ways with you.`);
      await fetchSceneState();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to dismiss companion');
    } finally {
      setDismissingCompanionId(null);
    }
  };

  // ---------- Law system handlers ----------

  const fetchRapSheet = async (charId) => {
    const id = charId || primaryCharacterId;
    if (!id) return;
    try {
      const res = await api.get(`/characters/${id}/rap-sheet`);
      setRapSheet(res.data);
    } catch (err) {
      console.error('Failed to load rap sheet:', err);
    }
  };

  useEffect(() => {
    if (primaryCharacterId) fetchRapSheet(primaryCharacterId);
    // eslint-disable-next-line
  }, [primaryCharacterId, nation, locationSlug]);

  const handleSurrender = async () => {
    if (!primaryCharacterId) return;
    if (!window.confirm(
      `Surrender to the authorities here? You will be moved to the city courthouse to stand trial — you may defend yourself up to 5 times before the verdict.`
    )) return;
    setSurrendering(true);
    setTrialResult(null);
    try {
      const res = await api.post(`/characters/${primaryCharacterId}/surrender`, {
        nation,
        location: locationSlug,
      });
      const data = res.data || {};
      setTrialResult(data);
      if (data.trial && data.courthouse_location) {
        toast.success('You have been brought to the courthouse.');
        const courthousePath = `/roleplay/${data.courthouse_nation || nation}/${data.courthouse_location}`;
        setTimeout(() => navigate(courthousePath), 800);
      } else if (data.dismissed) {
        toast.success(data.verdict_summary || 'Charges dismissed — you walk free.');
      }
      await fetchRapSheet();
      await fetchSceneState();
      await fetchActions();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Surrender failed');
    } finally {
      setSurrendering(false);
    }
  };

  const handleAttemptEscape = async () => {
    if (!primaryCharacterId) return;
    if (!escapeText.trim()) {
      toast.error('Describe your escape attempt — vague tries always fail.');
      return;
    }
    setEscaping(true);
    try {
      const res = await api.post(`/characters/${primaryCharacterId}/attempt-escape`, {
        description: escapeText,
      });
      const j = res.data?.judgement || {};
      if (j.success) {
        toast.success('Escape succeeded!');
      } else {
        toast.error('Escape failed. Your sentence was extended.');
      }
      setEscapeText('');
      await fetchRapSheet();
      await fetchSceneState();
      // Append the escape narration into the RP feed for continuity
      setActions((prev) => [
        ...prev,
        {
          id: `escape_${Date.now()}`,
          character_name: 'The Magistrate',
          action_text: escapeText,
          ai_response: j.narration || '',
          created_at: new Date().toISOString(),
        },
      ]);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Escape attempt failed');
    } finally {
      setEscaping(false);
    }
  };

  useEffect(() => {
    fetchActions();
    fetchSceneState();
    const interval = setInterval(() => {
      fetchActions();
      fetchSceneState();
    }, 10000); // Refresh every 10s
    return () => clearInterval(interval);
  }, [fetchActions, fetchSceneState]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!actionText.trim()) return;

    setSubmitting(true);
    try {
      const res = await api.post(`/locations/${nation}/${locationSlug}/roleplay`, {
        action_text: actionText
      });
      toast.success('Action submitted!');
      setActionText('');
      await fetchActions();
      await fetchSceneState();
      await fetchRapSheet();

      // Auto-arrest redirect — the AI's narration showed the player visibly
      // subdued. The server started a courtroom trial and assigned a
      // courthouse location; redirect the player there so they can defend
      // themselves before the verdict is delivered.
      const autoArrest = res?.data?.auto_arrest;
      if (autoArrest && autoArrest.courthouse_nation && autoArrest.courthouse_location) {
        const reason = autoArrest.arrest_reason || 'You have been taken into custody for trial.';
        toast.warning(`Arrested — heading to trial. ${reason}`, { duration: 7000 });
        const courthousePath = `/roleplay/${autoArrest.courthouse_nation}/${autoArrest.courthouse_location}`;
        if (`${nation}` !== autoArrest.courthouse_nation || `${locationSlug}` !== autoArrest.courthouse_location) {
          setTimeout(() => navigate(courthousePath), 800);
        }
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to submit action');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (rpId) => {
    if (!window.confirm('Are you sure you want to delete this post? This action cannot be undone.')) {
      return;
    }

    setDeletingId(rpId);
    try {
      await api.delete(`/locations/${nation}/${locationSlug}/roleplay/${rpId}`);
      toast.success('Post deleted successfully');
      await fetchActions();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to delete post');
    } finally {
      setDeletingId(null);
    }
  };

  const getDiceColor = (roll) => {
    if (roll === 20) return 'text-yellow-400';
    if (roll === 1) return 'text-red-400';
    if (roll >= 15) return 'text-green-400';
    if (roll <= 5) return 'text-orange-400';
    return 'text-blue-400';
  };

  return (
    <div className="min-h-screen relative">
      <AnimatedBackground />
      <Navbar />
      
      <div className="relative z-10 container mx-auto px-4 py-8 max-w-5xl">
        <Link to={`/nations/${nation}`}>
          <Button variant="ghost" className="mb-6 text-purple-400">
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to {nation.charAt(0).toUpperCase() + nation.slice(1)}
          </Button>
        </Link>

        <div className="glass-dark p-8 rounded-2xl mb-6">
          <h1 className="text-4xl font-bold text-white mb-2">{locationDisplayName}</h1>
          <p className="text-gray-400">Free Roleplay in {nation.charAt(0).toUpperCase() + nation.slice(1)}</p>
          <div className="mt-4 p-3 bg-purple-600/20 border border-purple-500/30 rounded-lg">
            <p className="text-sm text-purple-200">
              <Sparkles className="w-4 h-4 inline mr-2" />
              Freely roleplay in this location! The AI will respond as NPCs, bartenders, and environment.
            </p>
          </div>
          {/* World clock + active festivals (Phase 1 atmospheric layer) */}
          {(sceneState.world_time || (sceneState.active_festivals || []).length > 0) && (
            <div className="mt-4">
              <WorldClock
                clock={{
                  delarom_date: sceneState.delarom_date,
                  time_of_day: sceneState.world_time,
                }}
                festivals={sceneState.active_festivals || []}
              />
            </div>
          )}
          {/* Persona / Disguise active badge (Phase 4) */}
          {sceneState.persona_active && sceneState.persona_name && (
            <div className="mt-4 p-3 bg-indigo-900/30 border border-indigo-500/40 rounded-lg flex items-center gap-3" data-testid="persona-active-badge">
              <span className="text-2xl">🎭</span>
              <div>
                <p className="text-xs uppercase tracking-widest text-indigo-300">Walking incognito</p>
                <p className="text-indigo-100 font-bold">
                  The world sees you as <span className="text-amber-200">{sceneState.persona_name}</span>
                  {sceneState.persona_race && <span className="text-gray-400 text-sm">, a {sceneState.persona_race}</span>}.
                </p>
              </div>
            </div>
          )}

          {/* Faction allegiance + rival territory cues (Round 3 visibility pass) */}
          {!sceneState.persona_active && sceneState.player_faction && (
            <div className="mt-4 flex flex-wrap items-center gap-2" data-testid="scene-faction-state">
              <span className="text-xs uppercase tracking-widest text-gray-400 mr-1">Allegiance:</span>
              <FactionBadge faction={sceneState.player_faction} size="md" showRank />
              {rivalsHere.map((r) => (
                <span
                  key={r.slug}
                  className="inline-flex items-center gap-1.5 px-2 py-1 text-xs rounded-full font-semibold uppercase tracking-wider whitespace-nowrap animate-pulse"
                  style={{
                    backgroundColor: `${r.color_hex || '#dc2626'}22`,
                    border: `1px solid ${r.color_hex || '#dc2626'}66`,
                    color: r.color_hex || '#fca5a5',
                  }}
                  title={`You stand on ${r.name}'s home soil. They do not yet know your banner.`}
                  data-testid={`rival-territory-pill-${r.slug}`}
                >
                  <Swords className="w-3.5 h-3.5" />
                  Rival turf · {r.name}
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Tavern Bulletin Board (Phase 2) — public, anyone can read; posting needs a character */}
        <TavernBoard
          nation={nation}
          location={locationSlug}
          character={primaryCharacterId ? { id: primaryCharacterId } : null}
          currentUserId={user?.id}
          isStaff={user?.role === 'admin' || user?.role === 'moderator'}
        />

        {/* TRIAL panel — character is at the courthouse with an active trial */}
        {isOnTrialHere && (
          <TrialPanel
            characterId={primaryCharacterId}
            onFinalized={async ({ verdict, imprisonment: imp }) => {
              await fetchRapSheet();
              await fetchActiveTrial();
              if (imp && imp.jail_location && imp.nation) {
                toast.warning('Guilty. You are taken to the jail.', { duration: 6000 });
                setTimeout(() => navigate(`/roleplay/${imp.nation}/${imp.jail_location}`), 1200);
              } else if (verdict?.sentence_type === 'dismissed') {
                toast.success('Charges dismissed. You walk free.');
              } else if (verdict?.sentence_type === 'fine') {
                toast.success(`Fine of ${verdict.fine_amount || 0}g paid. You walk free.`);
              } else if (verdict?.sentence_type === 'exile') {
                toast.warning('Exiled from this nation.');
              } else if (verdict?.sentence_type === 'execute') {
                toast.error('Executed. Your character has died.');
              }
            }}
          />
        )}

        {/* IMPRISONED banner — character is locked to this jail */}
        {isImprisonedHere && (
          <div
            className="glass-dark p-5 rounded-xl mb-6 border-2 border-red-500/60 bg-red-900/20"
            data-testid="imprisoned-banner"
          >
            <div className="flex items-start gap-3">
              <Lock className="w-7 h-7 text-red-300 flex-shrink-0 mt-1" />
              <div className="flex-1">
                <p className="text-red-200 font-bold uppercase tracking-widest">Incarcerated</p>
                <p className="text-sm text-red-100/90 mt-1">
                  You are confined to the jail of {locationDisplayName}. Sentence served:{' '}
                  <span className="font-bold">{imprisonment.turns_served} / {imprisonment.sentence_turns}</span> turns.
                </p>
                {imprisonment.narration && (
                  <p className="text-xs italic text-red-100/70 mt-2">
                    “{imprisonment.narration}”
                  </p>
                )}

                {/* Escape attempt */}
                <div className="mt-4 space-y-2">
                  <p className="text-xs text-red-200/80 uppercase tracking-wider">Attempt Escape</p>
                  <textarea
                    value={escapeText}
                    onChange={(e) => setEscapeText(e.target.value)}
                    rows={3}
                    placeholder="Describe your escape attempt in detail. Lazy attempts (‘I run’) will always fail. Use your environment, companions, gold, earned favours..."
                    className="w-full bg-black/40 border border-red-500/40 rounded-md p-2 text-sm text-red-50 placeholder-red-200/30"
                    disabled={escaping}
                    data-testid="escape-description-input"
                  />
                  <Button
                    type="button"
                    onClick={handleAttemptEscape}
                    disabled={escaping || !escapeText.trim()}
                    className="bg-gradient-to-r from-red-600 to-orange-600 hover:from-red-700 hover:to-orange-700 text-sm"
                    data-testid="attempt-escape-btn"
                  >
                    {escaping ? 'Adjudicating…' : 'Attempt Escape'}
                  </Button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* WANTED banner — visible bounty in this nation, but not imprisoned here */}
        {!isImprisonedHere && bountyHere && bountyHere.open_crime_count > 0 && (
          <div
            className="glass-dark p-4 rounded-xl mb-6 border border-amber-500/40 bg-amber-900/15"
            data-testid="wanted-banner"
          >
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-start gap-3">
                <ShieldAlert className="w-6 h-6 text-amber-300 flex-shrink-0 mt-1" />
                <div>
                  <p className="text-amber-200 font-bold">
                    WANTED in {nation.charAt(0).toUpperCase() + nation.slice(1)}
                  </p>
                  <p className="text-xs text-amber-100/80 mt-1">
                    Bounty: {bountyHere.total_bounty.toLocaleString()}g across {bountyHere.open_crime_count} open crime
                    {bountyHere.open_crime_count === 1 ? '' : 's'} (worst severity: {bountyHere.worst_severity}). Guards
                    in this nation will recognise and act on you.
                  </p>
                </div>
              </div>
              <Button
                type="button"
                onClick={handleSurrender}
                disabled={surrendering}
                className="bg-amber-600/40 border border-amber-500/50 hover:bg-amber-600/60 text-amber-100 text-sm"
                data-testid="surrender-btn"
              >
                <Scale className="w-4 h-4 mr-2" />
                {surrendering ? 'On trial…' : 'Surrender'}
              </Button>
            </div>
            {trialResult?.trial && (
              <div className="mt-3 p-3 rounded-lg bg-black/30 border border-amber-500/30" data-testid="trial-result">
                <p className="text-amber-200 font-semibold text-sm">
                  {trialResult.trial.verdict_summary}
                </p>
                <p className="text-xs italic text-amber-100/80 mt-1">
                  {trialResult.trial.narration}
                </p>
              </div>
            )}
          </div>
        )}

        {/* Scene State: persistent NPCs + active events visible to everyone */}
        {(sceneState.events?.length > 0 || sceneState.npcs?.length > 0) && (
          <div className="glass-dark p-6 rounded-xl mb-6 border border-amber-500/20" data-testid="scene-state-panel">
            {sceneState.events?.length > 0 && (
              <div className="mb-4">
                <h3 className="text-sm uppercase tracking-widest text-amber-300/80 mb-3 flex items-center gap-2">
                  <Flame className="w-4 h-4" /> What's happening here right now
                </h3>
                <div className="space-y-2">
                  {sceneState.events.map((ev) => (
                    <div key={ev.id} className="p-3 rounded-lg bg-amber-900/15 border border-amber-500/30" data-testid={`scene-event-${ev.id}`}>
                      <div className="flex items-start gap-2">
                        <span className="text-xs px-2 py-0.5 rounded-full bg-amber-500/30 text-amber-200 uppercase tracking-wide">
                          {ev.event_type}
                        </span>
                        <span className="text-xs text-gray-400">intensity: {ev.intensity}</span>
                      </div>
                      <p className="text-amber-100 mt-2 font-semibold">{ev.summary}</p>
                      {ev.description && (
                        <p className="text-sm text-gray-300 mt-1">{ev.description}</p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {sceneState.npcs?.length > 0 && (() => {
              const companions = sceneState.npcs.filter((n) => n.is_companion);
              const others = sceneState.npcs.filter((n) => !n.is_companion);
              return (
                <div className="space-y-4">
                  {companions.length > 0 && (
                    <div data-testid="companions-section">
                      <h3 className="text-sm uppercase tracking-widest text-pink-300/90 mb-3 flex items-center gap-2">
                        <Heart className="w-4 h-4" fill="currentColor" /> Traveling with you
                      </h3>
                      <div className="grid sm:grid-cols-2 gap-2">
                        {companions.map((npc) => (
                          <div
                            key={npc.id}
                            className="p-3 rounded-lg border border-pink-500/40 bg-pink-900/15 text-pink-100"
                            data-testid={`companion-${npc.id}`}
                          >
                            <div className="flex items-start gap-3">
                              {npc.image_url ? (
                                <img
                                  src={npc.image_url}
                                  alt={npc.name}
                                  className="w-14 h-14 rounded-lg object-cover border border-pink-500/40 flex-shrink-0"
                                  data-testid={`companion-portrait-${npc.id}`}
                                />
                              ) : null}
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center justify-between gap-2">
                                  <span className="font-semibold">
                                    {npc.name}
                                    <span className="ml-2 text-xs text-pink-200/70 font-normal">
                                      {npc.race} • {npc.role}
                                    </span>
                                  </span>
                                  <span className="text-xs px-2 py-0.5 rounded-full bg-black/30 capitalize">
                                    {npc.overall_mood}
                                  </span>
                                </div>
                                <p className="text-xs mt-1 capitalize opacity-80">
                                  They see you as: {npc.relationship_label}
                                </p>
                                <button
                                  type="button"
                                  onClick={() => handleDismissCompanion(npc)}
                                  disabled={dismissingCompanionId === npc.id}
                                  className="mt-2 inline-flex items-center gap-1 text-xs text-pink-200 hover:text-white bg-pink-900/40 hover:bg-pink-800/60 disabled:opacity-50 border border-pink-500/50 rounded-full px-2 py-0.5 transition"
                                  data-testid={`dismiss-companion-${npc.id}`}
                                >
                                  <UserMinus className="w-3 h-3" />
                                  {dismissingCompanionId === npc.id ? 'Dismissing…' : 'Dismiss'}
                                </button>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {others.length > 0 && (
                    <div>
                      <h3 className="text-sm uppercase tracking-widest text-emerald-300/80 mb-3 flex items-center gap-2">
                        <Users className="w-4 h-4" /> Familiar faces in this location
                      </h3>
                      <div className="grid sm:grid-cols-2 gap-2">
                        {others.map((npc) => {
                          const isHostile = npc.relationship_score <= -10;
                          const isFriendly = npc.relationship_score >= 10;
                          const relColor = isHostile
                            ? 'text-red-300 border-red-500/30 bg-red-900/10'
                            : isFriendly
                            ? 'text-emerald-300 border-emerald-500/30 bg-emerald-900/10'
                            : 'text-gray-300 border-gray-500/20 bg-gray-900/30';
                          return (
                            <div
                              key={npc.id}
                              className={`p-3 rounded-lg border ${relColor}`}
                              data-testid={`scene-npc-${npc.id}`}
                            >
                              <div className="flex items-center justify-between">
                                <span className="font-semibold">
                                  {npc.name}
                                  <span className="ml-2 text-xs text-gray-400 font-normal">
                                    {npc.race} • {npc.role}
                                  </span>
                                </span>
                                <span className="text-xs px-2 py-0.5 rounded-full bg-black/30 capitalize">
                                  {npc.overall_mood}
                                </span>
                              </div>
                              <p className="text-xs mt-1 capitalize opacity-80">
                                They see you as: {npc.relationship_label}
                              </p>
                              {npc.status && npc.status !== 'alive' && (
                                <p className="text-xs mt-1 text-red-300 uppercase tracking-wide">
                                  {npc.status}{npc.status_note ? ` — ${npc.status_note}` : ''}
                                </p>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </div>
              );
            })()}
          </div>
        )}

        {/* Roleplay History */}
        <div className="glass-dark p-6 rounded-xl mb-6">
          <h2 className="text-2xl font-bold text-purple-300 mb-4">Roleplay Scene</h2>
          {loading ? (
            <p className="text-gray-400 text-center py-8">Loading...</p>
          ) : actions.length === 0 ? (
            <p className="text-gray-400 text-center py-8">Be the first to roleplay in {locationDisplayName}!</p>
          ) : (
            <div className="space-y-4 max-h-[600px] overflow-y-auto">
              {actions.map((action) => (
                <div key={action.id} className="space-y-2 group" data-testid={`rp-post-${action.id}`}>
                  {/* Player Action */}
                  <div className="glass p-4 rounded-lg border-l-4 border-blue-500 relative">
                    <div className="flex items-center justify-between mb-2 flex-wrap gap-2">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-bold text-blue-300">{action.character_name}</span>
                        {action.character_id && factionsByChar[action.character_id] && (
                          <FactionBadge faction={factionsByChar[action.character_id]} size="sm" />
                        )}
                      </div>
                      <div className="flex items-center gap-2">
                        {action.dice_roll && (
                          <>
                            <Dice6 className={`w-5 h-5 ${action.dice_roll === 20 ? 'text-yellow-400 animate-pulse' : action.dice_roll === 1 ? 'text-red-400 animate-bounce' : 'text-gray-400'}`} />
                            <span className={`font-bold text-lg ${getDiceColor(action.dice_roll)}`}>
                              {action.dice_roll}
                              {action.modifier > 0 && ` +${action.modifier}`}
                              {action.modifier < 0 && ` ${action.modifier}`}
                              {action.modifier !== 0 && ` = ${action.total_roll}`}
                            </span>
                            {action.dice_roll === 20 && (
                              <span className="bg-yellow-500/20 border border-yellow-400 px-2 py-1 rounded-full text-yellow-400 text-xs font-bold animate-pulse">
                                ⭐ CRITICAL SUCCESS!
                              </span>
                            )}
                            {action.dice_roll === 1 && (
                              <span className="bg-red-500/20 border border-red-400 px-2 py-1 rounded-full text-red-400 text-xs font-bold animate-bounce">
                                💥 EPIC FAIL!
                              </span>
                            )}
                          </>
                        )}
                        {/* Delete Button */}
                        {canDelete(action) && (
                          <button
                            onClick={() => handleDelete(action.id)}
                            disabled={deletingId === action.id}
                            className="opacity-0 group-hover:opacity-100 transition-opacity p-1.5 rounded-md hover:bg-red-500/20 text-gray-400 hover:text-red-400"
                            title={action.user_id === user?.id ? "Delete your post" : "Delete post (Admin/Mod)"}
                            data-testid={`delete-btn-${action.id}`}
                          >
                            {deletingId === action.id ? (
                              <span className="animate-spin">⏳</span>
                            ) : (
                              <Trash2 className="w-4 h-4" />
                            )}
                          </button>
                        )}
                      </div>
                    </div>
                    <p className="text-white whitespace-pre-wrap">{action.action_text}</p>
                    {/* Show owner indicator for mods/admins */}
                    {(user?.role === 'admin' || user?.role === 'moderator') && action.user_id !== user?.id && (
                      <p className="text-xs text-gray-500 mt-2">Posted by another user</p>
                    )}
                  </div>
                  
                  {/* AI Response */}
                  {action.ai_response && (
                    <div className="glass p-4 rounded-lg border-l-4 border-purple-500 bg-purple-900/20 ml-8">
                      <div className="flex items-center gap-2 mb-2">
                        <span className="font-bold text-purple-300">🎭 Scene</span>
                      </div>
                      <p className="text-gray-200 whitespace-pre-wrap italic">{action.ai_response}</p>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Action Input */}
        <div className="glass-dark p-6 rounded-xl">
          <h3 className="text-xl font-bold text-purple-300 mb-4">Your Action</h3>
          <form onSubmit={handleSubmit} className="space-y-4">
            <Textarea
              value={actionText}
              onChange={(e) => setActionText(e.target.value)}
              placeholder="Describe what your character does...\n\nExample: 'I walk up to the bar and order an ale, looking around at the other patrons.'\nOr: 'I attempt to pick the lock on the mysterious door, glancing over my shoulder.'\n\nA dice roll will automatically determine your success!"
              className="bg-black/20 border-purple-500/30 text-white min-h-[120px]"
              required
              data-testid="rp-action-input"
            />
            <Button
              type="submit"
              disabled={submitting}
              className="w-full bg-gradient-to-r from-purple-600 to-pink-600"
              data-testid="rp-submit-btn"
            >
              {submitting ? 'Submitting...' : '🎲 Roll & Submit Action'}
            </Button>
          </form>
        </div>
      </div>
    </div>
  );
};

export default LocationRP;
