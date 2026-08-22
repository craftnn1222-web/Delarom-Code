import React, { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { Loader2, Coins, Shield, Swords, Skull, TreePine, Hammer, Crown, ScrollText, Flame, Plus, Trash2 } from 'lucide-react';
import { fileFactionCharter, getMyCharacters, getMyFactionMemberships } from '../../utils/api';
import api from '../../utils/api';
import { Button } from '../ui/button';
import { Textarea } from '../ui/textarea';

const FACTION_CHARTER_COST = 5000;

const ICON_OPTIONS = [
  { key: 'shield', Icon: Shield },
  { key: 'swords', Icon: Swords },
  { key: 'skull',  Icon: Skull },
  { key: 'tree',   Icon: TreePine },
  { key: 'hammer', Icon: Hammer },
  { key: 'crown',  Icon: Crown },
  { key: 'scroll', Icon: ScrollText },
  { key: 'flame',  Icon: Flame },
];

const COLOR_OPTIONS = [
  '#a855f7', '#dc2626', '#16a34a', '#f59e0b', '#7c3aed', '#0ea5e9',
  '#475569', '#1f2937', '#be185d', '#0891b2', '#65a30d', '#ea580c',
];

const NATIONS = [
  { value: '', label: 'Unaligned' },
  { value: 'aigraels', label: 'Aigraels' },
  { value: 'dhor-kuldor', label: 'Dhor Kuldor' },
  { value: 'selindori', label: 'Selindori' },
  { value: 'ammeonon', label: 'Ammeonon' },
  { value: 'veiled-realms', label: 'The Veiled Realms' },
];

const CharterFactionDialog = ({ open, onClose, onSuccess, currentUserGold = 0 }) => {
  const [chars, setChars] = useState([]);
  const [memberships, setMemberships] = useState([]);
  const [goodsCatalogue, setGoodsCatalogue] = useState([]);
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState({
    character_id: '',
    name: '',
    motto: '',
    description: '',
    nation_home: '',
    color_hex: '#a855f7',
    icon: 'shield',
  });
  // Offered goods declared at charter time — seeded as specialties on approval.
  const [offeredGoods, setOfferedGoods] = useState([]);

  useEffect(() => {
    if (!open) return;
    (async () => {
      try {
        const [c, m, g] = await Promise.allSettled([
          getMyCharacters(),
          getMyFactionMemberships(),
          api.get('/economy/goods'),
        ]);
        if (c.status === 'fulfilled') setChars(c.value.data);
        if (m.status === 'fulfilled') setMemberships(m.value.data);
        if (g.status === 'fulfilled') setGoodsCatalogue(g.value.data || []);
      } catch { /* ignore */ }
    })();
  }, [open]);

  // Available characters = those NOT already in any active faction.
  const lockedCharIds = new Set(memberships.map((m) => m.character_id));
  const eligibleChars = chars.filter((c) => !lockedCharIds.has(c.id));

  useEffect(() => {
    if (!form.character_id && eligibleChars.length > 0) {
      setForm((f) => ({ ...f, character_id: eligibleChars[0].id }));
    }
  }, [eligibleChars, form.character_id]);

  if (!open) return null;

  const canAfford = currentUserGold >= FACTION_CHARTER_COST;
  const haveEligible = eligibleChars.length > 0;

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!canAfford) { toast.error(`Founding costs ${FACTION_CHARTER_COST} gold.`); return; }
    if (!form.character_id) { toast.error('Pick a character to lead the new faction.'); return; }
    if (form.description.length < 20) { toast.error('Charter description must be at least 20 characters.'); return; }
    // Sanity-check offered goods.
    for (const og of offeredGoods) {
      if (!og.good_slug || og.base_cost <= 0) {
        toast.error('Each offered good needs a slug and a positive base cost.');
        return;
      }
    }
    setSubmitting(true);
    try {
      const payload = {
        ...form,
        offered_goods: offeredGoods.length > 0
          ? offeredGoods.map((og) => ({
              good_slug: og.good_slug,
              base_cost: Number(og.base_cost),
              capacity: Number(og.capacity || 50),
              description: (og.description || '').slice(0, 400),
            }))
          : undefined,
      };
      const r = await fileFactionCharter(payload);
      toast.success(`Charter for "${r.data.name}" filed. Awaiting council review.`);
      onSuccess?.(r.data);
      onClose();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Charter submission failed.');
    } finally {
      setSubmitting(false);
    }
  };

  const addOffering = () => {
    if (offeredGoods.length >= 8) {
      toast.error('Charters may declare at most 8 founding offerings.');
      return;
    }
    setOfferedGoods([
      ...offeredGoods,
      { good_slug: goodsCatalogue[0]?.slug || '', base_cost: 50, capacity: 50, description: '' },
    ]);
  };
  const removeOffering = (idx) => {
    setOfferedGoods(offeredGoods.filter((_, i) => i !== idx));
  };
  const setOffering = (idx, patch) => {
    setOfferedGoods(offeredGoods.map((og, i) => (i === idx ? { ...og, ...patch } : og)));
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4" onClick={onClose}>
      <form
        onClick={(e) => e.stopPropagation()}
        onSubmit={handleSubmit}
        className="glass-dark border border-amber-500/40 rounded-xl p-6 w-full max-w-lg space-y-4 max-h-[90vh] overflow-y-auto"
        data-testid="charter-faction-form"
      >
        <div>
          <h3 className="text-2xl font-bold text-amber-200" style={{ fontFamily: 'Georgia, serif' }}>
            File a Charter
          </h3>
          <p className="text-xs text-gray-400 italic mt-1">
            Found your own faction. Your charter goes to the council for review.
            The fee of {FACTION_CHARTER_COST.toLocaleString()} gold is refunded if rejected,
            consumed if approved. On approval, your chosen character becomes Leader and three
            founding members swear in.
          </p>
        </div>

        {!canAfford && (
          <div className="rounded-lg border border-red-500/40 bg-red-950/30 p-3 text-sm text-red-200">
            You hold {currentUserGold.toLocaleString()} gold. The charter fee is{' '}
            {FACTION_CHARTER_COST.toLocaleString()}.
          </div>
        )}
        {!haveEligible && (
          <div className="rounded-lg border border-amber-500/40 bg-amber-950/30 p-3 text-sm text-amber-200">
            All your characters already belong to a faction. Have one leave first, or create a new
            character to lead the new faction.
          </div>
        )}

        <div>
          <label className="text-xs uppercase tracking-wider text-gray-400 block mb-1">Founder</label>
          <select
            required
            value={form.character_id}
            onChange={(e) => setForm({ ...form, character_id: e.target.value })}
            className="w-full bg-black/40 border border-gray-600 rounded px-3 py-2 text-gray-100"
            data-testid="charter-founder-select"
          >
            <option value="">Choose a character…</option>
            {eligibleChars.map((c) => (
              <option key={c.id} value={c.id}>{c.name} — {c.race} {c.character_class}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="text-xs uppercase tracking-wider text-gray-400 block mb-1">Faction name</label>
          <input
            type="text" required minLength={3} maxLength={80}
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            placeholder="e.g. The Sable Order"
            className="w-full bg-black/40 border border-gray-600 rounded px-3 py-2 text-gray-100"
            data-testid="charter-name-input"
          />
        </div>

        <div>
          <label className="text-xs uppercase tracking-wider text-gray-400 block mb-1">Motto (optional)</label>
          <input
            type="text" maxLength={200}
            value={form.motto}
            onChange={(e) => setForm({ ...form, motto: e.target.value })}
            placeholder="A single line that captures the order's spirit"
            className="w-full bg-black/40 border border-gray-600 rounded px-3 py-2 text-gray-100 italic"
            data-testid="charter-motto-input"
          />
        </div>

        <div>
          <label className="text-xs uppercase tracking-wider text-gray-400 block mb-1">
            Charter (what is your faction for?)
          </label>
          <Textarea
            required minLength={20} maxLength={2000} rows={5}
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
            placeholder="Three to four sentences. Who joins? What do they hold sacred? What do they fight for or against?"
            className="bg-black/40 border-gray-600 text-gray-100"
            data-testid="charter-description-input"
          />
          <p className="text-xs text-gray-500 mt-1">{form.description.length} / 2000</p>
        </div>

        <div>
          <label className="text-xs uppercase tracking-wider text-gray-400 block mb-1">Home nation</label>
          <select
            value={form.nation_home}
            onChange={(e) => setForm({ ...form, nation_home: e.target.value })}
            className="w-full bg-black/40 border border-gray-600 rounded px-3 py-2 text-gray-100"
            data-testid="charter-nation-select"
          >
            {NATIONS.map((n) => <option key={n.value} value={n.value}>{n.label}</option>)}
          </select>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-xs uppercase tracking-wider text-gray-400 block mb-1">Sigil</label>
            <div className="grid grid-cols-4 gap-1.5">
              {ICON_OPTIONS.map(({ key, Icon }) => (
                <button
                  key={key} type="button"
                  onClick={() => setForm({ ...form, icon: key })}
                  className={`p-2 rounded border transition ${
                    form.icon === key
                      ? 'border-amber-400 bg-amber-900/30'
                      : 'border-gray-600 hover:border-gray-400'
                  }`}
                  data-testid={`charter-icon-${key}`}
                >
                  <Icon className="w-4 h-4 mx-auto" style={{ color: form.color_hex }} />
                </button>
              ))}
            </div>
          </div>
          <div>
            <label className="text-xs uppercase tracking-wider text-gray-400 block mb-1">Colour</label>
            <div className="grid grid-cols-6 gap-1.5">
              {COLOR_OPTIONS.map((c) => (
                <button
                  key={c} type="button"
                  onClick={() => setForm({ ...form, color_hex: c })}
                  className={`h-7 rounded border-2 transition ${
                    form.color_hex === c ? 'border-amber-200' : 'border-transparent'
                  }`}
                  style={{ backgroundColor: c }}
                  data-testid={`charter-color-${c}`}
                />
              ))}
            </div>
          </div>
        </div>

        {/* OFFERED GOODS — economy lineup */}
        <div className="border-t border-gray-700/40 pt-3" data-testid="charter-offerings-section">
          <div className="flex items-center justify-between mb-2">
            <label className="text-xs uppercase tracking-wider text-gray-400">
              Offerings ({offeredGoods.length}/8) — what your faction will produce
            </label>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={addOffering}
              disabled={offeredGoods.length >= 8 || goodsCatalogue.length === 0}
              className="text-xs"
              data-testid="charter-add-offering-btn"
            >
              <Plus className="w-3 h-3 mr-1" />
              Add
            </Button>
          </div>
          {offeredGoods.length === 0 ? (
            <p className="text-xs text-gray-500 italic">
              Optional, but recommended. You can also add offerings after approval
              via the Offerings tab. Goods come from the realm catalogue.
            </p>
          ) : (
            <div className="space-y-2">
              {offeredGoods.map((og, i) => (
                <div
                  key={i}
                  className="p-2 rounded bg-black/30 border border-amber-500/20 grid grid-cols-12 gap-2"
                  data-testid={`charter-offering-row-${i}`}
                >
                  <select
                    value={og.good_slug}
                    onChange={(e) => setOffering(i, { good_slug: e.target.value })}
                    className="col-span-5 bg-black/50 border border-gray-600 rounded px-2 py-1 text-xs text-gray-100"
                    data-testid={`charter-offering-good-${i}`}
                  >
                    {goodsCatalogue.map((g) => (
                      <option key={g.slug} value={g.slug}>
                        {g.name} ({g.unit})
                      </option>
                    ))}
                  </select>
                  <input
                    type="number" min="1"
                    value={og.base_cost}
                    onChange={(e) => setOffering(i, { base_cost: e.target.value })}
                    placeholder="base cost"
                    title="Base cost in gold per unit"
                    className="col-span-3 bg-black/50 border border-gray-600 rounded px-2 py-1 text-xs text-gray-100"
                    data-testid={`charter-offering-cost-${i}`}
                  />
                  <input
                    type="number" min="1"
                    value={og.capacity}
                    onChange={(e) => setOffering(i, { capacity: e.target.value })}
                    placeholder="cap/tick"
                    title="Capacity per tick"
                    className="col-span-3 bg-black/50 border border-gray-600 rounded px-2 py-1 text-xs text-gray-100"
                    data-testid={`charter-offering-cap-${i}`}
                  />
                  <button
                    type="button"
                    onClick={() => removeOffering(i)}
                    className="col-span-1 flex items-center justify-center text-rose-300 hover:text-rose-200"
                    title="Remove"
                    data-testid={`charter-offering-remove-${i}`}
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="flex items-center justify-between pt-2 border-t border-gray-700/40">
          <p className="text-xs text-amber-200 inline-flex items-center gap-1">
            <Coins className="w-3.5 h-3.5" /> Fee: {FACTION_CHARTER_COST.toLocaleString()} gold
          </p>
          <div className="flex gap-2">
            <Button type="button" variant="outline" onClick={onClose}>Cancel</Button>
            <Button
              type="submit"
              disabled={submitting || !canAfford || !haveEligible}
              className="bg-gradient-to-r from-amber-600 to-orange-600"
              data-testid="charter-submit-btn"
            >
              {submitting ? <Loader2 className="w-4 h-4 mr-1 animate-spin" /> : null}
              File Charter
            </Button>
          </div>
        </div>
      </form>
    </div>
  );
};

export default CharterFactionDialog;
