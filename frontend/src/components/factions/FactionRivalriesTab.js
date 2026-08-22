import React, { useEffect, useState, useCallback } from 'react';
import { toast } from 'sonner';
import {
  Swords, Flame, Skull, Shield, Hammer, Crown, ScrollText, TreePine,
  TrendingUp, Handshake, AlertTriangle, ChevronRight,
} from 'lucide-react';
import {
  listFactionRivalries, declareFactionRivalry, escalateFactionRivalry,
  sueForPeace, listFactions,
} from '../../utils/api';
import { Button } from '../ui/button';
import { Textarea } from '../ui/textarea';

const ICONS = { shield: Shield, swords: Swords, skull: Skull, tree: TreePine, hammer: Hammer, crown: Crown, scroll: ScrollText, flame: Flame };

const STATUS_TONE = {
  dormant:         { text: 'text-gray-400',   bg: 'bg-gray-800/30',     border: 'border-gray-600/30',  label: 'Dormant' },
  tense:           { text: 'text-yellow-300', bg: 'bg-yellow-900/20',   border: 'border-yellow-600/40', label: 'Tense' },
  declared:        { text: 'text-orange-300', bg: 'bg-orange-900/20',   border: 'border-orange-600/40', label: 'Declared Rival' },
  escalated:       { text: 'text-red-300',    bg: 'bg-red-900/20',      border: 'border-red-600/40',    label: 'Escalated' },
  'sworn-enemies': { text: 'text-red-200',    bg: 'bg-red-900/40',      border: 'border-red-500/70',    label: 'Sworn Enemies' },
};

const IntensityBar = ({ intensity }) => {
  const pct = Math.max(0, Math.min(100, intensity));
  const color = pct >= 75 ? 'bg-red-500' : pct >= 50 ? 'bg-orange-500' : pct >= 25 ? 'bg-yellow-500' : 'bg-gray-500';
  return (
    <div className="w-full h-2 bg-gray-800 rounded-full overflow-hidden mt-1">
      <div className={`h-full ${color} transition-all`} style={{ width: `${pct}%` }} />
    </div>
  );
};

const FactionRivalriesTab = ({ slug, myCharsInFaction, factionName }) => {
  const [rivalries, setRivalries] = useState([]);
  const [allFactions, setAllFactions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showDeclare, setShowDeclare] = useState(false);
  const [busy, setBusy] = useState({});
  const [declareForm, setDeclareForm] = useState({
    actor_character_id: '', target_slug: '', reason: '',
  });

  const leaderActor = myCharsInFaction.find((m) => m.rank === 'leader');
  const canCommand = Boolean(leaderActor);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [r, f] = await Promise.allSettled([
        listFactionRivalries(slug),
        listFactions(),
      ]);
      if (r.status === 'fulfilled') setRivalries(r.value.data || []);
      if (f.status === 'fulfilled') setAllFactions((f.value.data || []).filter((x) => x.slug !== slug));
    } finally { setLoading(false); }
  }, [slug]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    if (leaderActor) {
      setDeclareForm((d) => ({ ...d, actor_character_id: d.actor_character_id || leaderActor.character_id }));
    }
  }, [leaderActor]);

  const handleDeclare = async (e) => {
    e.preventDefault();
    if (!declareForm.actor_character_id || !declareForm.target_slug) {
      toast.error('Pick your character and a target faction.');
      return;
    }
    try {
      await declareFactionRivalry(slug, declareForm.actor_character_id, declareForm.target_slug, declareForm.reason);
      toast.success('Rivalry declared. The heralds will spread the word.');
      setShowDeclare(false);
      setDeclareForm({ actor_character_id: leaderActor?.character_id || '', target_slug: '', reason: '' });
      await load();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to declare rivalry.');
    }
  };

  const handleEscalate = async (r) => {
    if (!leaderActor) return;
    setBusy((b) => ({ ...b, [r.id]: true }));
    try {
      await escalateFactionRivalry(slug, r.id, leaderActor.character_id, 10, '');
      toast.success(`Tensions rise with ${r.rival?.name}.`);
      await load();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to escalate.');
    } finally { setBusy((b) => ({ ...b, [r.id]: false })); }
  };

  const handlePeace = async (r) => {
    if (!leaderActor) return;
    if (!window.confirm(`Sue for peace with ${r.rival?.name}? Their leader is not bound by your decision.`)) return;
    setBusy((b) => ({ ...b, [r.id]: true }));
    try {
      await sueForPeace(slug, r.id, leaderActor.character_id);
      toast.success('Peace formally offered.');
      await load();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed.');
    } finally { setBusy((b) => ({ ...b, [r.id]: false })); }
  };

  if (loading) return <p className="text-gray-500 italic text-center py-8">The war-room scribes are tallying enemies…</p>;

  // Factions we can target = all OTHER factions not already in an active rivalry with us.
  const activeRivalIds = new Set(rivalries.filter((r) => r.intensity >= 25).map((r) => r.rival?.id));
  const targetableFactions = allFactions.filter((f) => !activeRivalIds.has(f.id));

  return (
    <div data-testid="faction-rivalries-tab">
      <div className="flex items-start justify-between gap-3 mb-4">
        <p className="text-xs text-gray-400 italic max-w-md">
          A rivalry is formally declared by the Leader, but it intensifies on its own
          whenever a member commits crimes on the rival's home soil.
        </p>
        {canCommand && targetableFactions.length > 0 && (
          <Button
            size="sm"
            onClick={() => setShowDeclare(true)}
            className="bg-gradient-to-r from-red-700 to-orange-700"
            data-testid="declare-rivalry-btn"
          >
            <AlertTriangle className="w-3 h-3 mr-1" /> Declare Rivalry
          </Button>
        )}
      </div>

      {rivalries.length === 0 ? (
        <p className="text-gray-500 italic text-center py-10" data-testid="rivalries-empty">
          {factionName} holds no rivalries at present.
        </p>
      ) : (
        <ul className="space-y-3">
          {rivalries.map((r) => {
            const tone = STATUS_TONE[r.status] || STATUS_TONE.dormant;
            const RivalIcon = ICONS[r.rival?.icon] || Swords;
            return (
              <li
                key={r.id}
                className={`glass-dark border rounded-lg p-4 ${tone.border}`}
                data-testid={`rivalry-row-${r.id}`}
              >
                <header className="flex items-center justify-between gap-2 flex-wrap">
                  <div className="flex items-center gap-3 min-w-0 flex-1">
                    <div className="p-2 rounded-lg" style={{ backgroundColor: `${r.rival?.color_hex || '#888'}22`, border: `1px solid ${r.rival?.color_hex || '#888'}66` }}>
                      <RivalIcon className="w-5 h-5" style={{ color: r.rival?.color_hex || '#aaa' }} />
                    </div>
                    <div className="min-w-0 flex-1">
                      <h4 className="font-bold text-gray-100 truncate" data-testid={`rival-name-${r.id}`}>
                        {r.rival?.name || 'Unknown faction'}
                      </h4>
                      <p className={`text-xs uppercase tracking-wider ${tone.text}`}>{tone.label}</p>
                    </div>
                  </div>
                  <span className="text-lg font-bold text-gray-200 font-mono" data-testid={`rivalry-intensity-${r.id}`}>
                    {r.intensity}/100
                  </span>
                </header>

                <IntensityBar intensity={r.intensity} />

                {r.reason && (
                  <p className="text-sm text-gray-300 italic mt-3 border-l-2 border-gray-600/40 pl-3">
                    &ldquo;{r.reason}&rdquo;
                  </p>
                )}

                {canCommand && (
                  <div className="flex gap-2 mt-3">
                    <Button
                      size="sm" variant="outline"
                      disabled={busy[r.id] || r.intensity >= 100}
                      onClick={() => handleEscalate(r)}
                      className="border-red-500/40 text-red-300 hover:bg-red-900/30"
                      data-testid={`escalate-rivalry-${r.id}`}
                    >
                      <TrendingUp className="w-3 h-3 mr-1" /> Escalate
                    </Button>
                    <Button
                      size="sm" variant="outline"
                      disabled={busy[r.id] || r.intensity === 0}
                      onClick={() => handlePeace(r)}
                      className="border-green-500/40 text-green-300 hover:bg-green-900/30"
                      data-testid={`peace-rivalry-${r.id}`}
                    >
                      <Handshake className="w-3 h-3 mr-1" /> Sue for Peace
                    </Button>
                  </div>
                )}

                {r.history && r.history.length > 0 && (
                  <details className="mt-3 text-xs">
                    <summary className="cursor-pointer text-gray-400 hover:text-gray-200">
                      Recent shifts ({r.history.length})
                    </summary>
                    <ul className="mt-2 space-y-1">
                      {r.history.slice(-6).reverse().map((h) => (
                        <li key={h.id} className="flex items-center gap-2 text-gray-400">
                          <ChevronRight className="w-3 h-3 flex-shrink-0" />
                          <span className={`font-mono ${h.delta >= 0 ? 'text-red-300' : 'text-green-300'}`}>
                            {h.delta >= 0 ? `+${h.delta}` : h.delta}
                          </span>
                          <span className="text-gray-500 uppercase text-[10px] tracking-wider">{h.kind}</span>
                          <span className="text-gray-300 truncate">{h.reason}</span>
                        </li>
                      ))}
                    </ul>
                  </details>
                )}
              </li>
            );
          })}
        </ul>
      )}

      {/* Declare modal */}
      {showDeclare && (
        <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4" onClick={() => setShowDeclare(false)}>
          <form
            onSubmit={handleDeclare}
            onClick={(e) => e.stopPropagation()}
            className="glass-dark border border-red-500/40 rounded-xl p-6 w-full max-w-md space-y-3"
            data-testid="declare-rivalry-form"
          >
            <h3 className="text-xl font-bold text-red-300" style={{ fontFamily: 'Georgia, serif' }}>
              Declare a Rivalry
            </h3>
            <p className="text-xs text-gray-400 italic">
              Only the Leader of {factionName} may formally name an enemy. Words spoken here cannot easily be unsaid.
            </p>
            <div>
              <label className="text-xs uppercase tracking-wider text-gray-400 block mb-1">Target faction</label>
              <select
                value={declareForm.target_slug}
                onChange={(e) => setDeclareForm((d) => ({ ...d, target_slug: e.target.value }))}
                className="w-full bg-black/40 border border-gray-600 rounded px-3 py-2 text-gray-100"
                required
                data-testid="declare-target-select"
              >
                <option value="">Choose a faction…</option>
                {targetableFactions.map((f) => (
                  <option key={f.id} value={f.slug}>
                    {f.name} — {f.nation_home || 'unaligned'}
                  </option>
                ))}
              </select>
            </div>
            <Textarea
              maxLength={400} rows={3} placeholder="The reason your faction speaks against them…"
              value={declareForm.reason}
              onChange={(e) => setDeclareForm((d) => ({ ...d, reason: e.target.value }))}
              className="bg-black/40 border-gray-600 text-gray-100"
              data-testid="declare-reason-input"
            />
            <div className="flex gap-2 justify-end pt-2">
              <Button type="button" variant="outline" onClick={() => setShowDeclare(false)}>Stand Down</Button>
              <Button type="submit" className="bg-gradient-to-r from-red-700 to-orange-700" data-testid="declare-submit-btn">
                <AlertTriangle className="w-3 h-3 mr-1" /> Declare
              </Button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
};

export default FactionRivalriesTab;
