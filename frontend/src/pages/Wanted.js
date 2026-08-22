import React, { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { toast } from 'sonner';
import {
  Skull, Loader2, Coins, MapPin, Sword, ScrollText, Eye, EyeOff,
} from 'lucide-react';
import api from '../utils/api';
import { useAuth } from '../contexts/AuthContext';
import { Button } from '../components/ui/button';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
  DialogDescription,
} from '../components/ui/dialog';

const NATIONS = [
  { slug: '', label: 'All Realms' },
  { slug: 'ammeonon',      label: 'Ammeonon' },
  { slug: 'dhor-kuldor',   label: 'Dhor-Kuldor' },
  { slug: 'selindori',     label: 'Selindori' },
  { slug: 'aigraels',      label: 'Aigraels' },
  { slug: 'veiled-realms', label: 'Veiled Realms' },
];

const Wanted = () => {
  const { currentUser } = useAuth();
  const [board, setBoard] = useState([]);
  const [contracts, setContracts] = useState([]);
  const [chars, setChars] = useState([]);
  const [nationFilter, setNationFilter] = useState('');
  const [loading, setLoading] = useState(true);
  const [claimTarget, setClaimTarget] = useState(null);
  const [claiming, setClaiming] = useState(false);
  const [claimForm, setClaimForm] = useState({ character_id: '', method: 'captured' });

  const refresh = async () => {
    try {
      const [bRes, cRes, chRes] = await Promise.all([
        api.get(`/bounty-board${nationFilter ? `?nation=${nationFilter}` : ''}`).catch(() => ({ data: [] })),
        api.get('/contracts/board').catch(() => ({ data: [] })),
        api.get('/characters').catch(() => ({ data: [] })),
      ]);
      setBoard(Array.isArray(bRes.data) ? bRes.data : []);
      setContracts(Array.isArray(cRes.data) ? cRes.data : []);
      const charList = Array.isArray(chRes.data) ? chRes.data : (chRes.data?.characters || []);
      setChars(charList);
      setClaimForm((f) => (!f.character_id && charList[0]?.id ? { ...f, character_id: charList[0].id } : f));
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to load the Wanted board.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { refresh(); }, [nationFilter]);

  const playerBounties = useMemo(
    () => board.filter((b) => b.perpetrator_type === 'character'),
    [board],
  );
  const npcBounties = useMemo(
    () => board.filter((b) => b.perpetrator_type === 'npc'),
    [board],
  );

  const doClaim = async () => {
    if (!claimTarget) return;
    if (!claimForm.character_id) { toast.error('Choose your hunter.'); return; }
    setClaiming(true);
    try {
      const r = await api.post('/bounties/claim-character', {
        target_character_id: claimTarget.perpetrator_id,
        hunter_character_id: claimForm.character_id,
        nation: claimTarget.nation,
        method: claimForm.method,
      });
      toast.success(
        `Bounty claimed — ${r.data.credited || 0}g deposited. ${claimTarget.perpetrator_name} ${claimForm.method === 'killed' ? 'has fallen.' : 'has been captured.'}`,
      );
      setClaimTarget(null);
      refresh();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Could not claim the bounty.');
    } finally {
      setClaiming(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center text-stone-300 bg-black">
        <Loader2 className="w-6 h-6 mr-2 animate-spin" />
        Reading the crier&apos;s post…
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-zinc-950 via-stone-950 to-black text-stone-100">
      <div className="max-w-5xl mx-auto px-6 py-12">
        <div className="mb-8 flex flex-wrap items-start justify-between gap-4">
          <div>
            <Link to="/dashboard" className="text-sm text-stone-400 hover:text-stone-200 transition" data-testid="wanted-back-link">
              ← Dashboard
            </Link>
            <h1 className="mt-4 text-4xl sm:text-5xl font-bold tracking-tight flex items-center gap-3">
              <Skull className="w-10 h-10 text-red-400" />
              <span>The Wanted Board</span>
            </h1>
            <p className="mt-3 text-stone-400 max-w-3xl">
              Public warrants and quieter arrangements. The crier posts the
              first; the fixer posts the second — with no name attached.
            </p>
          </div>
          <select
            value={nationFilter}
            onChange={(e) => setNationFilter(e.target.value)}
            className="bg-stone-900 border border-stone-700 rounded-md px-3 py-2 text-stone-100 text-sm"
            data-testid="wanted-nation-filter"
          >
            {NATIONS.map((n) => <option key={n.slug} value={n.slug}>{n.label}</option>)}
          </select>
        </div>

        {/* Player warrants */}
        <div className="mb-10">
          <h2 className="text-lg font-semibold mb-3 text-red-200 flex items-center gap-2">
            <Sword className="w-4 h-4" />
            Warrants on Characters
          </h2>
          {playerBounties.length === 0 ? (
            <div className="rounded-xl border border-stone-700/60 bg-stone-950/40 p-6 text-center text-stone-500 text-sm">
              No open warrants on named characters. The streets are calm.
            </div>
          ) : (
            <div className="grid sm:grid-cols-2 gap-4" data-testid="player-warrants-list">
              {playerBounties.map((b) => (
                <div
                  key={`${b.perpetrator_id}-${b.nation}`}
                  className="rounded-xl border border-red-900/40 bg-red-950/10 p-4"
                  data-testid={`warrant-${b.perpetrator_id}`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="text-red-100 font-semibold flex items-center gap-2">
                      <Skull className="w-4 h-4 text-red-400" />
                      {b.perpetrator_name}
                    </div>
                    <div className="text-amber-300 font-semibold flex items-center gap-1">
                      <Coins className="w-3 h-3" />
                      {b.total_bounty}g
                    </div>
                  </div>
                  <div className="text-xs text-stone-400 flex items-center gap-2 mb-2">
                    <MapPin className="w-3 h-3" />
                    <span>{b.nation}</span>
                    <span>·</span>
                    <span>{b.open_crime_count} open charge{b.open_crime_count === 1 ? '' : 's'}</span>
                  </div>
                  {b.top_crime_reason && (
                    <p className="text-xs text-stone-500 italic line-clamp-2 mb-3">
                      &quot;{b.top_crime_reason}&quot;
                    </p>
                  )}
                  <Button
                    onClick={() => setClaimTarget(b)}
                    size="sm"
                    className="w-full bg-red-900 hover:bg-red-950 text-red-100"
                    disabled={chars.length === 0 || chars.some((c) => c.id === b.perpetrator_id)}
                    data-testid={`claim-warrant-${b.perpetrator_id}`}
                  >
                    <Sword className="w-3.5 h-3.5 mr-2" />
                    Hunt this bounty
                  </Button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Anonymous contracts */}
        <div className="mb-10">
          <h2 className="text-lg font-semibold mb-3 text-purple-200 flex items-center gap-2">
            <EyeOff className="w-4 h-4" />
            The Fixer&apos;s Board
            <span className="text-xs text-stone-500 font-normal">— anonymous contracts</span>
          </h2>
          {contracts.length === 0 ? (
            <div className="rounded-xl border border-stone-700/60 bg-stone-950/40 p-6 text-center text-stone-500 text-sm">
              No open contracts. The fixer sips his wine.
            </div>
          ) : (
            <div className="grid sm:grid-cols-2 gap-4" data-testid="contracts-list">
              {contracts.map((c) => (
                <div
                  key={c.id}
                  className="rounded-xl border border-purple-900/40 bg-purple-950/10 p-4"
                  data-testid={`contract-${c.id}`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="text-purple-100 font-semibold flex items-center gap-2">
                      <Eye className="w-4 h-4 text-purple-400" />
                      {c.target_character_name}
                    </div>
                    <div className="text-amber-300 font-semibold flex items-center gap-1">
                      <Coins className="w-3 h-3" />
                      {c.reward_gold}g
                    </div>
                  </div>
                  <div className="text-xs text-stone-400 flex items-center gap-2 mb-2">
                    <MapPin className="w-3 h-3" />
                    <span>{c.city_slug}</span>
                    <span>·</span>
                    <span className="uppercase tracking-widest text-purple-300">{c.status}</span>
                  </div>
                  {c.note && (
                    <p className="text-xs text-stone-500 italic line-clamp-2 mb-3">
                      &quot;{c.note}&quot;
                    </p>
                  )}
                  <div className="text-[10px] text-stone-500 italic">
                    Posted by a hand that does not sign its name.
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* NPC warrants (existing, folded in for completeness) */}
        {npcBounties.length > 0 && (
          <div>
            <h2 className="text-lg font-semibold mb-3 text-amber-200 flex items-center gap-2">
              <ScrollText className="w-4 h-4" />
              NPC Warrants
            </h2>
            <div className="grid sm:grid-cols-2 gap-4" data-testid="npc-warrants-list">
              {npcBounties.slice(0, 8).map((b) => (
                <div
                  key={`${b.perpetrator_id}-${b.nation}`}
                  className="rounded-xl border border-amber-900/40 bg-amber-950/10 p-4"
                  data-testid={`npc-warrant-${b.perpetrator_id}`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="text-amber-100 font-semibold">{b.perpetrator_name}</div>
                    <div className="text-amber-300">{b.total_bounty}g</div>
                  </div>
                  <div className="text-xs text-stone-400">
                    {b.nation} · {b.open_crime_count} charge{b.open_crime_count === 1 ? '' : 's'}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Claim dialog */}
      <Dialog open={!!claimTarget} onOpenChange={(o) => !o && setClaimTarget(null)}>
        <DialogContent className="bg-stone-950 border-stone-700 text-stone-100" data-testid="claim-dialog">
          <DialogHeader>
            <DialogTitle className="text-xl text-red-200">
              Hunt {claimTarget?.perpetrator_name}
            </DialogTitle>
            <DialogDescription className="text-stone-400">
              A bounty of {claimTarget?.total_bounty}g stands on this head in {claimTarget?.nation}.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <div>
              <label className="text-xs text-stone-400">Your hunter</label>
              <select
                value={claimForm.character_id}
                onChange={(e) => setClaimForm({ ...claimForm, character_id: e.target.value })}
                className="w-full bg-stone-900 border border-stone-700 rounded-md px-3 py-2 text-stone-100"
                data-testid="claim-character-select"
              >
                {chars.map((c) => (
                  <option key={c.id} value={c.id}>{c.name} — {c.race}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs text-stone-400">Method</label>
              <div className="grid grid-cols-2 gap-2 mt-1">
                <button
                  type="button"
                  onClick={() => setClaimForm({ ...claimForm, method: 'captured' })}
                  className={`rounded-md border py-2 text-sm ${
                    claimForm.method === 'captured'
                      ? 'border-emerald-500/60 bg-emerald-950/40 text-emerald-100'
                      : 'border-stone-700 bg-stone-900 text-stone-300 hover:bg-stone-800'
                  }`}
                  data-testid="claim-method-captured"
                >
                  Captured
                </button>
                <button
                  type="button"
                  onClick={() => setClaimForm({ ...claimForm, method: 'killed' })}
                  className={`rounded-md border py-2 text-sm ${
                    claimForm.method === 'killed'
                      ? 'border-red-500/60 bg-red-950/40 text-red-100'
                      : 'border-stone-700 bg-stone-900 text-stone-300 hover:bg-stone-800'
                  }`}
                  data-testid="claim-method-killed"
                >
                  Killed
                </button>
              </div>
              {claimForm.method === 'killed' && (
                <p className="text-xs text-red-300/80 italic mt-2">
                  Choosing this retires the target permanently — they enter the Chronicles as fallen.
                </p>
              )}
            </div>
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setClaimTarget(null)} className="text-stone-300 hover:text-stone-100" data-testid="cancel-claim-btn">
              Cancel
            </Button>
            <Button
              onClick={doClaim}
              disabled={claiming || !claimForm.character_id}
              className={claimForm.method === 'killed'
                ? 'bg-red-800 hover:bg-red-900 text-red-50'
                : 'bg-emerald-800 hover:bg-emerald-900 text-emerald-50'}
              data-testid="submit-claim-btn"
            >
              {claiming
                ? (<><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Hunting…</>)
                : (<><Sword className="w-4 h-4 mr-2" /> Claim Bounty</>)}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default Wanted;
