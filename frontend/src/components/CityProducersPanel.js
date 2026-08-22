import React, { useEffect, useState } from 'react';
import { Package, Warehouse, Factory, Loader2 } from 'lucide-react';
import api from '../utils/api';

/**
 * "Produced Here" panel — shows the city's active producers plus current stock.
 * Used on CityDetail and (optionally) on Markets. Fails silently if the
 * economy hasn't been seeded — the panel just doesn't render.
 */
const CityProducersPanel = ({ nation, citySlug, className = '' }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const r = await api.get(`/economy/producers/cities/${nation}/${citySlug}`);
        if (!cancelled) setData(r.data);
      } catch {
        if (!cancelled) setData(null);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [nation, citySlug]);

  if (loading) {
    return (
      <div className={`glass-dark p-4 rounded-xl border border-amber-500/20 flex items-center gap-2 text-stone-400 ${className}`}>
        <Loader2 className="w-4 h-4 animate-spin" />
        <span>Consulting the guild ledgers…</span>
      </div>
    );
  }

  if (!data || !Array.isArray(data.producers) || data.producers.length === 0) {
    return null;
  }

  // Map stock rows by good_slug for quick lookup
  const stockByGood = {};
  (data.stock || []).forEach((s) => { stockByGood[s.good_slug] = s.units; });

  return (
    <div
      className={`glass-dark p-5 rounded-xl border border-amber-500/30 ${className}`}
      data-testid={`city-producers-${nation}-${citySlug}`}
    >
      <div className="flex items-center gap-2 mb-4">
        <Factory className="w-5 h-5 text-amber-300" />
        <h3 className="text-xl font-bold text-amber-200">Produced Here</h3>
      </div>
      <div className="grid sm:grid-cols-2 gap-3">
        {data.producers.map((p) => {
          const stock = stockByGood[p.good_slug] ?? 0;
          const cap = p.warehouse_cap || 1;
          const pct = Math.max(0, Math.min(100, Math.round((stock / cap) * 100)));
          return (
            <div
              key={`${p.city_slug}-${p.good_slug}`}
              className="rounded-lg border border-amber-800/40 bg-black/30 p-3"
              data-testid={`producer-${p.good_slug}`}
            >
              <div className="flex items-center justify-between mb-1">
                <div className="text-stone-100 font-semibold flex items-center gap-1.5">
                  <Package className="w-4 h-4 text-amber-400" />
                  {p.good_slug.replace(/-/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
                </div>
                <div className="text-xs text-amber-200/80">+{p.units_per_tick}/tick</div>
              </div>
              {p.description && (
                <p className="text-xs text-stone-400 italic mb-2 line-clamp-2">{p.description}</p>
              )}
              <div className="flex items-center gap-2 text-xs text-stone-400">
                <Warehouse className="w-3 h-3" />
                <span>Stock: <strong className="text-stone-200">{stock}</strong> / {cap}</span>
              </div>
              <div className="mt-1 h-1.5 rounded-full bg-stone-800 overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-amber-600 to-amber-400 transition-all"
                  style={{ width: `${pct}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default CityProducersPanel;
