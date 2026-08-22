import React, { useEffect, useState } from 'react';
import { Label } from './ui/label';
import { Input } from './ui/input';
import { Coins, Sparkles } from 'lucide-react';
import api from '../utils/api';

/**
 * Auto-pricing section for the shop item form.
 *
 * When `is_auto_priced` is on, the item's price is derived live from the
 * goods market: faction.base_cost → city.import_price → shop.retail_price
 * (= import × (1 + markup_pct/100)).
 */
const AutoPricingSection = ({ formData, setFormData }) => {
  const [goods, setGoods] = useState([]);
  const [cities, setCities] = useState([]);
  const [livePrice, setLivePrice] = useState(null);
  const [livePriceErr, setLivePriceErr] = useState('');

  useEffect(() => {
    (async () => {
      try {
        const [g, c] = await Promise.allSettled([
          api.get('/economy/goods'),
          (async () => {
            const nations = ['aigraels', 'dhor-kuldor', 'selindori', 'ammeonon'];
            const rs = await Promise.allSettled(nations.map((n) => api.get(`/cities/${n}`)));
            const all = [];
            rs.forEach((r, i) => {
              if (r.status === 'fulfilled' && Array.isArray(r.value.data)) {
                r.value.data.forEach((row) => all.push({ ...row, nation: nations[i] }));
              }
            });
            return { data: all };
          })(),
        ]);
        if (g.status === 'fulfilled') setGoods(g.value.data || []);
        if (c.status === 'fulfilled') setCities(c.value.data || []);
      } catch (err) {
        console.error('AutoPricingSection load failed', err);
      }
    })();
  }, []);

  // Recompute the live preview price whenever the sourcing fields change.
  useEffect(() => {
    if (!formData.is_auto_priced || !formData.source_good_slug || !formData.source_city_slug) {
      setLivePrice(null); setLivePriceErr('');
      return;
    }
    const nation = formData.source_nation || cities.find((c) => c.slug === formData.source_city_slug)?.nation;
    if (!nation) return;
    (async () => {
      try {
        const market = await api.get(`/economy/markets/${nation}/${formData.source_city_slug}`);
        const row = (market.data || []).find((p) => p.good_slug === formData.source_good_slug);
        if (!row || !row.is_available || row.import_price == null) {
          setLivePrice(null);
          setLivePriceErr('No active trade contract supplies this good to that city yet.');
          return;
        }
        const retail = Math.round(row.import_price * (1 + (Number(formData.markup_pct) || 0) / 100));
        setLivePrice(retail);
        setLivePriceErr('');
      } catch (_err) {
        setLivePrice(null);
        setLivePriceErr('Market preview failed.');
      }
    })();
  }, [
    formData.is_auto_priced,
    formData.source_good_slug,
    formData.source_city_slug,
    formData.source_nation,
    formData.markup_pct,
    cities,
  ]);

  return (
    <div
      className="rounded-lg border border-amber-500/30 bg-amber-950/10 p-3"
      data-testid="item-form-auto-pricing"
    >
      <label className="flex items-center gap-2 cursor-pointer">
        <input
          type="checkbox"
          checked={Boolean(formData.is_auto_priced)}
          onChange={(e) => setFormData({ ...formData, is_auto_priced: e.target.checked })}
          className="w-4 h-4 accent-amber-500"
          data-testid="item-auto-priced-toggle"
        />
        <Sparkles className="w-4 h-4 text-amber-300" />
        <span className="text-sm text-amber-200 font-semibold">Source from the goods market</span>
      </label>
      <p className="text-xs text-gray-400 mt-1">
        Live-link this item to a faction-produced good. Price moves with production
        cost, city tariffs, and your markup — no manual updates.
      </p>

      {formData.is_auto_priced && (
        <div className="mt-3 space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label className="text-xs text-amber-200/80">Good</Label>
              <select
                value={formData.source_good_slug || ''}
                onChange={(e) => setFormData({ ...formData, source_good_slug: e.target.value })}
                className="w-full bg-black/40 border border-amber-500/40 rounded p-2 text-sm text-amber-100"
                data-testid="item-source-good"
              >
                <option value="">— select —</option>
                {goods.map((g) => (
                  <option key={g.slug} value={g.slug}>{g.name}</option>
                ))}
              </select>
            </div>
            <div>
              <Label className="text-xs text-amber-200/80">City</Label>
              <select
                value={formData.source_city_slug || ''}
                onChange={(e) => {
                  const city = cities.find((c) => c.slug === e.target.value);
                  setFormData({
                    ...formData,
                    source_city_slug: e.target.value,
                    source_nation: city?.nation || formData.source_nation,
                  });
                }}
                className="w-full bg-black/40 border border-amber-500/40 rounded p-2 text-sm text-amber-100"
                data-testid="item-source-city"
              >
                <option value="">— select —</option>
                {cities.map((c) => (
                  <option key={`${c.nation}-${c.slug}`} value={c.slug}>
                    {c.name} ({c.nation})
                  </option>
                ))}
              </select>
            </div>
          </div>
          <div>
            <Label className="text-xs text-amber-200/80">Your markup %</Label>
            <Input
              type="number"
              min="0"
              max="500"
              value={formData.markup_pct ?? 30}
              onChange={(e) => setFormData({ ...formData, markup_pct: e.target.value })}
              className="bg-black/40 border-amber-500/40"
              data-testid="item-markup-pct"
            />
          </div>

          <div
            className="flex items-center justify-between text-sm p-2 rounded bg-black/30 border border-amber-500/20"
            data-testid="item-live-price-preview"
          >
            <span className="text-amber-200/70 flex items-center gap-1">
              <Coins className="w-3.5 h-3.5" />
              Live retail price
            </span>
            {livePrice != null ? (
              <span className="text-amber-200 font-bold">{livePrice}g</span>
            ) : (
              <span className="text-rose-300 text-xs italic">{livePriceErr || 'Pick good + city.'}</span>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default AutoPricingSection;
