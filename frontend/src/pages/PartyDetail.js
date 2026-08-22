import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link, useParams, useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { ArrowLeft, Crown, Flag, Loader2, LogIn, LogOut, MapPin, Play, Send, Users } from 'lucide-react';
import api from '../utils/api';
import { useAuth } from '../contexts/AuthContext';
import { Button } from '../components/ui/button';
import { Textarea } from '../components/ui/textarea';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../components/ui/dialog';

const STATUS_BADGE = {
  recruiting: { label: 'Recruiting', className: 'bg-emerald-950/60 border-emerald-500/40 text-emerald-200' },
  active:     { label: 'In session', className: 'bg-amber-950/60 border-amber-500/40 text-amber-200' },
  finished:   { label: 'Ended',      className: 'bg-stone-800/60 border-stone-500/40 text-stone-300' },
};

const REFRESH_INTERVAL_MS = 6000;

const PartyDetail = () => {
  const { partyId } = useParams();
  const { currentUser } = useAuth();
  const navigate = useNavigate();

  const [party, setParty] = useState(null);
  const [actions, setActions] = useState([]);
  const [characters, setCharacters] = useState([]);
  const [loading, setLoading] = useState(true);
  const [posting, setPosting] = useState(false);
  const [starting, setStarting] = useState(false);
  const [actionText, setActionText] = useState('');
  const [joinOpen, setJoinOpen] = useState(false);
  const [joinCharId, setJoinCharId] = useState('');
  const logRef = useRef(null);

  const load = useCallback(async () => {
    try {
      const [pRes, aRes, cRes] = await Promise.all([
        api.get(`/parties/${partyId}`),
        api.get(`/parties/${partyId}/actions`).catch(() => ({ data: [] })),
        api.get('/characters').catch(() => ({ data: [] })),
      ]);
      setParty(pRes.data);
      setActions(Array.isArray(aRes.data) ? aRes.data : []);
      const chars = Array.isArray(cRes.data) ? cRes.data : (cRes.data?.characters || []);
      setCharacters(chars);
      setJoinCharId((prev) => prev || chars[0]?.id || '');
    } catch (e) {
      if (e.response?.status === 404) {
        toast.error('That party could not be found.');
        navigate('/parties');
      } else {
        toast.error(e.response?.data?.detail || 'Failed to load party.');
      }
    } finally {
      setLoading(false);
    }
  }, [partyId, navigate]);

  useEffect(() => { load(); }, [load]);

  // Simple polling: keep the scene log fresh so other players' turns show up.
  useEffect(() => {
    if (!party || party.status === 'finished') return undefined;
    const id = setInterval(load, REFRESH_INTERVAL_MS);
    return () => clearInterval(id);
  }, [party, load]);

  // Auto-scroll the scene log to the newest turn
  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [actions.length]);

  const isMember = useMemo(
    () => !!party?.members?.some((m) => m.user_id === currentUser?.id),
    [party, currentUser],
  );
  const isHost = !!party && party.host_user_id === currentUser?.id;
  const isFull = !!party && (party.members?.length || 0) >= party.max_members;
  const activeCharId = party?.turn_order?.[party?.current_turn_index];
  const activeMember = useMemo(
    () => party?.members?.find((m) => m.character_id === activeCharId),
    [party, activeCharId],
  );
  const itIsMyTurn = !!activeMember && activeMember.user_id === currentUser?.id;

  const badge = party ? (STATUS_BADGE[party.status] || STATUS_BADGE.finished) : null;

  const handleJoin = async () => {
    if (!joinCharId) { toast.error('Choose a character to join with.'); return; }
    try {
      await api.post(`/parties/${partyId}/join`, { character_id: joinCharId });
      setJoinOpen(false);
      toast.success('You have joined the party.');
      load();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Could not join party.');
    }
  };

  const handleLeave = async () => {
    if (isHost) {
      toast.error('The host cannot leave — end the party instead.');
      return;
    }
    try {
      await api.post(`/parties/${partyId}/leave`);
      toast.success('You have left the party.');
      load();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Could not leave party.');
    }
  };

  const handleStart = async () => {
    if (starting) return;
    setStarting(true);
    try {
      await api.post(`/parties/${partyId}/start`);
      toast.success('The scene begins.');
      load();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Could not start party.');
    } finally {
      setStarting(false);
    }
  };

  const handleFinish = async () => {
    if (!window.confirm('End the party for everyone? This cannot be undone.')) return;
    try {
      const r = await api.post(`/parties/${partyId}/finish`);
      // Optimistically flip the badge — the 6s poll would otherwise lag.
      setParty((prev) => (prev ? { ...prev, ...r.data, status: 'finished' } : prev));
      toast.success('The party has ended.');
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Could not end party.');
      load();
    }
  };

  const handleAction = async () => {
    if (posting) return;
    const text = actionText.trim();
    if (text.length < 3) {
      toast.error('Your action needs at least a few words.');
      return;
    }
    setPosting(true);
    try {
      await api.post(`/parties/${partyId}/action`, { action_text: text });
      setActionText('');
      load();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Could not submit your action.');
    } finally {
      setPosting(false);
    }
  };

  if (loading || !party) {
    return (
      <div className="min-h-screen flex items-center justify-center text-stone-300 bg-black">
        <Loader2 className="w-6 h-6 mr-2 animate-spin" />
        Approaching the party…
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-zinc-950 via-stone-950 to-black text-stone-100">
      <div className="max-w-5xl mx-auto px-6 py-10">
        <Link to="/parties" className="text-sm text-stone-400 hover:text-stone-200 transition flex items-center gap-1" data-testid="party-back-link">
          <ArrowLeft className="w-4 h-4" /> All Parties
        </Link>

        {/* ── Header ─────────────────────────────────────────────── */}
        <div className="mt-4 mb-8 rounded-xl border border-stone-700/60 bg-stone-950/60 p-6">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h1 className="text-3xl sm:text-4xl font-bold tracking-tight flex items-center gap-3" data-testid="party-title">
                {party.name}
              </h1>
              <div className="mt-2 text-xs text-stone-400 flex items-center gap-4">
                <span className="flex items-center gap-1"><MapPin className="w-3 h-3" /> {party.location}</span>
                <span className="flex items-center gap-1"><Users className="w-3 h-3" /> {party.members.length}/{party.max_members}</span>
              </div>
            </div>
            <span className={`text-[10px] uppercase tracking-widest rounded border px-2 py-1 ${badge.className}`} data-testid="party-status-badge">
              {badge.label}
            </span>
          </div>
          <p className="mt-4 text-stone-200/90 italic leading-relaxed" data-testid="party-scene-description">
            {party.scene_description}
          </p>

          {/* ── Actions bar ──────────────────────────────────────── */}
          <div className="mt-5 flex flex-wrap items-center gap-2">
            {party.status === 'recruiting' && !isMember && (
              <Button
                onClick={() => setJoinOpen(true)}
                disabled={isFull || characters.length === 0}
                className="bg-emerald-800 hover:bg-emerald-900 text-emerald-50"
                data-testid="join-party-btn"
              >
                <LogIn className="w-4 h-4 mr-2" />
                {isFull ? 'Full' : 'Join Party'}
              </Button>
            )}
            {isHost && party.status === 'recruiting' && (
              <Button
                onClick={handleStart}
                disabled={starting}
                className="bg-amber-700 hover:bg-amber-800 text-amber-50"
                data-testid="start-party-btn"
              >
                {starting ? (<><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Starting…</>) : (<><Play className="w-4 h-4 mr-2" /> Start the Scene</>)}
              </Button>
            )}
            {isHost && party.status !== 'finished' && (
              <Button
                onClick={handleFinish}
                variant="outline"
                className="border-stone-600 text-stone-200 hover:bg-stone-800"
                data-testid="finish-party-btn"
              >
                <Flag className="w-4 h-4 mr-2" />
                End Party
              </Button>
            )}
            {isMember && !isHost && party.status !== 'finished' && (
              <Button
                onClick={handleLeave}
                variant="outline"
                className="border-stone-600 text-stone-200 hover:bg-stone-800"
                data-testid="leave-party-btn"
              >
                <LogOut className="w-4 h-4 mr-2" />
                Leave
              </Button>
            )}
          </div>
        </div>

        {/* ── Roster + Turn ─────────────────────────────────────── */}
        <div className="grid md:grid-cols-3 gap-4 mb-8">
          <div className="md:col-span-2 rounded-xl border border-stone-700/60 bg-stone-950/40 p-5" data-testid="party-roster">
            <h2 className="text-sm uppercase tracking-widest text-stone-400 mb-3 flex items-center gap-2">
              <Users className="w-4 h-4" /> Party Roster
            </h2>
            <div className="space-y-2">
              {party.members.map((m) => {
                const isActive = m.character_id === activeCharId && party.status === 'active';
                return (
                  <div
                    key={m.character_id}
                    className={`flex items-center justify-between rounded-md border p-2.5 text-sm ${
                      isActive
                        ? 'border-amber-500/50 bg-amber-950/30'
                        : 'border-stone-800 bg-stone-950/40'
                    }`}
                    data-testid={`roster-member-${m.character_id}`}
                  >
                    <div>
                      <span className="text-stone-100 font-medium">{m.character_name}</span>
                      <span className="text-stone-500 ml-2 text-xs">
                        {m.character_race} {m.character_class}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      {m.role === 'host' && (
                        <span className="text-amber-300 text-xs flex items-center gap-1">
                          <Crown className="w-3 h-3" /> Host
                        </span>
                      )}
                      {isActive && (
                        <span className="text-xs uppercase tracking-widest text-amber-200" data-testid="active-turn-badge">
                          Acting
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="rounded-xl border border-stone-700/60 bg-stone-950/40 p-5">
            <h2 className="text-sm uppercase tracking-widest text-stone-400 mb-3">Turn</h2>
            {party.status === 'recruiting' && (
              <p className="text-sm text-stone-300">
                Waiting on the host to <strong>start the scene</strong>.
              </p>
            )}
            {party.status === 'active' && activeMember && (
              <p className="text-sm text-stone-300" data-testid="turn-status-line">
                {itIsMyTurn ? (
                  <>It is <strong className="text-amber-200">your turn</strong>, {activeMember.character_name}.</>
                ) : (
                  <>Waiting on <strong className="text-amber-200">{activeMember.character_name}</strong>…</>
                )}
              </p>
            )}
            {party.status === 'finished' && (
              <p className="text-sm text-stone-400 italic">This scene has ended.</p>
            )}
          </div>
        </div>

        {/* ── Scene Log ─────────────────────────────────────────── */}
        {actions.length > 0 && (
          <div
            ref={logRef}
            className="rounded-xl border border-stone-700/60 bg-stone-950/50 p-5 mb-6 max-h-[520px] overflow-y-auto space-y-5"
            data-testid="party-scene-log"
          >
            {actions.map((a) => (
              <div key={a.id} className="space-y-2" data-testid={`scene-action-${a.id}`}>
                {a.actor_character_id !== 'MOC' && (
                  <div className="rounded-md border border-stone-800 bg-stone-900/60 p-3">
                    <div className="text-xs uppercase tracking-widest text-stone-500 mb-1">
                      {a.actor_character_name}
                    </div>
                    <div className="text-stone-100 whitespace-pre-wrap">{a.action_text}</div>
                  </div>
                )}
                <div className="rounded-md border border-amber-900/40 bg-amber-950/10 p-3">
                  <div className="text-xs uppercase tracking-widest text-amber-300/80 mb-1">
                    Master of Ceremonies
                  </div>
                  <div className="text-stone-100 italic whitespace-pre-wrap leading-relaxed">
                    {a.ai_response}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* ── Action Input ──────────────────────────────────────── */}
        {party.status === 'active' && isMember && (
          <div className="rounded-xl border border-stone-700/60 bg-stone-950/60 p-5 mb-8">
            <label className="block text-sm text-stone-400 mb-2">
              {itIsMyTurn
                ? `Your move, ${activeMember?.character_name}. What do you do?`
                : `Watch and wait — the Master will call on you when it's your turn.`}
            </label>
            <Textarea
              value={actionText}
              onChange={(e) => setActionText(e.target.value)}
              placeholder="I glance across the room, then step forward and speak…"
              maxLength={2000}
              rows={4}
              disabled={!itIsMyTurn || posting}
              className="bg-stone-900 border-stone-700 text-stone-100"
              data-testid="party-action-input"
            />
            <div className="flex items-center justify-between mt-2">
              <div className="text-xs text-stone-500">{actionText.length}/2000</div>
              <Button
                onClick={handleAction}
                disabled={!itIsMyTurn || posting || actionText.trim().length < 3}
                className="bg-gradient-to-r from-amber-700 to-stone-700 hover:from-amber-800 hover:to-stone-800 text-stone-100"
                data-testid="submit-action-btn"
              >
                {posting ? (
                  <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Narrating…</>
                ) : (
                  <><Send className="w-4 h-4 mr-2" /> Take Your Turn</>
                )}
              </Button>
            </div>
          </div>
        )}
      </div>

      {/* ── Join Dialog ──────────────────────────────────────────── */}
      <Dialog open={joinOpen} onOpenChange={setJoinOpen}>
        <DialogContent
          className="bg-stone-950 border-stone-700 text-stone-100"
          data-testid="join-party-dialog"
        >
          <DialogHeader>
            <DialogTitle className="text-xl text-emerald-200">Join the Party</DialogTitle>
            <DialogDescription className="text-stone-400">
              Choose which of your characters will step into the scene.
            </DialogDescription>
          </DialogHeader>
          {characters.length === 0 ? (
            <p className="text-sm text-stone-400 italic">
              Create a character first — you cannot join a party without one.
            </p>
          ) : (
            <select
              value={joinCharId}
              onChange={(e) => setJoinCharId(e.target.value)}
              className="w-full bg-stone-900 border border-stone-700 rounded-md px-3 py-2 text-stone-100"
              data-testid="join-character-select"
            >
              {characters.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name} — {c.race}{c.character_class ? ` (${c.character_class})` : ''}
                </option>
              ))}
            </select>
          )}
          <DialogFooter>
            <Button variant="ghost" onClick={() => setJoinOpen(false)} className="text-stone-300 hover:text-stone-100" data-testid="cancel-join-btn">
              Cancel
            </Button>
            <Button
              onClick={handleJoin}
              disabled={!joinCharId}
              className="bg-emerald-800 hover:bg-emerald-900 text-emerald-50"
              data-testid="confirm-join-btn"
            >
              <LogIn className="w-4 h-4 mr-2" />
              Join
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default PartyDetail;
