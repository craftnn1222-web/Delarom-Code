import React, { useEffect, useState, useCallback } from 'react';
import { Truck, Plus, ShieldAlert, Hourglass, CheckCircle2, XCircle, Coins, MapPin } from 'lucide-react';
import { Button } from './ui/button';
import { toast } from 'sonner';
import api from '../utils/api';

/**
 * Caravans board.
 *
 * Two modes, controlled by props:
 *   - `factionSlug` set → list ONLY this faction's caravans and (if `canPost`)
 *     show the "Post Caravan" composer.
 *   - `factionSlug` null → public marketplace view: list all OPEN caravans
 *     from every faction so players can claim a haul.
 *
 * Players claim a caravan against one of their characters, RP the haul in
 * the world, then come back here and mark it Completed (success or failure).
 */

const STATUS_TONES = {
  open:      { color: 'text-amber-200',    Icon: Truck },
  claimed:   { color: 'text-blue-300',     Icon: Hourglass },
  completed: { color: 'text-emerald-300',  Icon: CheckCircle2 },
  failed:    { color: 'text-rose-300',     Icon: XCircle },
  cancelled: { color: 'text-gray-400',     Icon: XCircle },
  expired:   { color: 'text-gray-400',     Icon: XCircle },
};

const formatGold = (n) => `${Number(n || 0).toLocaleString()}g`;

const CaravansBoard = ({ factionSlug = null, canPost = false, currentUserCharacterIds = [] }) => {
  const [caravans, setCaravans] = useState([]);
  const [goods, setGoods] = useState([]);
  const [cities, setCities] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState({
    good_slug: '',
    quantity: 50,
    to_city_slug: '',
    reward_gold: 400,
    description: '',
    danger_note: '',
    expires_in_hours: 72,
  });
  const [characterOptions, setCharacterOptions] = useState([]);

  const loadAll = useCallback(async () => {
    setLoading(true);
    try {
      const url = factionSlug
        ? `/economy/caravans?from_faction_slug=${factionSlug}`
        : '/economy/caravans?status=open';
      const requests = [api.get(url)];
      if (canPost && goods.length === 0) requests.push(api.get('/economy/goods'));
      const results = await Promise.allSettled(requests);
      if (results[0].status === 'fulfilled') setCaravans(results[0].value.data || []);
      if (results[1] && results[1].status === 'fulfilled') setGoods(results[1].value.data || []);
      // Also load my characters for the Claim flow.
      try {
        const me = await api.get('/characters');
        setCharacterOptions(me.data || []);
      } catch {
        /* unauthenticated viewer — claim controls just won't render */
      }
    } finally {
      setLoading(false);
    }
  }, [factionSlug, canPost, goods.length]);

  const loadCitiesIfNeeded = useCallback(async () => {
    if (cities.length > 0) return;
    const nations = ['aigraels', 'dhor-kuldor', 'selindori', 'ammeonon'];
    const r = await Promise.allSettled(nations.map((n) => api.get(`/cities/${n}`)));
    const all = [];
    r.forEach((row, idx) => {
      if (row.status === 'fulfilled' && Array.isArray(row.value.data)) {
        row.value.data.forEach((c) => all.push({ ...c, nation: nations[idx] }));
      }
    });
    setCities(all);
  }, [cities.length]);

  useEffect(() => { loadAll(); }, [loadAll]);

  const openComposer = async () => {
    await loadCitiesIfNeeded();
    setForm({
      good_slug: goods[0]?.slug || '',
      quantity: 50,
      to_city_slug: '',
      reward_gold: 400,
      description: '',
      danger_note: '',
      expires_in_hours: 72,
    });
    setShowForm(true);
  };

  const submitPost = async () => {
    if (!form.good_slug || !form.to_city_slug) {
      toast.error('Pick a good and a destination city.');
      return;
    }
    if (form.reward_gold <= 0) {
      toast.error('Set a positive reward.');
      return;
    }
    setBusy(true);
    try {
      await api.post(`/economy/factions/${factionSlug}/caravans`, {
        good_slug: form.good_slug,
        quantity: Number(form.quantity),
        to_city_slug: form.to_city_slug,
        reward_gold: Number(form.reward_gold),
        description: form.description || '',
        danger_note: form.danger_note || '',
        expires_in_hours: Number(form.expires_in_hours || 72),
      });
      toast.success('Caravan posted.');
      setShowForm(false);
      await loadAll();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to post caravan.');
    } finally {
      setBusy(false);
    }
  };

  const claim = async (caravanId, characterId) => {
    if (!characterId) {
      toast.error('Pick which character claims this caravan.');
      return;
    }
    try {
      await api.post(`/economy/caravans/${caravanId}/claim`, { character_id: characterId });
      toast.success('Caravan claimed. Travel safely.');
      await loadAll();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Could not claim.');
    }
  };

  const complete = async (caravanId, success, story) => {
    try {
      await api.post(`/economy/caravans/${caravanId}/complete`, { success, story: story || '' });
      toast.success(success ? 'Delivered. Reward credited.' : 'Marked as lost en route.');
      await loadAll();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Could not finalise.');
    }
  };

  const cancel = async (caravanId) => {
    if (!window.confirm('Cancel this caravan? Reward gold is refunded to you.')) return;
    try {
      await api.post(`/economy/caravans/${caravanId}/cancel`);
      toast.success('Caravan cancelled, reward refunded.');
      await loadAll();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Could not cancel.');
    }
  };

  if (loading) return <p className="text-gray-400 italic">Loading caravans…</p>;

  return (
    <section data-testid="caravans-board">
      <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
        <div>
          <h2 className="text-sm uppercase tracking-[0.3em] text-gray-400 flex items-center gap-2">
            <Truck className="w-4 h-4" />
            {factionSlug ? 'Faction Caravans' : 'Open Caravan Board'}
            <span className="text-gray-500">({caravans.length})</span>
          </h2>
          <p className="text-xs text-gray-500 mt-1 italic">
            {factionSlug
              ? 'One-off paid hauls this faction has posted. Players can claim, deliver, and earn the reward.'
              : 'Open caravan jobs posted by factions across the realms. Claim one and roleplay the journey.'}
          </p>
        </div>
        {factionSlug && canPost && (
          <Button
            type="button"
            onClick={openComposer}
            className="bg-amber-600 hover:bg-amber-700 text-black"
            data-testid="caravan-post-btn"
          >
            <Plus className="w-4 h-4 mr-1" />
            Post Caravan
          </Button>
        )}
      </div>

      {caravans.length === 0 ? (
        <div
          className="p-6 rounded-xl glass-dark border border-gray-700/40 text-center"
          data-testid="caravans-empty"
        >
          <Truck className="w-8 h-8 mx-auto mb-2 text-gray-500" />
          <p className="text-gray-400 italic">
            {factionSlug
              ? "No caravans posted yet. As Leader you can post a paid haul above."
              : 'No open caravans right now. Check back after a faction posts a fresh haul.'}
          </p>
        </div>
      ) : (
        <div className="grid sm:grid-cols-2 gap-3" data-testid="caravans-list">
          {caravans.map((c) => {
            const tone = STATUS_TONES[c.status] || STATUS_TONES.open;
            const ToneIcon = tone.Icon;
            const isMyClaim = c.claimed_by_character_id &&
              currentUserCharacterIds.includes(c.claimed_by_character_id);
            return (
              <div
                key={c.id}
                className="p-3 rounded-lg glass-dark border border-amber-500/20"
                data-testid={`caravan-${c.id}`}
              >
                <div className="flex items-start gap-2">
                  <ToneIcon className={`w-5 h-5 mt-1 flex-shrink-0 ${tone.color}`} />
                  <div className="flex-1 min-w-0">
                    <p className="font-semibold text-amber-100">
                      {c.quantity}× {c.good_name || c.good_slug}{' '}
                      <span className="text-[10px] uppercase tracking-wider text-amber-200/60">
                        · {c.status}
                      </span>
                    </p>
                    <p className="text-xs text-amber-200/70 mt-1 flex items-center gap-1">
                      <MapPin className="w-3 h-3" />
                      {c.from_faction_name || c.from_faction_slug}{' → '}{c.to_city_name || c.to_city_slug}
                    </p>
                    {c.description && (
                      <p className="text-xs text-gray-400 italic mt-1 line-clamp-2">{c.description}</p>
                    )}
                    {c.danger_note && (
                      <p className="text-[11px] text-rose-300/90 mt-1 flex items-center gap-1">
                        <ShieldAlert className="w-3 h-3" />
                        {c.danger_note}
                      </p>
                    )}
                    {c.claimed_by_character_name && (
                      <p className="text-[11px] text-blue-300/80 mt-1">
                        Claimed by {c.claimed_by_character_name}
                      </p>
                    )}
                  </div>
                  <div className="text-right">
                    <p className="text-amber-200 font-bold flex items-center gap-1">
                      <Coins className="w-3.5 h-3.5" />
                      {formatGold(c.reward_gold)}
                    </p>
                  </div>
                </div>

                {/* Action row */}
                {c.status === 'open' && characterOptions.length > 0 && (
                  <ClaimRow
                    characters={characterOptions}
                    onClaim={(charId) => claim(c.id, charId)}
                  />
                )}
                {c.status === 'open' && canPost && factionSlug && (
                  <Button
                    type="button" size="sm" variant="outline"
                    className="mt-2 text-xs text-rose-300 border-rose-500/40 hover:bg-rose-900/30"
                    onClick={() => cancel(c.id)}
                    data-testid={`caravan-cancel-${c.id}`}
                  >
                    Cancel & Refund
                  </Button>
                )}
                {c.status === 'claimed' && isMyClaim && (
                  <CompleteRow caravanId={c.id} onComplete={complete} />
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Composer modal */}
      {showForm && (
        <div className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4">
          <div
            className="glass-dark border border-amber-500/40 rounded-xl p-5 max-w-md w-full"
            data-testid="caravan-composer-modal"
          >
            <h3 className="text-lg font-semibold text-amber-200 mb-3">Post New Caravan</h3>
            <div className="space-y-3">
              <div>
                <label className="text-xs uppercase tracking-wider text-amber-200/70">Good</label>
                <select
                  value={form.good_slug}
                  onChange={(e) => setForm({ ...form, good_slug: e.target.value })}
                  className="w-full bg-black/50 border border-amber-500/40 rounded p-2 text-sm text-amber-100"
                  data-testid="caravan-form-good"
                >
                  {goods.map((g) => (
                    <option key={g.slug} value={g.slug}>{g.name} ({g.unit})</option>
                  ))}
                </select>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs uppercase tracking-wider text-amber-200/70">Quantity</label>
                  <input
                    type="number" min="1"
                    value={form.quantity}
                    onChange={(e) => setForm({ ...form, quantity: e.target.value })}
                    className="w-full bg-black/50 border border-amber-500/40 rounded p-2 text-sm text-amber-100"
                    data-testid="caravan-form-quantity"
                  />
                </div>
                <div>
                  <label className="text-xs uppercase tracking-wider text-amber-200/70">Reward (g)</label>
                  <input
                    type="number" min="1"
                    value={form.reward_gold}
                    onChange={(e) => setForm({ ...form, reward_gold: e.target.value })}
                    className="w-full bg-black/50 border border-amber-500/40 rounded p-2 text-sm text-amber-100"
                    data-testid="caravan-form-reward"
                  />
                </div>
              </div>
              <div>
                <label className="text-xs uppercase tracking-wider text-amber-200/70">Destination city</label>
                <select
                  value={form.to_city_slug}
                  onChange={(e) => setForm({ ...form, to_city_slug: e.target.value })}
                  className="w-full bg-black/50 border border-amber-500/40 rounded p-2 text-sm text-amber-100"
                  data-testid="caravan-form-city"
                >
                  <option value="">— pick a city —</option>
                  {cities.map((c) => (
                    <option key={`${c.nation}-${c.slug}`} value={c.slug}>
                      {c.name} ({c.nation})
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-xs uppercase tracking-wider text-amber-200/70">Brief (optional)</label>
                <textarea
                  rows={2}
                  value={form.description}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                  className="w-full bg-black/50 border border-amber-500/40 rounded p-2 text-sm text-amber-100"
                  placeholder="What's the haul about? Who needs it?"
                  data-testid="caravan-form-description"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs uppercase tracking-wider text-amber-200/70">Danger note</label>
                  <input
                    type="text"
                    value={form.danger_note}
                    onChange={(e) => setForm({ ...form, danger_note: e.target.value })}
                    placeholder="bandits? weather?"
                    className="w-full bg-black/50 border border-amber-500/40 rounded p-2 text-sm text-amber-100"
                    data-testid="caravan-form-danger"
                  />
                </div>
                <div>
                  <label className="text-xs uppercase tracking-wider text-amber-200/70">Expires in (hours)</label>
                  <input
                    type="number" min="1" max="720"
                    value={form.expires_in_hours}
                    onChange={(e) => setForm({ ...form, expires_in_hours: e.target.value })}
                    className="w-full bg-black/50 border border-amber-500/40 rounded p-2 text-sm text-amber-100"
                    data-testid="caravan-form-expires"
                  />
                </div>
              </div>
            </div>
            <div className="flex justify-end gap-2 mt-4">
              <Button type="button" variant="outline" onClick={() => setShowForm(false)} disabled={busy}>
                Cancel
              </Button>
              <Button
                type="button" onClick={submitPost} disabled={busy}
                className="bg-amber-600 hover:bg-amber-700 text-black"
                data-testid="caravan-form-save"
              >
                {busy ? 'Posting…' : 'Post Caravan'}
              </Button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
};

const ClaimRow = ({ characters, onClaim }) => {
  const [charId, setCharId] = useState(characters[0]?.id || '');
  return (
    <div className="flex gap-2 mt-2">
      <select
        value={charId}
        onChange={(e) => setCharId(e.target.value)}
        className="flex-1 bg-black/50 border border-amber-500/40 rounded p-1 text-xs text-amber-100"
        data-testid="caravan-claim-char-select"
      >
        {characters.map((c) => (
          <option key={c.id} value={c.id}>{c.name}</option>
        ))}
      </select>
      <Button
        type="button" size="sm"
        onClick={() => onClaim(charId)}
        className="bg-amber-600 hover:bg-amber-700 text-black text-xs"
        data-testid="caravan-claim-btn"
      >
        Claim
      </Button>
    </div>
  );
};

const CompleteRow = ({ caravanId, onComplete }) => {
  const [story, setStory] = useState('');
  return (
    <div className="mt-2 space-y-1">
      <textarea
        rows={2}
        value={story}
        onChange={(e) => setStory(e.target.value)}
        placeholder="Optional journey log (shown on the world Chronicle)…"
        className="w-full bg-black/50 border border-amber-500/40 rounded p-1 text-xs text-amber-100"
        data-testid={`caravan-story-${caravanId}`}
      />
      <div className="flex gap-1">
        <Button
          type="button" size="sm"
          className="bg-emerald-600 hover:bg-emerald-700 text-xs"
          onClick={() => onComplete(caravanId, true, story)}
          data-testid={`caravan-success-${caravanId}`}
        >
          <CheckCircle2 className="w-3 h-3 mr-1" />
          Delivered
        </Button>
        <Button
          type="button" size="sm" variant="outline"
          className="text-xs text-rose-300 border-rose-500/40 hover:bg-rose-900/30"
          onClick={() => onComplete(caravanId, false, story)}
          data-testid={`caravan-fail-${caravanId}`}
        >
          <XCircle className="w-3 h-3 mr-1" />
          Lost
        </Button>
      </div>
    </div>
  );
};

export default CaravansBoard;
