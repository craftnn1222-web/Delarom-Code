import React, { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { toast } from 'sonner';
import {
  Flag, Loader2, Swords, Shield, MapPin, Users, Timer, Trophy,
  Sword, ScrollText,
} from 'lucide-react';
import api from '../utils/api';
import { Button } from '../components/ui/button';
import { Textarea } from '../components/ui/textarea';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
  DialogDescription,
} from '../components/ui/dialog';

const NATIONS = [
  { slug: '', label: 'All Realms' },
  { slug: 'ammeonon',      label: 'Ammeonon' },
  { slug: 'dhor-kuldor',   label: 'Dhor-Kuldor' },
  { slug: 'selindori',     label: 'Selindori' },
  { slug: 'aigraels',      label: 'Aigraels' },
  { slug: 'veiled-realms', label: 'Veiled Realms' },
];

const fmtCountdown = (iso) => {
  if (!iso) return '—';
  const ms = new Date(iso).getTime() - Date.now();
  if (ms <= 0) return 'expired';
  const h = Math.floor(ms / 3_600_000);
  const m = Math.floor((ms % 3_600_000) / 60_000);
  if (h >= 24) return `${Math.floor(h / 24)}d ${h % 24}h`;
  return `${h}h ${m}m`;
};

const ContestedCities = () => {
  const [sieges, setSieges] = useState([]);
  const [chars, setChars] = useState([]);
  const [nationFilter, setNationFilter] = useState('');
  const [loading, setLoading] = useState(true);

  // Contribute modal state
  const [contributeTarget, setContributeTarget] = useState(null);
  const [contributeForm, setContributeForm] = useState({
    character_id: '', side: 'attacker', action_text: '',
  });
  const [submitting, setSubmitting] = useState(false);

  // Answer modal state
  const [answerTarget, setAnswerTarget] = useState(null);
  const [answerForm, setAnswerForm] = useState({
    character_id: '', defender_faction_slug: '',
  });

  const refresh = async () => {
    try {
      const [sRes, chRes] = await Promise.all([
        api.get('/sieges').catch(() => ({ data: [] })),
        api.get('/characters').catch(() => ({ data: [] })),
      ]);
      const list = Array.isArray(sRes.data) ? sRes.data : [];
      setSieges(list);
      const charList = Array.isArray(chRes.data) ? chRes.data : (chRes.data?.characters || []);
      setChars(charList);
      if (!contributeForm.character_id && charList[0]?.id) {
        setContributeForm((f) => ({ ...f, character_id: charList[0].id }));
      }
      if (!answerForm.character_id && charList[0]?.id) {
        setAnswerForm((f) => ({ ...f, character_id: charList[0].id }));
      }
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to load the contested board.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 30_000);        // pick up expiries / new contributions
    return () => clearInterval(id);
  }, []);

  const filtered = useMemo(() => (
    nationFilter ? sieges.filter((s) => s.target_nation === nationFilter) : sieges
  ), [sieges, nationFilter]);

  const doContribute = async () => {
    if (!contributeTarget) return;
    if (!contributeForm.character_id) { toast.error('Choose a character.'); return; }
    if ((contributeForm.action_text || '').trim().length < 20) {
      toast.error('Write at least 20 characters of RP.');
      return;
    }
    setSubmitting(true);
    try {
      const r = await api.post(`/sieges/${contributeTarget.id}/contribute`, contributeForm);
      const side = r.data?.contribution?.side || contributeForm.side;
      toast.success(`Committed to the ${side} — the crier will remember.`);
      setContributeTarget(null);
      setContributeForm({ character_id: contributeForm.character_id, side: 'attacker', action_text: '' });
      refresh();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Could not commit your contribution.');
    } finally {
      setSubmitting(false);
    }
  };

  const doAnswer = async () => {
    if (!answerTarget) return;
    if (!answerForm.character_id || !answerForm.defender_faction_slug) {
      toast.error('Choose your character and faction.');
      return;
    }
    setSubmitting(true);
    try {
      await api.post(`/sieges/${answerTarget.id}/answer`, answerForm);
      toast.success('Your faction answers the siege.');
      setAnswerTarget(null);
      refresh();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Could not answer the siege.');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center text-stone-300 bg-black">
        <Loader2 className="w-6 h-6 mr-2 animate-spin" />
        Reading the war-crier&apos;s scrolls…
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-zinc-950 via-stone-950 to-black text-stone-100">
      <div className="max-w-5xl mx-auto px-6 py-12">
        <div className="mb-8 flex flex-wrap items-start justify-between gap-4">
          <div>
            <Link to="/dashboard" className="text-sm text-stone-400 hover:text-stone-200 transition" data-testid="contested-back-link">
              ← Dashboard
            </Link>
            <h1 className="mt-4 text-4xl sm:text-5xl font-bold tracking-tight flex items-center gap-3">
              <Flag className="w-10 h-10 text-rose-400" />
              <span>The Contested Board</span>
            </h1>
            <p className="mt-3 text-stone-400 max-w-3xl">
              Neutral holdings, put to the sword. When a faction lays siege to
              a landmark, any hand — banner-sworn or coin-sworn — may tip the
              scale. Seven world-days settle it.
            </p>
          </div>
          <select
            value={nationFilter}
            onChange={(e) => setNationFilter(e.target.value)}
            className="bg-stone-900 border border-stone-700 rounded-md px-3 py-2 text-stone-100 text-sm"
            data-testid="contested-nation-filter"
          >
            {NATIONS.map((n) => <option key={n.slug} value={n.slug}>{n.label}</option>)}
          </select>
        </div>

        {filtered.length === 0 ? (
          <div className="rounded-xl border border-stone-700/60 bg-stone-950/40 p-10 text-center">
            <Flag className="w-10 h-10 mx-auto text-stone-500 mb-3" />
            <p className="text-stone-400 text-lg">The realm is quiet. No sieges under way.</p>
            <p className="text-stone-500 text-xs mt-2">
              Faction officers may open one from a city&apos;s neutral landmarks.
            </p>
          </div>
        ) : (
          <div className="grid md:grid-cols-2 gap-6" data-testid="contested-list">
            {filtered.map((s) => {
              const att = s.attacker_contribution_count || 0;
              const def = s.defender_contribution_count || 0;
              const total = Math.max(1, att + def);
              const attPct = Math.round((att / total) * 100);
              return (
                <div
                  key={s.id}
                  className="rounded-xl border border-rose-900/40 bg-rose-950/10 p-5"
                  data-testid={`siege-${s.id}`}
                >
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <div className="text-rose-100 font-semibold text-lg flex items-center gap-2">
                        <Swords className="w-4 h-4 text-rose-400" />
                        {s.target_location_name}
                      </div>
                      <div className="text-xs text-stone-400 flex items-center gap-1 mt-1">
                        <MapPin className="w-3 h-3" />
                        {s.target_city_slug ? `${s.target_city_slug} · ` : ''}{s.target_nation}
                      </div>
                    </div>
                    <div className="text-right text-xs">
                      <div className="text-amber-300 flex items-center gap-1 justify-end">
                        <Timer className="w-3 h-3" />
                        {fmtCountdown(s.expires_at)}
                      </div>
                      <div className="text-stone-500 mt-1">
                        opened {s.world_date_opened || '—'}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center justify-between text-xs mb-2">
                    <div className="text-red-300 font-semibold flex items-center gap-1">
                      <Sword className="w-3 h-3" />
                      {s.attacker_faction_name}
                    </div>
                    <div className={`font-semibold flex items-center gap-1 ${s.defender_faction_name ? 'text-emerald-300' : 'text-stone-500 italic'}`}>
                      <Shield className="w-3 h-3" />
                      {s.defender_faction_name || 'unanswered'}
                    </div>
                  </div>

                  <div className="h-2 bg-stone-800/70 rounded-full overflow-hidden mb-2">
                    <div className="h-full bg-red-500/70" style={{ width: `${attPct}%` }} />
                  </div>
                  <div className="flex items-center justify-between text-[10px] text-stone-400 mb-4">
                    <span className="flex items-center gap-1">
                      <Users className="w-3 h-3" /> {att} attacker&nbsp;acts
                    </span>
                    <span className="flex items-center gap-1">
                      {def}&nbsp;defender&nbsp;acts <Users className="w-3 h-3" />
                    </span>
                  </div>

                  <div className="flex gap-2">
                    {!s.defender_faction_slug && (
                      <Button
                        size="sm"
                        variant="outline"
                        className="border-emerald-500/60 text-emerald-100 hover:bg-emerald-900/40 flex-1"
                        onClick={() => setAnswerTarget(s)}
                        data-testid={`answer-siege-${s.id}`}
                      >
                        <Shield className="w-3.5 h-3.5 mr-1" />
                        Answer siege
                      </Button>
                    )}
                    <Button
                      size="sm"
                      className="bg-rose-800 hover:bg-rose-900 text-rose-50 flex-1"
                      onClick={() => {
                        setContributeTarget(s);
                        setContributeForm((f) => ({ ...f, side: 'attacker', action_text: '' }));
                      }}
                      disabled={chars.length === 0}
                      data-testid={`contribute-siege-${s.id}`}
                    >
                      <ScrollText className="w-3.5 h-3.5 mr-1" />
                      Contribute
                    </Button>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        <div className="mt-10 border-t border-stone-800/70 pt-6 text-xs text-stone-500 leading-relaxed">
          <p className="flex items-start gap-2">
            <Trophy className="w-4 h-4 mt-0.5 text-amber-400/70 flex-shrink-0" />
            <span>
              When a siege&apos;s clock runs out, the side with more
              contributions takes the day. If neither side rallies, the crisis
              passes and the landmark stays neutral. A seized holding flies
              the victor&apos;s banner from that point on.
            </span>
          </p>
        </div>
      </div>

      {/* Contribute dialog */}
      <Dialog open={!!contributeTarget} onOpenChange={(o) => !o && setContributeTarget(null)}>
        <DialogContent className="bg-stone-950 border-stone-700 text-stone-100 max-w-lg" data-testid="contribute-dialog">
          <DialogHeader>
            <DialogTitle className="text-xl text-rose-200">
              Commit to the siege of {contributeTarget?.target_location_name}
            </DialogTitle>
            <DialogDescription className="text-stone-400 text-sm">
              One paragraph, in character. One commitment per character — choose your side.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="text-xs text-stone-400 uppercase tracking-widest">Character</label>
              <select
                value={contributeForm.character_id}
                onChange={(e) => setContributeForm({ ...contributeForm, character_id: e.target.value })}
                className="w-full bg-stone-900 border border-stone-700 rounded-md px-3 py-2 text-stone-100 mt-1"
                data-testid="contribute-character-select"
              >
                <option value="">— pick a character —</option>
                {chars.map((c) => (
                  <option key={c.id} value={c.id}>{c.name} — {c.race}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs text-stone-400 uppercase tracking-widest">Side</label>
              <div className="grid grid-cols-2 gap-2 mt-1">
                <button
                  type="button"
                  onClick={() => setContributeForm({ ...contributeForm, side: 'attacker' })}
                  className={`rounded-md border py-2 text-sm ${
                    contributeForm.side === 'attacker'
                      ? 'border-rose-500/60 bg-rose-950/40 text-rose-100'
                      : 'border-stone-700 bg-stone-900 text-stone-300 hover:bg-stone-800'
                  }`}
                  data-testid="contribute-side-attacker"
                >
                  <Sword className="w-3.5 h-3.5 inline mr-2 -mt-0.5" />
                  Attacker — {contributeTarget?.attacker_faction_name}
                </button>
                <button
                  type="button"
                  onClick={() => setContributeForm({ ...contributeForm, side: 'defender' })}
                  className={`rounded-md border py-2 text-sm ${
                    contributeForm.side === 'defender'
                      ? 'border-emerald-500/60 bg-emerald-950/40 text-emerald-100'
                      : 'border-stone-700 bg-stone-900 text-stone-300 hover:bg-stone-800'
                  }`}
                  data-testid="contribute-side-defender"
                >
                  <Shield className="w-3.5 h-3.5 inline mr-2 -mt-0.5" />
                  Defender {contributeTarget?.defender_faction_name ? `— ${contributeTarget.defender_faction_name}` : '(the townsfolk)'}
                </button>
              </div>
            </div>
            <div>
              <label className="text-xs text-stone-400 uppercase tracking-widest">Your act, in the scene</label>
              <Textarea
                value={contributeForm.action_text}
                onChange={(e) => setContributeForm({ ...contributeForm, action_text: e.target.value })}
                placeholder="I raise the crimson banner over the courtyard and bar the eastern gate…"
                rows={5}
                className="mt-1 bg-stone-900 border-stone-700 text-stone-100 min-h-[120px]"
                data-testid="contribute-action-text"
              />
              <div className="text-[10px] text-stone-500 mt-1">
                {(contributeForm.action_text || '').length} / 2000 · min 20
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setContributeTarget(null)} className="text-stone-300 hover:text-stone-100" data-testid="cancel-contribute-btn">
              Cancel
            </Button>
            <Button
              onClick={doContribute}
              disabled={submitting || (contributeForm.action_text || '').trim().length < 20}
              className="bg-rose-800 hover:bg-rose-900 text-rose-50"
              data-testid="submit-contribute-btn"
            >
              {submitting
                ? (<><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Committing…</>)
                : (<><ScrollText className="w-4 h-4 mr-2" /> Commit act</>)}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Answer siege dialog */}
      <Dialog open={!!answerTarget} onOpenChange={(o) => !o && setAnswerTarget(null)}>
        <DialogContent className="bg-stone-950 border-stone-700 text-stone-100" data-testid="answer-dialog">
          <DialogHeader>
            <DialogTitle className="text-xl text-emerald-200">
              Answer the siege of {answerTarget?.target_location_name}
            </DialogTitle>
            <DialogDescription className="text-stone-400 text-sm">
              First faction to answer becomes the defender. Only an Officer or
              Leader may claim this.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="text-xs text-stone-400 uppercase tracking-widest">Your character</label>
              <select
                value={answerForm.character_id}
                onChange={(e) => setAnswerForm({ ...answerForm, character_id: e.target.value })}
                className="w-full bg-stone-900 border border-stone-700 rounded-md px-3 py-2 text-stone-100 mt-1"
                data-testid="answer-character-select"
              >
                <option value="">— pick a character —</option>
                {chars.map((c) => (
                  <option key={c.id} value={c.id}>{c.name} — {c.race}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs text-stone-400 uppercase tracking-widest">Defending faction slug</label>
              <input
                type="text"
                value={answerForm.defender_faction_slug}
                onChange={(e) => setAnswerForm({ ...answerForm, defender_faction_slug: e.target.value.trim().toLowerCase() })}
                placeholder="e.g. ardent-legion"
                className="w-full bg-stone-900 border border-stone-700 rounded-md px-3 py-2 text-stone-100 mt-1"
                data-testid="answer-faction-slug-input"
              />
              <div className="text-[10px] text-stone-500 mt-1">
                Use the slug from the faction page URL (lowercase, hyphens).
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setAnswerTarget(null)} className="text-stone-300 hover:text-stone-100" data-testid="cancel-answer-btn">
              Cancel
            </Button>
            <Button
              onClick={doAnswer}
              disabled={submitting || !answerForm.character_id || !answerForm.defender_faction_slug}
              className="bg-emerald-800 hover:bg-emerald-900 text-emerald-50"
              data-testid="submit-answer-btn"
            >
              {submitting
                ? (<><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Answering…</>)
                : (<><Shield className="w-4 h-4 mr-2" /> Answer siege</>)}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default ContestedCities;
