import React, { useEffect, useState, useCallback } from 'react';
import { Link, useParams } from 'react-router-dom';
import api from '../utils/api';
import AnimatedBackground from '../components/AnimatedBackground';
import Navbar from '../components/Navbar';
import {
  ArrowLeft, Hammer, ShoppingBag, Coins, MapPin, Factory,
  TrendingUp, TrendingDown,
} from 'lucide-react';

/**
 * Good detail page — surfaces:
 *  - The good's catalogue metadata.
 *  - Every faction that produces it, ranked cheapest first.
 *  - Every city currently importing it via an active contract, with the
 *    real-time import_price each city is paying.
 *
 * Helps both players (where do I buy this?) and shop owners (who should I
 * source from?) make informed decisions.
 */
const GoodDetail = () => {
  const { goodSlug } = useParams();
  const [good, setGood] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchGood = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get(`/economy/goods/${goodSlug}`);
      setGood(res.data);
    } catch (err) {
      console.error('GoodDetail load failed', err);
      setGood(null);
    } finally {
      setLoading(false);
    }
  }, [goodSlug]);

  useEffect(() => { fetchGood(); }, [fetchGood]);

  return (
    <div className="min-h-screen bg-black text-amber-50 relative">
      <AnimatedBackground />
      <div className="relative z-10">
        <Navbar />
        <div className="container mx-auto px-4 py-8 max-w-5xl">
          <Link
            to="/markets"
            className="inline-flex items-center gap-2 text-amber-300/80 hover:text-amber-200 text-sm mb-4"
            data-testid="good-detail-back"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Markets
          </Link>

          {loading && <p className="text-amber-200/70 italic">Loading the ledger…</p>}

          {!loading && !good && (
            <div
              className="glass-dark p-6 rounded-xl border border-rose-500/30"
              data-testid="good-detail-not-found"
            >
              <p className="text-rose-200">No record of this good in the realm's catalogue.</p>
            </div>
          )}

          {!loading && good && (
            <>
              {/* Header */}
              <div
                className="glass-dark p-6 rounded-xl border border-amber-500/40 mb-6"
                data-testid="good-detail-header"
              >
                <div className="flex items-start gap-3">
                  <Hammer className="w-7 h-7 text-amber-300 flex-shrink-0 mt-1" />
                  <div className="flex-1">
                    <h1 className="text-3xl sm:text-4xl font-bold text-amber-200 tracking-tight">
                      {good.name}
                    </h1>
                    <p className="text-xs uppercase tracking-[0.3em] text-amber-200/60 mt-1">
                      {good.category} · {good.unit}
                    </p>
                    {good.description && (
                      <p className="text-amber-100/80 italic mt-2 max-w-3xl">{good.description}</p>
                    )}
                    <p className="text-sm text-amber-200/70 mt-3">
                      Catalogue base from{' '}
                      <span className="text-amber-200 font-semibold">{good.default_base_cost}g</span>
                      {good.tags && good.tags.length > 0 && (
                        <span className="ml-3">
                          {good.tags.map((t) => (
                            <span
                              key={t}
                              className="text-[10px] uppercase tracking-wider px-2 py-0.5 mr-1 rounded-full bg-amber-900/30 border border-amber-500/30 text-amber-100"
                            >
                              {t}
                            </span>
                          ))}
                        </span>
                      )}
                    </p>
                  </div>
                </div>
              </div>

              <div className="grid lg:grid-cols-2 gap-6">
                {/* PRODUCERS */}
                <div
                  className="glass-dark p-5 rounded-xl border border-amber-500/30"
                  data-testid="good-detail-producers"
                >
                  <div className="flex items-center gap-2 mb-3">
                    <Factory className="w-5 h-5 text-amber-300" />
                    <h2 className="text-lg font-semibold text-amber-200">
                      Producers ({(good.suppliers || []).length})
                    </h2>
                  </div>
                  {(good.suppliers || []).length === 0 ? (
                    <p className="text-amber-100/60 italic text-sm">
                      No faction currently produces this. It can still be referenced in trade,
                      but no live supply exists.
                    </p>
                  ) : (
                    <div className="space-y-2">
                      {good.suppliers.map((s, i) => {
                        const lastDelta = (s.cost_history || []).slice(-1)[0];
                        const moved = lastDelta && lastDelta.delta;
                        const Tone = moved && moved > 0 ? TrendingUp : moved && moved < 0 ? TrendingDown : null;
                        const toneColor = moved && moved > 0 ? 'text-rose-300' : moved && moved < 0 ? 'text-emerald-300' : 'text-amber-200/60';
                        return (
                          <div
                            key={s.id || s.faction_slug}
                            className="p-3 rounded-lg bg-black/30 border border-amber-500/20 flex items-start gap-3"
                            data-testid={`producer-${s.faction_slug}`}
                          >
                            <div className="text-xs uppercase tracking-wider text-amber-200/40 mt-1 w-5 text-right">
                              #{i + 1}
                            </div>
                            <div className="flex-1 min-w-0">
                              <Link
                                to={`/factions/${s.faction_slug}`}
                                className="font-semibold text-amber-100 hover:text-amber-200"
                              >
                                {s.faction_name || s.faction_slug}
                              </Link>
                              <p className="text-[10px] uppercase tracking-wider text-amber-200/60">
                                {s.faction_nation || 'unknown nation'} · cap {s.capacity}
                              </p>
                              {s.description && (
                                <p className="text-xs italic text-amber-200/70 mt-1 line-clamp-2">
                                  {s.description}
                                </p>
                              )}
                              {Tone && (
                                <p className={`text-[11px] mt-1 flex items-center gap-1 ${toneColor}`}>
                                  <Tone className="w-3 h-3" />
                                  {moved > 0 ? '+' : ''}{moved}g · {(lastDelta.reason || 'recent shift').slice(0, 80)}
                                </p>
                              )}
                            </div>
                            <div className="text-right whitespace-nowrap">
                              <p className="text-lg font-bold text-amber-200">{s.base_cost}g</p>
                              <p className="text-[10px] text-amber-200/50">/ unit</p>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>

                {/* CITY MARKETS */}
                <div
                  className="glass-dark p-5 rounded-xl border border-blue-500/30"
                  data-testid="good-detail-markets"
                >
                  <div className="flex items-center gap-2 mb-3">
                    <ShoppingBag className="w-5 h-5 text-blue-300" />
                    <h2 className="text-lg font-semibold text-blue-200">
                      City Markets ({(good.markets || []).length})
                    </h2>
                  </div>
                  {(good.markets || []).length === 0 ? (
                    <p className="text-blue-100/60 italic text-sm">
                      No city has an active contract importing this right now. Standing routes
                      may have been broken by diplomacy, or none have been opened yet.
                    </p>
                  ) : (
                    <div className="space-y-2">
                      {good.markets.map((m, i) => (
                        <div
                          key={`${m.nation}-${m.city_slug}`}
                          className="p-3 rounded-lg bg-black/30 border border-blue-500/20 flex items-start gap-3"
                          data-testid={`market-${m.city_slug}`}
                        >
                          <MapPin className="w-4 h-4 mt-1 text-blue-300" />
                          <div className="flex-1 min-w-0">
                            <p className="font-semibold text-blue-100">
                              {m.city_name}
                            </p>
                            <p className="text-[10px] uppercase tracking-wider text-blue-200/60">
                              {m.nation}
                            </p>
                            {m.source_faction_slug && (
                              <p className="text-xs text-blue-200/70 mt-1">
                                Sourced from{' '}
                                <Link
                                  to={`/factions/${m.source_faction_slug}`}
                                  className="text-blue-200 hover:text-blue-100 underline-offset-2 hover:underline"
                                >
                                  {m.source_faction_slug}
                                </Link>
                              </p>
                            )}
                          </div>
                          <div className="text-right">
                            <p className="text-lg font-bold text-blue-200 flex items-center gap-1">
                              <Coins className="w-3.5 h-3.5" />
                              {m.import_price}g
                            </p>
                            <p className="text-[10px] text-blue-200/50">
                              {i === 0 ? 'cheapest' : `+${m.import_price - good.markets[0].import_price}g`}
                            </p>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                  <p className="text-[11px] text-blue-200/50 italic mt-3">
                    Import price = source faction's base cost × (1 + tariff %). A shop's retail
                    price is then this × (1 + the shop's own markup %).
                  </p>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default GoodDetail;
