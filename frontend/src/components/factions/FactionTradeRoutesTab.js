import React, { useEffect, useState, useCallback } from 'react';
import { Plus, Trash2, ArrowRight, AlertTriangle, Coins } from 'lucide-react';
import { Button } from '../ui/button';
import { toast } from 'sonner';
import api from '../../utils/api';

/**
 * Faction Trade Routes tab.
 *
 * Public view: every standing contract this faction originates (active +
 * broken). Leader / admin actions: propose a NEW route, BREAK an active route.
 *
 * Mirrors the admin endpoints in scope but locks `from_faction_slug` to the
 * tab's `factionSlug` so a leader cannot spoof contracts for other factions.
 */
const FactionTradeRoutesTab = ({ factionSlug, canEdit }) => {
  const [contracts, setContracts] = useState([]);
  const [specialties, setSpecialties] = useState([]);
  const [cities, setCities] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    good_slug: '',
    to_type: 'city',
    to_city_slug: '',
    to_nation: '',
    tariff_pct: 25,
    quantity_per_tick: 50,
  });
  const [busy, setBusy] = useState(false);
  const [breakingId, setBreakingId] = useState(null);
  const [breakReason, setBreakReason] = useState('');

  const loadAll = useCallback(async () => {
    setLoading(true);
    try {
      const [cRes, sRes] = await Promise.allSettled([
        api.get(`/economy/factions/${factionSlug}/contracts`),
        api.get(`/economy/factions/${factionSlug}/specialties`),
      ]);
      if (cRes.status === 'fulfilled') setContracts(cRes.value.data || []);
      if (sRes.status === 'fulfilled') setSpecialties(sRes.value.data?.specialties || []);
    } finally {
      setLoading(false);
    }
  }, [factionSlug]);

  // Cities can be loaded lazily — we use them for the destination dropdown.
  const loadCities = useCallback(async () => {
    try {
      // Load only the nation-meta endpoint, then per-nation as we need.
      // For v1 we just grab the most common nations on first open.
      const nations = ['aigraels', 'dhor-kuldor', 'selindori', 'ammeonon'];
      const results = await Promise.allSettled(nations.map((n) => api.get(`/cities/${n}`)));
      const all = [];
      results.forEach((r, idx) => {
        if (r.status === 'fulfilled' && Array.isArray(r.value.data)) {
          r.value.data.forEach((c) => all.push({ ...c, nation: nations[idx] }));
        }
      });
      setCities(all);
    } catch (err) {
      console.error('city lookup failed', err);
    }
  }, []);

  useEffect(() => { loadAll(); }, [loadAll]);

  const openForm = async () => {
    if (specialties.length === 0) {
      toast.error('Add at least one offering before proposing a trade route.');
      return;
    }
    if (cities.length === 0) await loadCities();
    setForm({
      good_slug: specialties[0].good_slug,
      to_type: 'city',
      to_city_slug: '',
      to_nation: '',
      tariff_pct: 25,
      quantity_per_tick: 50,
    });
    setShowForm(true);
  };

  const submit = async () => {
    if (!form.good_slug || !form.to_city_slug) {
      toast.error('Pick a good and a destination city.');
      return;
    }
    setBusy(true);
    try {
      await api.post(`/economy/factions/${factionSlug}/contracts`, {
        from_faction_slug: factionSlug,
        good_slug: form.good_slug,
        to_type: 'city',
        to_city_slug: form.to_city_slug,
        to_nation: form.to_nation,
        tariff_pct: Number(form.tariff_pct),
        quantity_per_tick: Number(form.quantity_per_tick),
      });
      toast.success('Trade route opened.');
      setShowForm(false);
      await loadAll();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Could not open the route.');
    } finally {
      setBusy(false);
    }
  };

  const breakContract = async (id) => {
    setBusy(true);
    try {
      await api.post(`/economy/factions/${factionSlug}/contracts/${id}/break`, { reason: breakReason });
      toast.success('Contract broken.');
      setBreakingId(null);
      setBreakReason('');
      await loadAll();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Could not break the route.');
    } finally {
      setBusy(false);
    }
  };

  if (loading) return <p className="text-gray-400 italic">Loading caravan ledger…</p>;

  const active = contracts.filter((c) => c.status === 'active');
  const broken = contracts.filter((c) => c.status === 'broken');

  return (
    <section data-testid="faction-trade-routes-tab">
      <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
        <div>
          <h2 className="text-sm uppercase tracking-[0.3em] text-gray-400">
            Standing Trade Routes ({active.length} active · {broken.length} broken)
          </h2>
          <p className="text-xs text-gray-500 mt-1 italic">
            Standing contracts shipping this faction&apos;s offerings to cities or other factions.
            Each pays the source&apos;s base cost plus a tariff agreed at signing.
          </p>
        </div>
        {canEdit && (
          <Button
            type="button"
            onClick={openForm}
            className="bg-amber-600 hover:bg-amber-700 text-black"
            data-testid="trade-routes-add-btn"
          >
            <Plus className="w-4 h-4 mr-1" />
            Open Route
          </Button>
        )}
      </div>

      {/* Active routes */}
      {active.length === 0 ? (
        <p className="text-gray-500 italic text-sm" data-testid="trade-routes-empty">
          No active routes. {canEdit && 'Open one above to start shipping goods.'}
        </p>
      ) : (
        <div className="grid sm:grid-cols-2 gap-3 mb-5">
          {active.map((c) => (
            <div
              key={c.id}
              className="p-3 rounded-lg glass-dark border border-amber-500/30"
              data-testid={`route-active-${c.id}`}
            >
              <p className="font-semibold text-amber-100 flex items-center gap-2">
                {c.good_slug}
                <ArrowRight className="w-3.5 h-3.5 text-amber-300" />
                {c.to_city_slug || c.to_faction_slug || '?'}
              </p>
              <div className="text-xs text-amber-200/70 mt-1 flex justify-between">
                <span>Tariff {c.tariff_pct}% · Qty/tick {c.quantity_per_tick}</span>
                <span className="text-amber-200/50">{c.base_cost_snapshot}g base</span>
              </div>
              <p className="text-xs text-emerald-300 mt-1 font-semibold" data-testid={`route-delivered-${c.id}`}>
                Delivers at {Math.round((c.base_cost_snapshot || 0) * (1 + (c.tariff_pct || 0) / 100))}g
              </p>
              {canEdit && breakingId !== c.id && (
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  onClick={() => setBreakingId(c.id)}
                  className="mt-2 text-xs text-rose-300 border-rose-500/40 hover:bg-rose-900/30"
                  data-testid={`route-break-btn-${c.id}`}
                >
                  <Trash2 className="w-3 h-3 mr-1" />
                  Break Route
                </Button>
              )}
              {breakingId === c.id && (
                <div className="mt-2 space-y-1">
                  <input
                    type="text"
                    placeholder="Reason (recorded)"
                    value={breakReason}
                    onChange={(e) => setBreakReason(e.target.value)}
                    className="w-full bg-black/50 border border-rose-500/40 rounded p-1 text-xs text-rose-100"
                    data-testid={`route-break-reason-${c.id}`}
                  />
                  <div className="flex gap-1">
                    <Button
                      type="button" size="sm" variant="outline"
                      onClick={() => { setBreakingId(null); setBreakReason(''); }}
                      className="text-xs"
                    >
                      Cancel
                    </Button>
                    <Button
                      type="button" size="sm"
                      onClick={() => breakContract(c.id)}
                      disabled={busy}
                      className="bg-rose-600 hover:bg-rose-700 text-xs"
                      data-testid={`route-break-confirm-${c.id}`}
                    >
                      Confirm
                    </Button>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Broken routes */}
      {broken.length > 0 && (
        <div className="mt-2">
          <h3 className="text-xs uppercase tracking-wider text-rose-300 mb-2 flex items-center gap-1">
            <AlertTriangle className="w-3.5 h-3.5" />
            Broken Routes ({broken.length})
          </h3>
          <div className="space-y-2">
            {broken.slice(0, 5).map((c) => (
              <div key={c.id} className="p-2 rounded bg-rose-900/10 border border-rose-500/20" data-testid={`route-broken-${c.id}`}>
                <p className="text-xs text-rose-100">
                  {c.good_slug} → {c.to_city_slug || c.to_faction_slug || '?'} ·{' '}
                  <span className="text-rose-200/80 italic">{c.break_reason || 'cause unrecorded'}</span>
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Modal — open new route */}
      {showForm && (
        <div className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4">
          <div
            className="glass-dark border border-amber-500/40 rounded-xl p-5 max-w-md w-full"
            data-testid="trade-routes-form-modal"
          >
            <h3 className="text-lg font-semibold text-amber-200 mb-3">Open Standing Trade Route</h3>
            <div className="space-y-3">
              <div>
                <label className="text-xs uppercase tracking-wider text-amber-200/70">Good</label>
                <select
                  value={form.good_slug}
                  onChange={(e) => setForm({ ...form, good_slug: e.target.value })}
                  className="w-full bg-black/50 border border-amber-500/40 rounded p-2 text-sm text-amber-100"
                  data-testid="trade-routes-form-good"
                >
                  {specialties.map((s) => (
                    <option key={s.good_slug} value={s.good_slug}>
                      {s.good_name || s.good_slug} ({s.base_cost}g base)
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-xs uppercase tracking-wider text-amber-200/70">Destination city</label>
                <select
                  value={form.to_city_slug}
                  onChange={(e) => {
                    const city = cities.find((c) => c.slug === e.target.value);
                    setForm({ ...form, to_city_slug: e.target.value, to_nation: city?.nation || '' });
                  }}
                  className="w-full bg-black/50 border border-amber-500/40 rounded p-2 text-sm text-amber-100"
                  data-testid="trade-routes-form-city"
                >
                  <option value="">— pick a city —</option>
                  {cities.map((c) => (
                    <option key={`${c.nation}-${c.slug}`} value={c.slug}>
                      {c.name} ({c.nation})
                    </option>
                  ))}
                </select>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs uppercase tracking-wider text-amber-200/70">Tariff %</label>
                  <input
                    type="number" min="0" max="300"
                    value={form.tariff_pct}
                    onChange={(e) => setForm({ ...form, tariff_pct: e.target.value })}
                    className="w-full bg-black/50 border border-amber-500/40 rounded p-2 text-sm text-amber-100"
                    data-testid="trade-routes-form-tariff"
                  />
                </div>
                <div>
                  <label className="text-xs uppercase tracking-wider text-amber-200/70">Qty / tick</label>
                  <input
                    type="number" min="1"
                    value={form.quantity_per_tick}
                    onChange={(e) => setForm({ ...form, quantity_per_tick: e.target.value })}
                    className="w-full bg-black/50 border border-amber-500/40 rounded p-2 text-sm text-amber-100"
                    data-testid="trade-routes-form-qty"
                  />
                </div>
              </div>
            </div>
            <div className="flex justify-end gap-2 mt-4">
              <Button type="button" variant="outline" onClick={() => setShowForm(false)} disabled={busy}>
                Cancel
              </Button>
              <Button
                type="button" onClick={submit} disabled={busy}
                className="bg-amber-600 hover:bg-amber-700 text-black"
                data-testid="trade-routes-form-save"
              >
                <Coins className="w-4 h-4 mr-1" />
                {busy ? 'Opening…' : 'Sign Contract'}
              </Button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
};

export default FactionTradeRoutesTab;
