import React, { useEffect, useState } from 'react';
import { ScrollText, Crown, Swords, Sparkles, Flame, Bell } from 'lucide-react';
import api from '../utils/api';

// Maps an event_type → { icon, accent (tailwind text), tone (tailwind border/bg) }
const TYPE_STYLE = {
  royal_insult:        { icon: Crown,     accent: 'text-red-300',     tone: 'border-red-500/30 bg-red-900/10',     headline: 'A royal slight' },
  royal_favour:        { icon: Crown,     accent: 'text-emerald-300', tone: 'border-emerald-500/30 bg-emerald-900/10', headline: 'A royal favour' },
  'stance_change:war':       { icon: Swords, accent: 'text-red-300',    tone: 'border-red-600/40 bg-red-950/20',    headline: 'War declared' },
  'stance_change:cold_war':  { icon: Swords, accent: 'text-orange-300', tone: 'border-orange-500/30 bg-orange-900/10', headline: 'Cold war looms' },
  'stance_change:tense':     { icon: Swords, accent: 'text-amber-300',  tone: 'border-amber-500/30 bg-amber-900/10', headline: 'Tensions rising' },
  'stance_change:neutral':   { icon: Sparkles, accent: 'text-gray-300', tone: 'border-gray-500/30 bg-gray-900/30',  headline: 'A fragile calm' },
  'stance_change:friendly':  { icon: Sparkles, accent: 'text-emerald-300', tone: 'border-emerald-500/30 bg-emerald-900/10', headline: 'New goodwill' },
  'stance_change:alliance':  { icon: Sparkles, accent: 'text-blue-300', tone: 'border-blue-500/30 bg-blue-900/10', headline: 'An alliance forged' },
};

const DEFAULT_STYLE = { icon: Bell, accent: 'text-purple-300', tone: 'border-purple-500/20 bg-purple-900/10', headline: 'Word from the realms' };

const formatStanceType = (type) => {
  if (!type.startsWith('stance_change:')) return type.replace(/_/g, ' ');
  return `Stance: ${type.split(':')[1].replace('_', ' ')}`;
};

const ChroniclePanel = () => {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchChronicle = async () => {
      try {
        const res = await api.get('/chronicle?limit=80');
        setEvents(res.data || []);
      } catch (err) {
        // Non-critical — log for debugging, page still renders empty state
        console.error('Failed to load chronicle:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchChronicle();
    const interval = setInterval(fetchChronicle, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="max-w-4xl mx-auto px-4 py-6" data-testid="chronicle-page">
      <header className="mb-8">
        <div className="flex items-center gap-3">
          <ScrollText className="w-7 h-7 text-amber-300" />
          <h2 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
            The Chronicle
          </h2>
        </div>
        <p className="text-gray-400 mt-2 max-w-2xl text-sm">
          Whispers from every corner of Delarom. Royal insults, broken alliances, festivals, and the
          slow drumbeat of war — every act between mortal and monarch leaves a mark here.
        </p>
      </header>

        {loading && <p className="text-gray-400">Gathering the rumours…</p>}

        {!loading && events.length === 0 && (
          <div className="glass-dark p-8 rounded-2xl border border-purple-500/20 text-center">
            <Sparkles className="w-10 h-10 text-purple-300 mx-auto mb-3" />
            <p className="text-gray-300">The realms are quiet. Nothing of consequence has happened… yet.</p>
            <p className="text-gray-500 text-sm mt-2">Stir something up.</p>
          </div>
        )}

        <ol className="relative border-l border-amber-500/20 ml-2 space-y-6">
          {events.map((ev) => {
            const style = TYPE_STYLE[ev.event_type] || DEFAULT_STYLE;
            const Icon = style.icon;
            return (
              <li key={ev.id} className="ml-6" data-testid={`chronicle-event-${ev.id}`}>
                <span className={`absolute -left-[13px] flex items-center justify-center w-6 h-6 rounded-full bg-gray-900 border border-amber-500/40 ${style.accent}`}>
                  <Icon className="w-3.5 h-3.5" />
                </span>
                <div className={`p-5 rounded-xl border ${style.tone} backdrop-blur-sm`}>
                  <div className="flex items-center justify-between gap-3 flex-wrap mb-2">
                    <div className="flex items-center gap-2">
                      <span className={`text-xs uppercase tracking-widest font-semibold ${style.accent}`}>
                        {style.headline}
                      </span>
                      <span className="text-xs text-gray-500 lowercase">
                        · {formatStanceType(ev.event_type)}
                      </span>
                    </div>
                    <time className="text-xs text-gray-500">
                      {ev.created_at ? new Date(ev.created_at).toLocaleString() : ''}
                    </time>
                  </div>
                  <p className="text-white text-lg font-semibold leading-snug">{ev.summary}</p>
                  {ev.details && (
                    <p className="text-gray-300 text-sm mt-2 leading-relaxed">{ev.details}</p>
                  )}
                  {ev.nations?.length > 0 && (
                    <div className="mt-3 flex flex-wrap gap-2">
                      {ev.nations.map((n) => (
                        <span
                          key={n}
                          className="text-xs px-2 py-0.5 rounded-full bg-black/40 text-amber-200 border border-amber-500/30 capitalize"
                        >
                          {n}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </li>
            );
          })}
        </ol>

        {!loading && events.length > 0 && (
          <p className="text-center text-xs text-gray-600 mt-10 italic">
            <Flame className="w-3 h-3 inline mr-1" />
            The Chronicle updates every thirty seconds. New whispers find their way here.
          </p>
        )}
    </div>
  );
};

export default ChroniclePanel;
