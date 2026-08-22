import React, { useEffect, useState, useCallback } from 'react';
import { Link } from 'react-router-dom';
import api from '../utils/api';
import AnimatedBackground from '../components/AnimatedBackground';
import Navbar from '../components/Navbar';
import {
  TrendingUp, TrendingDown, AlertTriangle, ArrowRight, Coins,
  Hammer, ShieldOff, Sparkles, Wheat, Wine,
} from 'lucide-react';
import CaravansBoard from '../components/CaravansBoard';

/**
 * Markets page — read-only economy view.
 *
 * Surfaces:
 *  - Top movers (7-day): largest absolute price deltas across all factions.
 *  - Broken routes: trade contracts that have been cancelled (war/embargo).
 *  - Goods catalogue: every good, with the cheapest current supplier.
 */

const CATEGORY_ICONS = {
  metal: Hammer,
  weapon: ShieldOff,
  armor: ShieldOff,
  food: Wheat,
  textile: Coins,
  luxury: Sparkles,
  reagent: Sparkles,
  service: Coins,
  stone: Hammer,
  default: Coins,
};

const CategoryIcon = ({ category, className }) => {
  const Icon = CATEGORY_ICONS[category] || CATEGORY_ICONS.default;
  return <Icon className={className} />;
};

const formatGold = (n) =>
  n == null ? '—' : `${Number(n).toLocaleString()}g`;

const formatDelta = (d) => {
  if (!d) return '0';
  const sign = d > 0 ? '+' : '';
  return `${sign}${Number(d).toLocaleString()}g`;
};

const Markets = () => {
  const [goods, setGoods] = useState([]);
  const [movers, setMovers] = useState([]);
  const [broken, setBroken] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filterCategory, setFilterCategory] = useState('');

  const fetchAll = useCallback(async () => {
    setLoading(true);
    try {
      const [goodsRes, moversRes, brokenRes] = await Promise.allSettled([
        api.get('/economy/goods'),
        api.get('/economy/top-movers?limit=8&hours=168'),
        api.get('/economy/broken-routes?limit=20'),
      ]);
      if (goodsRes.status === 'fulfilled') setGoods(goodsRes.value.data || []);
      if (moversRes.status === 'fulfilled') setMovers(moversRes.value.data || []);
      if (brokenRes.status === 'fulfilled') setBroken(brokenRes.value.data || []);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  const categories = Array.from(new Set(goods.map((g) => g.category))).sort();
  const visibleGoods = filterCategory ? goods.filter((g) => g.category === filterCategory) : goods;

  return (
    <div className="min-h-screen bg-black text-amber-50 relative">
      <AnimatedBackground />
      <div className="relative z-10">
        <Navbar />
        <div className="container mx-auto px-4 py-8 max-w-7xl">
          <div className="mb-8 flex items-end justify-between flex-wrap gap-3" data-testid="markets-header">
            <div>
              <h1 className="text-4xl sm:text-5xl font-bold text-amber-200 tracking-tight">
                Markets of Delarom
              </h1>
              <p className="text-amber-200/70 text-sm mt-2">
                Goods, trade routes, and the rumours that move them.
                Prices propagate from faction production costs through city tariffs
                to the merchants and crafters who serve the realms.
              </p>
            </div>
            <div className="flex items-center gap-2">
              <label className="text-xs uppercase tracking-wider text-amber-200/70">Category</label>
              <select
                value={filterCategory}
                onChange={(e) => setFilterCategory(e.target.value)}
                className="bg-black/50 border border-amber-500/40 rounded px-3 py-1 text-sm text-amber-100"
                data-testid="markets-category-filter"
              >
                <option value="">All</option>
                {categories.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>
          </div>

          {loading && (
            <p className="text-amber-200/70 italic">Loading the realm's ledgers…</p>
          )}

          {!loading && (
            <div className="grid lg:grid-cols-3 gap-6 mb-10">
              {/* TOP MOVERS */}
              <div
                className="glass-dark p-5 rounded-xl border border-amber-500/30 lg:col-span-2"
                data-testid="markets-top-movers"
              >
                <div className="flex items-center gap-2 mb-3">
                  <TrendingUp className="w-5 h-5 text-amber-300" />
                  <h2 className="text-lg font-semibold text-amber-200">Top Movers · 7 Days</h2>
                </div>
                {movers.length === 0 ? (
                  <p className="text-sm text-amber-100/60 italic">
                    The markets have been quiet — no significant price moves this week.
                  </p>
                ) : (
                  <div className="space-y-2">
                    {movers.map((m, i) => {
                      const up = (m.delta || 0) > 0;
                      const Tone = up ? TrendingUp : TrendingDown;
                      const color = up ? 'text-rose-300' : 'text-emerald-300';
                      return (
                        <div
                          key={`${m.good_slug}-${i}`}
                          className="flex items-start gap-3 p-3 rounded-lg bg-black/30 border border-amber-500/15"
                          data-testid={`mover-${i}`}
                        >
                          <Tone className={`w-4 h-4 mt-1 ${color}`} />
                          <div className="flex-1 min-w-0">
                            <p className="text-amber-100 font-semibold">
                              {m.good_slug}{' '}
                              <span className="text-amber-300/60 font-normal text-xs">
                                · {m.faction_slug}
                              </span>
                            </p>
                            <p className="text-xs text-amber-200/70 italic mt-0.5 line-clamp-2">
                              {m.reason || 'No recorded cause.'}
                            </p>
                          </div>
                          <div className="text-right whitespace-nowrap">
                            <p className={`text-sm font-bold ${color}`}>{formatDelta(m.delta)}</p>
                            <p className="text-[10px] text-amber-200/50">
                              {formatGold(m.from)} → {formatGold(m.to)}
                            </p>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>

              {/* BROKEN ROUTES */}
              <div
                className="glass-dark p-5 rounded-xl border border-rose-500/30"
                data-testid="markets-broken-routes"
              >
                <div className="flex items-center gap-2 mb-3">
                  <AlertTriangle className="w-5 h-5 text-rose-300" />
                  <h2 className="text-lg font-semibold text-rose-200">Broken Routes</h2>
                </div>
                {broken.length === 0 ? (
                  <p className="text-sm text-amber-100/60 italic">
                    All standing contracts are flowing. Trade remains peaceful.
                  </p>
                ) : (
                  <div className="space-y-2 max-h-96 overflow-y-auto pr-1">
                    {broken.map((b, i) => (
                      <div
                        key={b.id || i}
                        className="p-3 rounded-lg bg-rose-900/10 border border-rose-500/20"
                        data-testid={`broken-route-${i}`}
                      >
                        <p className="text-sm text-rose-100">
                          <span className="font-semibold">{b.from_faction_slug}</span>
                          <ArrowRight className="inline w-3 h-3 mx-1 text-rose-300" />
                          <span className="font-semibold">{b.to_city_slug || b.to_faction_slug || '?'}</span>
                        </p>
                        <p className="text-xs text-rose-200/80 mt-1">
                          {b.good_slug} · {b.break_reason || 'Cause unrecorded.'}
                        </p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* CARAVANS — public bulletin */}
          {!loading && (
            <div
              className="glass-dark p-5 rounded-xl border border-amber-500/30 mb-6"
              data-testid="markets-caravans"
            >
              <CaravansBoard />
            </div>
          )}

          {/* GOODS CATALOGUE */}
          {!loading && (
            <div
              className="glass-dark p-5 rounded-xl border border-amber-500/30"
              data-testid="markets-goods-list"
            >
              <h2 className="text-lg font-semibold text-amber-200 mb-3">Goods Catalogue</h2>
              <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {visibleGoods.map((g) => (
                  <Link
                    key={g.slug}
                    to={`/markets/${g.slug}`}
                    className="p-3 rounded-lg bg-black/30 border border-amber-500/20 hover:border-amber-500/60 hover:bg-black/40 transition-colors"
                    data-testid={`good-card-${g.slug}`}
                  >
                    <div className="flex items-start gap-3">
                      <CategoryIcon category={g.category} className="w-4 h-4 mt-1 text-amber-300/70" />
                      <div className="flex-1">
                        <p className="font-semibold text-amber-100">{g.name}</p>
                        <p className="text-[11px] uppercase tracking-wider text-amber-200/60">
                          {g.category} · {g.unit}
                        </p>
                        <p className="text-xs text-amber-200/70 mt-1">
                          Base from <span className="text-amber-200">{formatGold(g.default_base_cost)}</span>
                        </p>
                      </div>
                    </div>
                  </Link>
                ))}
              </div>
            </div>
          )}

          {!loading && (
            <div className="mt-6">
              <Wine className="w-4 h-4 text-amber-300/60 inline" />
              <span className="text-xs text-amber-200/60 ml-2 italic">
                Prices update whenever a faction's production cost shifts, a contract is broken,
                or a Chronicle event (war, festival, disaster) ripples through the realms.
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Markets;
