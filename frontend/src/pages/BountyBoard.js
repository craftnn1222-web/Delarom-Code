import React, { useEffect, useState } from 'react';
import api, { commissionPoster } from '../utils/api';
import { toast } from 'sonner';
import { Skull, Coins, Filter, FileImage } from 'lucide-react';

/**
 * BountyBoard — public, anonymous-friendly page listing huntable bounties.
 * Players can use this to find NPC criminals to hunt and to see which
 * fellow players are wanted in each nation.
 */

const SEVERITY_TINT = {
  petty:    'border-yellow-500/30 bg-yellow-900/10 text-yellow-100',
  minor:    'border-orange-500/30 bg-orange-900/10 text-orange-100',
  major:    'border-red-500/40  bg-red-900/30  text-red-50',
  capital:  'border-rose-500/40 bg-rose-900/20 text-rose-50',
  regicide: 'border-fuchsia-500/50 bg-fuchsia-900/30 text-fuchsia-50',
};

const NATIONS = ['ammeonon', 'selindori', 'dhor-kuldor', 'aigraels', 'veiled-realms'];

const BountyBoard = () => {
  const [bounties, setBounties] = useState([]);
  const [loading, setLoading] = useState(true);
  const [nationFilter, setNationFilter] = useState('');

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    const url = nationFilter
      ? `/bounty-board?nation=${encodeURIComponent(nationFilter)}`
      : '/bounty-board';
    api.get(url)
      .then((res) => { if (!cancelled) setBounties(res.data || []); })
      .catch((err) => { if (!cancelled) console.error('Failed to load bounty board:', err); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [nationFilter]);

  const npcBounties = bounties.filter((b) => b.perpetrator_type === 'npc');
  const charBounties = bounties.filter((b) => b.perpetrator_type === 'character');

  return (
    <div className="pb-10">
      <header className="max-w-5xl mx-auto px-4 pt-6 pb-6">
        <h2 className="text-2xl sm:text-3xl font-bold text-amber-300 flex items-center gap-3">
          <Skull className="w-7 h-7" />
          Bounty Board
        </h2>
        <p className="text-gray-300 mt-2 max-w-3xl text-sm">
          By order of every crown in Delarom — these warrants are open for collection.
          NPC fugitives may be brought in (alive or dead) for the listed reward.
          Player criminals of major rank or worse have an open warrant; bring proof of
          capture and the local magistrate will pay you.
        </p>
        <div className="mt-6 flex items-center gap-2 flex-wrap" data-testid="bounty-filter">
          <span className="text-xs text-gray-400 uppercase tracking-widest flex items-center gap-1">
            <Filter className="w-3 h-3" /> Nation:
          </span>
          <button
            onClick={() => setNationFilter('')}
            className={`text-xs px-3 py-1 rounded-full border ${nationFilter === '' ? 'bg-amber-600/40 border-amber-400 text-white' : 'bg-black/30 border-gray-600/40 text-gray-300 hover:text-white'}`}
            data-testid="bounty-filter-all"
          >
            All
          </button>
          {NATIONS.map((n) => (
            <button
              key={n}
              onClick={() => setNationFilter(n)}
              className={`text-xs px-3 py-1 rounded-full border capitalize ${nationFilter === n ? 'bg-amber-600/40 border-amber-400 text-white' : 'bg-black/30 border-gray-600/40 text-gray-300 hover:text-white'}`}
              data-testid={`bounty-filter-${n}`}
            >
              {n.replace('-', ' ')}
            </button>
          ))}
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 space-y-8">
        {loading && (
          <p className="text-center text-gray-400 italic">Reading the warrants…</p>
        )}

        {!loading && bounties.length === 0 && (
          <div className="glass-dark p-8 rounded-xl text-center" data-testid="bounty-empty">
            <p className="text-gray-300 italic">The boards are clean. For now.</p>
          </div>
        )}

        {!loading && npcBounties.length > 0 && (
          <section data-testid="bounty-board-npcs">
            <h2 className="text-2xl font-bold text-rose-300 mb-3 uppercase tracking-widest">
              Fugitive Bounties ({npcBounties.length})
            </h2>
            <div className="grid sm:grid-cols-2 gap-3">
              {npcBounties.map((b) => (
                <BountyCard key={`${b.perpetrator_type}-${b.perpetrator_id}-${b.nation}`} bounty={b} />
              ))}
            </div>
          </section>
        )}

        {!loading && charBounties.length > 0 && (
          <section data-testid="bounty-board-characters">
            <h2 className="text-2xl font-bold text-amber-300 mb-3 uppercase tracking-widest">
              Outlaw Warrants ({charBounties.length})
            </h2>
            <div className="grid sm:grid-cols-2 gap-3">
              {charBounties.map((b) => (
                <BountyCard key={`${b.perpetrator_type}-${b.perpetrator_id}-${b.nation}`} bounty={b} />
              ))}
            </div>
          </section>
        )}
      </main>
    </div>
  );
};

const BountyCard = ({ bounty }) => {
  const tint = SEVERITY_TINT[bounty.worst_severity] || SEVERITY_TINT.minor;
  const [posterUrl, setPosterUrl] = useState(bounty.poster_image_id ? `/api/image/${bounty.poster_image_id}` : null);
  const [generating, setGenerating] = useState(false);
  const [open, setOpen] = useState(false);

  const handleCommission = async () => {
    if (!bounty.id) { toast.error("This bounty cannot be illustrated."); return; }
    setGenerating(true);
    try {
      const r = await commissionPoster(bounty.id);
      setPosterUrl(r.data.image_url);
      if (!r.data.cached) toast.success('The herald printed a fresh poster.');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'The herald has no ink.');
    } finally { setGenerating(false); }
  };

  return (
    <div
      className={`p-4 rounded-xl border ${tint}`}
      data-testid={`bounty-${bounty.perpetrator_type}-${bounty.perpetrator_id}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="font-bold text-lg truncate">
            {bounty.perpetrator_name || (bounty.perpetrator_type === 'npc' ? 'Unknown Fugitive' : 'Unknown Outlaw')}
          </p>
          <p className="text-xs uppercase tracking-widest opacity-80 capitalize">
            {bounty.perpetrator_type === 'npc' ? 'NPC fugitive' : 'Player outlaw'}
            <span className="ml-2">· {bounty.nation}</span>
          </p>
        </div>
        <div className="text-right flex-shrink-0">
          <p className="text-2xl font-bold font-mono flex items-center gap-1">
            <Coins className="w-5 h-5" /> {bounty.total_bounty.toLocaleString()}
          </p>
          <p className="text-[10px] uppercase opacity-80">{bounty.worst_severity}</p>
        </div>
      </div>
      <p className="text-xs mt-2 opacity-90">
        {bounty.open_crime_count} open crime{bounty.open_crime_count === 1 ? '' : 's'}
      </p>

      {/* WANTED POSTER section (Phase 5) */}
      <div className="mt-3 pt-3 border-t border-current/20">
        {posterUrl ? (
          <button
            onClick={() => setOpen(true)}
            className="block w-full"
            data-testid={`bounty-poster-${bounty.id}`}
          >
            <img
              src={posterUrl}
              alt={`Wanted poster for ${bounty.perpetrator_name}`}
              className="w-full h-40 object-cover rounded-lg opacity-90 hover:opacity-100 transition border border-current/30"
            />
            <p className="text-[10px] uppercase tracking-widest opacity-70 mt-1">Tap to view</p>
          </button>
        ) : bounty.id ? (
          <button
            onClick={handleCommission}
            disabled={generating}
            className="text-xs px-3 py-1 rounded-full border border-current/40 bg-black/30 hover:bg-current/10 transition flex items-center gap-1"
            data-testid={`commission-poster-${bounty.id}`}
          >
            <FileImage className="w-3 h-3" />
            {generating ? 'The herald sketches…' : 'Commission Wanted Poster'}
          </button>
        ) : null}
      </div>

      {open && posterUrl && (
        <div className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4" onClick={() => setOpen(false)}>
          <img
            src={posterUrl}
            alt="Wanted poster"
            className="max-h-[90vh] max-w-[90vw] rounded-xl shadow-2xl border-2 border-amber-700/60"
          />
        </div>
      )}
    </div>
  );
};

export default BountyBoard;