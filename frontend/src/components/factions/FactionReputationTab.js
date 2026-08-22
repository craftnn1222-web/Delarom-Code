import React, { useEffect, useState, useCallback } from 'react';
import api from '../../utils/api';
import { TrendingUp, TrendingDown } from 'lucide-react';

const NATION_LABELS = {
  ammeonon:        'Ammeonon',
  selindori:       'Selindori',
  'dhor-kuldor':  'Dhor Kuldor',
  aigraels:        'Aigraels',
  'veiled-realms': 'The Veiled Realms',
};

const REPUTATION_MIN = -1000;
const REPUTATION_MAX = 1000;

const standingLabel = (score) => {
  if (score >= 750)  return { text: 'Revered',   tone: 'text-amber-300' };
  if (score >= 250)  return { text: 'Honored',   tone: 'text-green-300' };
  if (score >= 50)   return { text: 'Friendly',  tone: 'text-emerald-300' };
  if (score > -50)   return { text: 'Neutral',   tone: 'text-gray-300' };
  if (score > -250)  return { text: 'Wary',      tone: 'text-yellow-400' };
  if (score > -750)  return { text: 'Hostile',   tone: 'text-orange-400' };
  return                  { text: 'Reviled',  tone: 'text-red-400' };
};

const ReputationBar = ({ score }) => {
  // Map -1000..+1000 to a bar where 50% is neutral.
  const pct = ((score - REPUTATION_MIN) / (REPUTATION_MAX - REPUTATION_MIN)) * 100;
  const isPos = score >= 0;
  return (
    <div className="relative w-full h-2 bg-gray-800 rounded-full overflow-hidden">
      {/* center line */}
      <div className="absolute left-1/2 top-0 bottom-0 w-px bg-gray-600" />
      <div
        className={`absolute top-0 bottom-0 ${isPos ? 'bg-green-500' : 'bg-red-500'} transition-all`}
        style={
          isPos
            ? { left: '50%', width: `${Math.max(0, pct - 50)}%` }
            : { right: `${100 - 50}%`, width: `${50 - pct}%` }
        }
      />
    </div>
  );
};

const FactionReputationTab = ({ slug }) => {
  const [rows, setRows] = useState([]);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [r, h] = await Promise.allSettled([
        api.get(`/factions/${slug}/reputation`),
        api.get(`/factions/${slug}/reputation/history`),
      ]);
      if (r.status === 'fulfilled') setRows(r.value.data);
      if (h.status === 'fulfilled') setHistory(h.value.data);
    } finally { setLoading(false); }
  }, [slug]);

  useEffect(() => { load(); }, [load]);

  if (loading) return <p className="text-gray-500 italic text-center py-6">Reading the rolls…</p>;

  return (
    <div data-testid="faction-reputation-tab">
      <p className="text-xs text-gray-400 italic mb-4">
        Each nation tracks the faction's standing separately. Members' deeds shift these scales over time.
      </p>

      <div className="space-y-3" data-testid="reputation-rows">
        {rows.map((r) => {
          const label = standingLabel(r.score);
          return (
            <div key={r.nation} className="glass-dark border border-gray-700/40 rounded-lg p-4" data-testid={`rep-row-${r.nation}`}>
              <div className="flex items-center justify-between mb-2">
                <div>
                  <p className="text-sm font-semibold text-gray-100">{NATION_LABELS[r.nation] || r.nation}</p>
                  <p className={`text-xs uppercase tracking-wide ${label.tone}`}>{label.text}</p>
                </div>
                <div className="text-right">
                  <p className={`text-lg font-bold ${label.tone}`} data-testid={`rep-score-${r.nation}`}>
                    {r.score > 0 ? `+${r.score}` : r.score}
                  </p>
                </div>
              </div>
              <ReputationBar score={r.score} />
            </div>
          );
        })}
      </div>

      {history.length > 0 && (
        <section className="mt-8" data-testid="reputation-history-section">
          <h3 className="text-sm uppercase tracking-[0.3em] text-gray-400 mb-3">Recent Shifts</h3>
          <ul className="space-y-1 text-sm">
            {history.slice(0, 12).map((h) => (
              <li key={h.id} className="flex items-center justify-between gap-3 py-1.5 border-b border-gray-800/40">
                <div className="flex items-center gap-3 min-w-0 flex-1">
                  <span className={`flex-shrink-0 ${h.delta >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {h.delta >= 0 ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
                  </span>
                  <span className="text-gray-400 text-xs uppercase tracking-wider w-32 truncate">{NATION_LABELS[h.nation] || h.nation}</span>
                  <span className="text-gray-300 text-xs truncate flex-1">{h.reason || '—'}</span>
                </div>
                <span className={`text-xs font-mono ${h.delta >= 0 ? 'text-green-300' : 'text-red-300'}`}>
                  {h.delta > 0 ? `+${h.delta}` : h.delta}
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
};

export default FactionReputationTab;
