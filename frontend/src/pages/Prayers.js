import React, { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { toast } from 'sonner';
import { CalendarDays, ChevronDown, ChevronUp, Flame, Loader2, ScrollText, Sparkles, Sun, TreeDeciduous, Wind, Hourglass, Mountain } from 'lucide-react';
import api from '../utils/api';
import { Button } from '../components/ui/button';
import { Textarea } from '../components/ui/textarea';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '../components/ui/dialog';

const GOD_ICONS = {
  seren:  TreeDeciduous,
  yros:   Mountain,
  uesis:  Wind,
  ehena:  Hourglass,
};

const GOD_PALETTES = {
  seren: {
    accent: 'text-emerald-300',
    bg: 'from-emerald-950/60 via-green-950/40 to-emerald-950/60',
    border: 'border-emerald-700/50',
    button: 'from-emerald-700 to-green-700 hover:from-emerald-800 hover:to-green-800',
  },
  yros: {
    accent: 'text-amber-300',
    bg: 'from-amber-950/60 via-stone-950/50 to-zinc-950/60',
    border: 'border-amber-700/50',
    button: 'from-amber-700 to-stone-700 hover:from-amber-800 hover:to-stone-800',
  },
  uesis: {
    accent: 'text-sky-300',
    bg: 'from-sky-950/60 via-indigo-950/40 to-sky-950/60',
    border: 'border-sky-700/50',
    button: 'from-sky-700 to-indigo-700 hover:from-sky-800 hover:to-indigo-800',
  },
  ehena: {
    accent: 'text-violet-300',
    bg: 'from-violet-950/60 via-purple-950/40 to-violet-950/60',
    border: 'border-violet-700/50',
    button: 'from-violet-700 to-purple-700 hover:from-violet-800 hover:to-purple-800',
  },
};

const VERDICT_STYLES = {
  silence:  { color: 'text-stone-300',    label: 'Silence',   sub: 'No answer comes.' },
  flicker:  { color: 'text-amber-300',    label: 'A Flicker', sub: 'Something stirred — briefly.' },
  blessing: { color: 'text-emerald-300',  label: 'BLESSING',  sub: 'You have been heard, and answered.' },
};

const Prayers = () => {
  const [gods, setGods] = useState([]);
  const [characters, setCharacters] = useState([]);
  const [selectedCharId, setSelectedCharId] = useState('');
  const [selectedGod, setSelectedGod] = useState(null);
  const [prayerText, setPrayerText] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [resultOpen, setResultOpen] = useState(false);
  const [result, setResult] = useState(null);
  const [recent, setRecent] = useState([]);
  const [activeBlessings, setActiveBlessings] = useState([]);
  const [festival, setFestival] = useState(null);        // { active, calendar }
  const [showCalendar, setShowCalendar] = useState(false);
  const [loading, setLoading] = useState(true);

  const refresh = async () => {
    try {
      const [godsRes, charRes, recentRes, festRes] = await Promise.all([
        api.get('/prayers/gods').catch(() => ({ data: { gods: [] } })),
        api.get('/characters').catch(() => ({ data: [] })),
        api.get('/prayers/recent?limit=25').catch(() => ({ data: [] })),
        api.get('/prayers/festivals').catch(() => ({ data: null })),
      ]);
      setGods(godsRes.data?.gods || []);
      const allChars = Array.isArray(charRes.data) ? charRes.data : (charRes.data?.characters || []);
      setCharacters(allChars);
      setRecent(Array.isArray(recentRes.data) ? recentRes.data : []);
      setFestival(festRes.data || null);
      if (!selectedCharId && allChars[0]?.id) {
        setSelectedCharId(allChars[0].id);
      }
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to load the temple.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  useEffect(() => {
    if (!selectedCharId) {
      setActiveBlessings([]);
      return;
    }
    api.get(`/prayers/character/${selectedCharId}/active`)
      .then((r) => setActiveBlessings(r.data?.active_blessings || []))
      .catch(() => setActiveBlessings([]));
  }, [selectedCharId, resultOpen]);

  const selectedChar = useMemo(
    () => characters.find((c) => c.id === selectedCharId),
    [characters, selectedCharId],
  );

  const handleSubmit = async () => {
    if (!selectedCharId || !selectedGod) {
      toast.error('Choose a character and a god first.');
      return;
    }
    if ((prayerText || '').trim().length < 10) {
      toast.error('Your prayer must be at least 10 characters of heartfelt text.');
      return;
    }
    if (submitting) return;
    setSubmitting(true);
    try {
      const r = await api.post('/prayers/submit', {
        character_id: selectedCharId,
        god: selectedGod,
        prayer_text: prayerText.trim(),
      });
      setResult(r.data);
      setResultOpen(true);
      setPrayerText('');
      refresh();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'The prayer could not be offered.');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center text-stone-300">
        <Loader2 className="w-6 h-6 mr-2 animate-spin" />
        Approaching the temple…
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-zinc-950 via-stone-950 to-black text-stone-100">
      <div className="max-w-5xl mx-auto px-6 py-12">
        <div className="mb-10">
          <Link
            to="/dashboard"
            className="text-sm text-stone-400 hover:text-stone-200 transition"
            data-testid="back-to-dashboard-link"
          >
            ← Dashboard
          </Link>
          <h1 className="mt-4 text-4xl sm:text-5xl font-bold tracking-tight flex items-center gap-3">
            <Sparkles className="w-10 h-10 text-amber-300" />
            <span>Prayers to the Elder Gods</span>
          </h1>
          <p className="mt-3 text-stone-400 max-w-3xl">
            The four Elder Gods cannot descend to the mortal realm — but they
            still listen. A prayer that speaks plainly to a god&apos;s domain may
            kindle a fleeting flicker, or, more rarely, a true Blessing that
            colours the next hours of your life. Pray sparingly; the gods grow
            cold when their names are used like coin.
          </p>
        </div>

        {/* ── Elder-Gods Festival Banner ─────────────────────────────── */}
        {festival && festival.active && (() => {
          const active = festival.active;
          const palette = GOD_PALETTES[active.god] || GOD_PALETTES.uesis;
          const Icon = GOD_ICONS[active.god] || Sparkles;
          const isMajor = active.level === 'major';
          return (
            <div
              className={`mb-8 rounded-xl border ${palette.border} bg-gradient-to-br ${palette.bg} p-6 relative overflow-hidden`}
              data-testid="active-festival-banner"
            >
              <div className="absolute -right-8 -top-8 opacity-10 pointer-events-none">
                <Icon className="w-56 h-56" />
              </div>
              <div className="flex items-start gap-4 relative">
                <div className={`shrink-0 rounded-full p-3 border ${palette.border} bg-black/30`}>
                  <Icon className={`w-8 h-8 ${palette.accent}`} />
                </div>
                <div className="flex-1">
                  <div className="flex flex-wrap items-center gap-2 mb-1">
                    <span className={`text-xs uppercase tracking-widest ${palette.accent}`}>
                      {isMajor ? 'Holy Day — Major Festival' : 'Weekly Observance'}
                    </span>
                    <span className="text-xs text-stone-500">·</span>
                    <span className="text-xs text-stone-400">{active.date_iso}</span>
                  </div>
                  <h2
                    className={`text-2xl sm:text-3xl font-semibold ${palette.accent}`}
                    data-testid="active-festival-name"
                  >
                    {active.festival_name}
                  </h2>
                  <p className="mt-2 text-stone-200/90 italic leading-relaxed">
                    {active.atmosphere}
                  </p>
                  <div className="mt-3 inline-flex items-center gap-2 rounded-md border border-amber-500/40 bg-amber-950/40 px-3 py-1 text-amber-200 text-xs">
                    <Sparkles className="w-3.5 h-3.5" />
                    <span data-testid="active-festival-boost">
                      Prayers to {gods.find((g) => g.key === active.god)?.name || active.god} are heard
                      more clearly today (+{active.affinity_boost} favour bias)
                    </span>
                  </div>
                </div>
              </div>
            </div>
          );
        })()}

        {/* Compact calendar peek — shown when nothing is active, or as a toggle when active */}
        {festival && festival.calendar && (
          <div
            className="mb-8 rounded-xl border border-stone-700/60 bg-stone-950/40 overflow-hidden"
            data-testid="festival-calendar-block"
          >
            <button
              type="button"
              onClick={() => setShowCalendar((v) => !v)}
              className="w-full flex items-center justify-between px-5 py-3 text-left hover:bg-stone-900/40 transition"
              data-testid="toggle-festival-calendar-btn"
            >
              <div className="flex items-center gap-2">
                <CalendarDays className="w-4 h-4 text-stone-400" />
                <span className="text-sm text-stone-300">
                  {festival.active
                    ? 'View the full Elder-Gods festival calendar'
                    : 'No Elder-Gods festival today — but here is when they fall'}
                </span>
              </div>
              {showCalendar
                ? <ChevronUp className="w-4 h-4 text-stone-500" />
                : <ChevronDown className="w-4 h-4 text-stone-500" />}
            </button>
            {showCalendar && (
              <div className="grid sm:grid-cols-2 gap-3 p-5 border-t border-stone-800/60">
                {festival.calendar.map((c) => {
                  const palette = GOD_PALETTES[c.god] || GOD_PALETTES.uesis;
                  const Icon = GOD_ICONS[c.god] || Sun;
                  return (
                    <div
                      key={c.god}
                      className={`rounded-lg border ${palette.border} bg-black/20 p-3 text-sm`}
                      data-testid={`festival-cal-${c.god}`}
                    >
                      <div className="flex items-center gap-2 mb-1">
                        <Icon className={`w-4 h-4 ${palette.accent}`} />
                        <strong className={palette.accent}>{c.festival_name}</strong>
                      </div>
                      <div className="text-xs text-stone-400">
                        <div>
                          <span className="text-stone-500">Major days:</span>{' '}
                          <span className="text-stone-300">{c.major_dates_mm_dd.join(', ')}</span>
                        </div>
                        <div>
                          <span className="text-stone-500">Weekly observance:</span>{' '}
                          <span className="text-stone-300">{c.weekly_dow_label}</span>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        <div className="rounded-xl border border-stone-700/60 bg-stone-950/60 p-6 mb-8">
          <label className="block text-sm font-medium text-stone-300 mb-2">
            Praying as
          </label>
          {characters.length === 0 ? (
            <div className="text-stone-400">
              Create a character first to bring a prayer before the gods.
            </div>
          ) : (
            <select
              value={selectedCharId}
              onChange={(e) => setSelectedCharId(e.target.value)}
              className="w-full bg-stone-900 border border-stone-700 rounded-md px-3 py-2 mb-4 text-stone-100"
              data-testid="prayer-character-select"
            >
              {characters.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name} — {c.race}{c.character_class ? ` (${c.character_class})` : ''}
                </option>
              ))}
            </select>
          )}

          {selectedChar && activeBlessings.length > 0 && (
            <div className="mt-3 p-3 bg-emerald-950/30 border border-emerald-700/40 rounded-md">
              <div className="text-xs uppercase text-emerald-300/80 tracking-wider mb-1">
                Active blessings on {selectedChar.name}
              </div>
              <div className="space-y-1" data-testid="active-blessings-list">
                {activeBlessings.map((b) => (
                  <div key={b.god} className="text-sm text-emerald-100/90">
                    <strong className="text-emerald-300">{b.god_name}</strong>
                    {b.verdict === 'flicker' ? ' (flicker)' : ' (blessing)'}
                    {b.boon_text && <> — <span className="italic">{b.boon_text}</span></>}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="grid sm:grid-cols-2 gap-5 mb-10">
          {gods.map((g) => {
            const Icon = GOD_ICONS[g.key] || Sun;
            const palette = GOD_PALETTES[g.key] || GOD_PALETTES.uesis;
            const isSelected = selectedGod === g.key;
            const raceMatch = selectedChar && (g.race_affinity || []).some(
              (aff) => (selectedChar.race || '').toLowerCase().includes(aff),
            );
            return (
              <button
                key={g.key}
                onClick={() => setSelectedGod(g.key)}
                className={`text-left rounded-xl border p-5 transition-all ${palette.border} bg-gradient-to-br ${palette.bg} ${
                  isSelected ? 'ring-2 ring-amber-400/60 scale-[1.02]' : 'hover:scale-[1.01] hover:ring-1 hover:ring-stone-500/40'
                }`}
                data-testid={`god-card-${g.key}`}
              >
                <div className="flex items-center gap-3 mb-2">
                  <Icon className={`w-7 h-7 ${palette.accent}`} />
                  <h3 className={`text-xl font-semibold ${palette.accent}`}>
                    {g.name}
                  </h3>
                  {raceMatch && (
                    <span className="ml-auto text-xs bg-amber-900/40 border border-amber-500/40 text-amber-200 px-2 py-0.5 rounded">
                      race-affinity
                    </span>
                  )}
                </div>
                <p className="text-xs text-stone-400 italic mb-2">{g.title}</p>
                <p className="text-sm text-stone-300">
                  <strong className="text-stone-200">Domain:</strong> {g.domain}
                </p>
              </button>
            );
          })}
        </div>

        {selectedGod && (
          <div className="rounded-xl border border-stone-700/60 bg-stone-950/60 p-6 mb-10">
            <h2 className="text-xl font-semibold mb-1 flex items-center gap-2">
              <Flame className="w-5 h-5 text-amber-300" />
              Your Prayer to {gods.find((g) => g.key === selectedGod)?.name}
            </h2>
            <p className="text-sm text-stone-400 mb-4">
              Speak plainly. The gods value sincerity over flourish, and weigh
              your prayer against your own story. One prayer per god, per
              character, per day.
            </p>
            <Textarea
              value={prayerText}
              onChange={(e) => setPrayerText(e.target.value)}
              placeholder={`Speak the words you would offer to ${gods.find((g) => g.key === selectedGod)?.name}…`}
              maxLength={1500}
              rows={6}
              className="bg-stone-900 border-stone-700 text-stone-100 mb-2"
              data-testid="prayer-text-input"
            />
            <div className="flex items-center justify-between mb-4">
              <div className="text-xs text-stone-500">
                {prayerText.length} / 1500 characters
              </div>
            </div>
            <Button
              onClick={handleSubmit}
              disabled={submitting || !selectedCharId || prayerText.trim().length < 10}
              className={`bg-gradient-to-r ${GOD_PALETTES[selectedGod]?.button || GOD_PALETTES.uesis.button} text-stone-100`}
              data-testid="submit-prayer-btn"
            >
              {submitting ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  The words leave your lips…
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4 mr-2" />
                  Offer this prayer
                </>
              )}
            </Button>
          </div>
        )}

        {recent.length > 0 && (
          <div className="rounded-xl border border-stone-700/60 bg-stone-950/40 p-6">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <ScrollText className="w-5 h-5 text-stone-400" />
              Your Recent Prayers
            </h2>
            <div className="space-y-3" data-testid="recent-prayers-list">
              {recent.slice(0, 12).map((p) => {
                const v = VERDICT_STYLES[p.verdict] || VERDICT_STYLES.silence;
                return (
                  <div
                    key={p.id}
                    className="rounded-md border border-stone-700/50 bg-stone-900/40 p-3"
                    data-testid={`prayer-record-${p.id}`}
                  >
                    <div className="flex items-center justify-between text-sm mb-1">
                      <div>
                        <strong className={v.color}>{v.label}</strong>
                        {' '}— <span className="text-stone-300">{p.god_name}</span>
                        {p.affinity_match && (
                          <span className="ml-2 text-xs text-amber-200/80">(race-affinity)</span>
                        )}
                      </div>
                      <span className="text-stone-500 text-xs">
                        {new Date(p.prayed_at).toLocaleString()}
                      </span>
                    </div>
                    <p className="text-stone-200 text-sm italic">{p.narration}</p>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>

      <Dialog open={resultOpen} onOpenChange={setResultOpen}>
        <DialogContent
          className="bg-stone-950 border-stone-700 text-stone-100 max-w-lg"
          data-testid="prayer-result-modal"
        >
          {result && (() => {
            const v = VERDICT_STYLES[result.verdict] || VERDICT_STYLES.silence;
            const palette = GOD_PALETTES[result.god] || GOD_PALETTES.uesis;
            const Icon = GOD_ICONS[result.god] || Sparkles;
            return (
              <>
                <DialogHeader>
                  <DialogTitle
                    className={`flex items-center gap-2 text-2xl ${v.color}`}
                    data-testid="prayer-result-verdict-label"
                  >
                    <Icon className={`w-7 h-7 ${palette.accent}`} />
                    {v.label}
                  </DialogTitle>
                  <DialogDescription className="text-stone-400">
                    {v.sub}
                  </DialogDescription>
                </DialogHeader>
                <p
                  className="text-stone-100 italic text-lg leading-relaxed mt-4"
                  data-testid="prayer-result-narration"
                >
                  {result.narration}
                </p>
                {result.boon_text && (
                  <div className="mt-4 rounded-md border bg-emerald-900/30 border-emerald-500/40 p-3 text-emerald-200 text-sm">
                    <strong>Boon:</strong> {result.boon_text}
                  </div>
                )}
                <div className="mt-4 flex justify-end">
                  <Button
                    onClick={() => setResultOpen(false)}
                    className="bg-stone-800 hover:bg-stone-700 text-stone-100"
                    data-testid="prayer-result-close-btn"
                  >
                    Withdraw
                  </Button>
                </div>
              </>
            );
          })()}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default Prayers;
