import React, { useEffect, useState } from 'react';
import { Shield, Landmark, Sparkles, Loader2 } from 'lucide-react';
import api from '../utils/api';

const BAND_TONE = {
  Legend:    'bg-amber-950/40 border-amber-400/60 text-amber-100',
  Respected: 'bg-emerald-950/40 border-emerald-500/40 text-emerald-100',
  Known:     'bg-sky-950/40 border-sky-500/40 text-sky-100',
  Nobody:    'bg-stone-900/40 border-stone-700 text-stone-300',
  Disliked:  'bg-orange-950/40 border-orange-500/40 text-orange-100',
  Reviled:   'bg-rose-950/40 border-rose-500/40 text-rose-100',
  Hunted:    'bg-red-950/60 border-red-500/60 text-red-100',
};

const AXIS_META = {
  city:    { label: 'City Renown',      Icon: Landmark },
  faction: { label: 'Faction Standing', Icon: Shield },
  god:     { label: 'Elder-God Favour', Icon: Sparkles },
};

/**
 * Compact per-axis reputation panel — city, faction, god. Silent if the
 * character has no reputation yet (the world hasn't noticed them).
 */
const CharacterReputationPanel = ({ characterId, className = '' }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const r = await api.get(`/reputation/characters/${characterId}`);
        if (!cancelled) setData(r.data);
      } catch {
        if (!cancelled) setData(null);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [characterId]);

  if (loading) {
    return (
      <div className={`glass-dark p-4 rounded-xl border border-purple-500/20 flex items-center gap-2 text-stone-400 ${className}`}>
        <Loader2 className="w-4 h-4 animate-spin" />
        <span>Consulting the world&apos;s memory…</span>
      </div>
    );
  }

  const axes = ['city', 'faction', 'god'];
  const anyRep = data && axes.some((a) => (data[a] || []).length > 0);
  if (!anyRep) return null;

  return (
    <div className={`glass-dark p-5 rounded-xl border border-purple-500/30 ${className}`} data-testid={`rep-panel-${characterId}`}>
      <div className="flex items-center gap-2 mb-4">
        <Shield className="w-5 h-5 text-purple-300" />
        <h3 className="text-xl font-bold text-purple-200">Renown & Reputation</h3>
      </div>
      <div className="grid md:grid-cols-3 gap-4">
        {axes.map((axis) => {
          const rows = data?.[axis] || [];
          const meta = AXIS_META[axis];
          const Icon = meta.Icon;
          return (
            <div key={axis} className="rounded-lg border border-stone-700/60 bg-black/30 p-3" data-testid={`rep-axis-${axis}`}>
              <div className="flex items-center gap-2 text-stone-300 text-sm mb-2">
                <Icon className="w-4 h-4 text-purple-300" />
                <span>{meta.label}</span>
              </div>
              {rows.length === 0 ? (
                <div className="text-xs text-stone-500 italic">
                  You are Nobody — yet.
                </div>
              ) : (
                <div className="space-y-1.5">
                  {rows.slice(0, 5).map((r) => {
                    const tone = BAND_TONE[r.label] || BAND_TONE.Nobody;
                    return (
                      <div
                        key={`${axis}-${r.key}`}
                        className={`flex items-center justify-between rounded-md border px-2 py-1.5 text-xs ${tone}`}
                        data-testid={`rep-row-${axis}-${r.key}`}
                      >
                        <span className="truncate mr-2">{r.key.replace(/-/g, ' ')}</span>
                        <span className="font-semibold whitespace-nowrap">
                          {r.label} ({r.score >= 0 ? '+' : ''}{r.score})
                        </span>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default CharacterReputationPanel;
