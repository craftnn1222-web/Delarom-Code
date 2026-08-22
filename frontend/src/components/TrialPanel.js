import React, { useEffect, useState, useCallback } from 'react';
import { Scale, Gavel, Mic2, Users, AlertTriangle, Hourglass, ShieldX } from 'lucide-react';
import { Button } from './ui/button';
import { toast } from 'sonner';
import api from '../utils/api';

/**
 * Courtroom Trial Panel.
 *
 * Renders the active multi-turn trial scene: opening narration, judge +
 * prosecutor + witness list, prior defence turns, and an input for the
 * next defence. Replaces the old one-shot verdict modal.
 *
 * Props:
 *   - characterId: string  (required)
 *   - onFinalized: ({verdict, imprisonment, trial}) => void
 *                   Called after the trial concludes so the parent page can
 *                   redirect to the jail / refresh state.
 */
const TrialPanel = ({ characterId, onFinalized }) => {
  const [trialState, setTrialState] = useState(null);
  const [loading, setLoading] = useState(true);
  const [defenceText, setDefenceText] = useState('');
  const [defending, setDefending] = useState(false);
  const [resting, setResting] = useState(false);
  const [lastTurnResult, setLastTurnResult] = useState(null);

  const fetchTrial = useCallback(async () => {
    if (!characterId) {
      setLoading(false);
      return;
    }
    try {
      const res = await api.get(`/characters/${characterId}/trial`);
      setTrialState(res.data || {});
    } catch (err) {
      console.error('Failed to load trial state', err);
    } finally {
      setLoading(false);
    }
  }, [characterId]);

  useEffect(() => {
    fetchTrial();
  }, [fetchTrial]);

  if (loading) {
    return (
      <div className="glass-dark p-6 rounded-xl mb-6 border border-amber-500/30 text-amber-200 text-sm" data-testid="trial-panel-loading">
        Loading trial state…
      </div>
    );
  }

  const trial = trialState?.trial;
  if (!trial) return null;

  const turnsUsed = trial.defense_turns_used || 0;
  const maxTurns = trial.max_defense_turns || 5;
  const turnsLeft = Math.max(0, maxTurns - turnsUsed);
  const history = trial.defense_history || [];
  const judge = trialState.judge;
  const prosecutor = trialState.prosecutor;
  const witnesses = trialState.witnesses || [];

  const handleDefend = async () => {
    const text = defenceText.trim();
    if (!text) {
      toast.error('Speak your defence before the court.');
      return;
    }
    if (turnsLeft <= 0) {
      toast.error('No defence turns remain — rest your case for the verdict.');
      return;
    }
    setDefending(true);
    try {
      const res = await api.post(`/characters/${characterId}/trial/defend`, {
        defence_text: text,
      });
      const data = res.data || {};
      setLastTurnResult(data.turn_result || null);
      if (data.turn_result?.judge_cut_off) {
        toast.warning('The judge cuts the defence short!');
      } else if ((data.turn_result?.leniency_delta || 0) > 0) {
        toast.success('The court softens toward you.');
      } else if ((data.turn_result?.leniency_delta || 0) < 0) {
        toast.error('The court hardens against you.');
      } else {
        toast('The court records your defence.', { duration: 3500 });
      }
      setDefenceText('');
      if (data.finalized) {
        toast(`Verdict: ${data.verdict?.verdict_summary || 'sentence delivered.'}`, { duration: 9000 });
        if (typeof onFinalized === 'function') {
          onFinalized({
            verdict: data.verdict,
            imprisonment: data.imprisonment,
            trial: data.trial,
          });
        }
      }
      await fetchTrial();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'The court rejects your defence.');
    } finally {
      setDefending(false);
    }
  };

  const handleRestCase = async () => {
    if (!window.confirm('Rest your case? The judge will deliver the final verdict now based on the defence offered so far.')) return;
    setResting(true);
    try {
      const res = await api.post(`/characters/${characterId}/trial/rest-case`);
      const data = res.data || {};
      toast(`Verdict: ${data.verdict?.verdict_summary || 'sentence delivered.'}`, { duration: 9000 });
      if (typeof onFinalized === 'function') {
        onFinalized({
          verdict: data.verdict,
          imprisonment: data.imprisonment,
          trial: data.trial,
        });
      }
      await fetchTrial();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to rest case');
    } finally {
      setResting(false);
    }
  };

  return (
    <div
      className="glass-dark p-6 rounded-xl mb-6 border-2 border-amber-500/50 bg-gradient-to-b from-amber-900/15 to-black/40"
      data-testid="trial-panel"
    >
      <div className="flex items-start gap-3 mb-4">
        <Scale className="w-8 h-8 text-amber-300 flex-shrink-0" />
        <div className="flex-1">
          <p className="text-amber-200 font-bold uppercase tracking-widest text-sm">
            Trial in Session
          </p>
          <p className="text-amber-100 text-base mt-1">
            {trial.character_name} stands accused before the court.
          </p>
        </div>
        <div className="text-right">
          <p className="text-xs text-amber-200/70 uppercase">Turns Remaining</p>
          <p className="text-2xl font-bold text-amber-200" data-testid="trial-turns-remaining">
            {turnsLeft} / {maxTurns}
          </p>
        </div>
      </div>

      {/* Court personnel */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-4">
        {judge && (
          <div className="p-3 rounded-lg bg-black/40 border border-amber-500/30">
            <div className="flex items-center gap-2 text-amber-300 text-xs uppercase tracking-wider mb-1">
              <Gavel className="w-3.5 h-3.5" /> Presiding
            </div>
            <p className="font-semibold text-amber-100">{judge.name}</p>
            {judge.appearance && (
              <p className="text-xs italic text-amber-100/70 mt-1">{judge.appearance}</p>
            )}
          </div>
        )}
        {prosecutor && (
          <div className="p-3 rounded-lg bg-black/40 border border-rose-500/30">
            <div className="flex items-center gap-2 text-rose-300 text-xs uppercase tracking-wider mb-1">
              <Mic2 className="w-3.5 h-3.5" /> Prosecution
            </div>
            <p className="font-semibold text-rose-100">{prosecutor.name}</p>
            {prosecutor.appearance && (
              <p className="text-xs italic text-rose-100/70 mt-1">{prosecutor.appearance}</p>
            )}
          </div>
        )}
      </div>

      {/* Witnesses */}
      {witnesses.length > 0 && (
        <div className="mb-4 p-3 rounded-lg bg-black/30 border border-amber-500/20">
          <div className="flex items-center gap-2 text-amber-200/90 text-xs uppercase tracking-wider mb-2">
            <Users className="w-3.5 h-3.5" /> Witnesses summoned ({witnesses.length})
          </div>
          <div className="flex flex-wrap gap-2">
            {witnesses.map((w, i) => (
              <span
                key={`${w.name}-${i}`}
                className="text-xs px-2 py-1 rounded-full bg-amber-900/30 border border-amber-500/30 text-amber-100"
                data-testid={`trial-witness-${i}`}
              >
                {w.name} <span className="text-amber-300/60">· {w.crime_summary}</span>
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Charges summary */}
      <div className="mb-4 p-3 rounded-lg bg-black/30 border border-rose-500/20">
        <p className="text-xs uppercase tracking-wider text-rose-200/80 mb-1">
          Charges (total bounty {Number(trial.total_bounty || 0).toLocaleString()}g)
        </p>
        <ul className="text-sm text-rose-100/90 space-y-1">
          {(trial.open_crimes_snapshot || []).slice(0, 6).map((c, i) => (
            <li key={c.id || i} data-testid={`trial-charge-${i}`}>
              <span className="font-semibold text-rose-200">[{(c.severity || 'minor').toUpperCase()}]</span>{' '}
              {c.crime_type} against {c.victim_name || 'unknown'} ({c.victim_importance || 'commoner'})
            </li>
          ))}
        </ul>
      </div>

      {/* Opening narration + history */}
      {trial.opening_narration && history.length === 0 && (
        <div className="mb-4 p-3 rounded-lg bg-black/40 border border-amber-500/30 italic text-amber-100/90 text-sm" data-testid="trial-opening">
          {trial.opening_narration}
        </div>
      )}

      {history.length > 0 && (
        <div className="mb-4 space-y-2 max-h-80 overflow-y-auto pr-2" data-testid="trial-history">
          {history.map((h, i) => (
            <div key={i} className="p-3 rounded-lg bg-black/30 border border-amber-500/20">
              <div className="flex items-center justify-between mb-1">
                <p className="text-xs uppercase tracking-wider text-amber-300/80">
                  Turn {h.turn} · {h.judge_cut_off ? 'Cut off' : `Leniency Δ ${h.leniency_delta > 0 ? '+' : ''}${h.leniency_delta}`}
                </p>
                {h.judge_cut_off && <ShieldX className="w-3.5 h-3.5 text-rose-300" />}
              </div>
              <p className="text-sm text-amber-100/90">
                <span className="font-semibold text-amber-200">Defendant:</span>{' '}
                <span className="italic">{h.defence_text}</span>
              </p>
              <p className="text-sm text-amber-100/80 mt-2">{h.ai_narration}</p>
              {h.judge_remark && (
                <p className="text-xs italic text-amber-200 mt-2">
                  ⚖ {h.judge_remark}
                </p>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Last turn detail (highlighted) */}
      {lastTurnResult?.judge_cut_off && (
        <div className="mb-4 p-3 rounded-lg bg-rose-900/30 border border-rose-500/40 flex items-start gap-2" data-testid="trial-cut-off-alert">
          <AlertTriangle className="w-4 h-4 text-rose-300 flex-shrink-0 mt-0.5" />
          <p className="text-rose-100 text-sm">
            The judge has cut off further defence. The verdict has been rendered.
          </p>
        </div>
      )}

      {/* Defence input */}
      {turnsLeft > 0 && (
        <div className="space-y-2">
          <label className="text-xs uppercase tracking-wider text-amber-200/80">
            Your Defence ({turnsLeft} turn{turnsLeft === 1 ? '' : 's'} remaining)
          </label>
          <textarea
            value={defenceText}
            onChange={(e) => setDefenceText(e.target.value)}
            rows={4}
            placeholder='Plead your case. Specifics persuade — vague denials do not. Try alibis, witnesses, bribes (in named denomination), rank, mercy, contrition…'
            className="w-full bg-black/50 border border-amber-500/40 rounded-md p-3 text-sm text-amber-50 placeholder-amber-200/30 focus:border-amber-400 focus:outline-none"
            disabled={defending || resting}
            data-testid="trial-defence-input"
          />
          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              onClick={handleDefend}
              disabled={defending || resting || !defenceText.trim()}
              className="bg-gradient-to-r from-amber-600 to-amber-500 hover:from-amber-700 hover:to-amber-600 text-black font-semibold"
              data-testid="trial-submit-defence-btn"
            >
              {defending ? <Hourglass className="w-4 h-4 mr-2 animate-spin" /> : <Mic2 className="w-4 h-4 mr-2" />}
              {defending ? 'The court deliberates…' : 'Speak your defence'}
            </Button>
            <Button
              type="button"
              variant="outline"
              onClick={handleRestCase}
              disabled={defending || resting}
              className="border-amber-500/40 text-amber-200 hover:bg-amber-900/30"
              data-testid="trial-rest-case-btn"
            >
              <Scale className="w-4 h-4 mr-2" />
              {resting ? 'Awaiting verdict…' : 'Rest my case'}
            </Button>
          </div>
        </div>
      )}

      {turnsLeft <= 0 && trial.status === 'in_session' && (
        <div className="space-y-2">
          <p className="text-amber-200 text-sm">
            All defence turns have been used. The judge will deliver the verdict.
          </p>
          <Button
            type="button"
            onClick={handleRestCase}
            disabled={resting}
            className="bg-gradient-to-r from-amber-600 to-amber-500 text-black font-semibold"
            data-testid="trial-rest-case-final-btn"
          >
            <Scale className="w-4 h-4 mr-2" />
            {resting ? 'Awaiting verdict…' : 'Receive verdict'}
          </Button>
        </div>
      )}

      {trial.status !== 'in_session' && trial.verdict && (
        <div className="mt-4 p-4 rounded-lg bg-black/50 border border-amber-500/40" data-testid="trial-verdict">
          <p className="text-amber-200 font-bold uppercase tracking-wider text-sm mb-2">
            Final Verdict
          </p>
          <p className="text-amber-100 italic mb-2">{trial.verdict.narration}</p>
          <p className="text-amber-300 font-semibold">{trial.verdict.verdict_summary}</p>
        </div>
      )}
    </div>
  );
};

export default TrialPanel;
