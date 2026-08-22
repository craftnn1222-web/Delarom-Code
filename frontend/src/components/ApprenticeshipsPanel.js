import React, { useEffect, useState, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { toast } from 'sonner';
import {
  fetchApprenticeships, startApprenticeship, recordMilestone,
  promoteApprentice, graduateApprentice, abandonApprenticeship, fetchCrafts,
  searchMentors,
} from '../utils/api';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Textarea } from './ui/textarea';
import { Label } from './ui/label';
import { Hammer, Plus, X, Award } from 'lucide-react';

const RANK_TINT = {
  initiate:   'bg-stone-700/40 border-stone-500/40 text-stone-100',
  journeyman: 'bg-amber-700/40 border-amber-500/40 text-amber-100',
  master:     'bg-violet-700/40 border-violet-500/40 text-violet-100',
};

const ApprenticeshipsPanel = ({ character }) => {
  const characterId = character?.id;
  const [apps, setApps] = useState([]);
  const [crafts, setCrafts] = useState([]);
  const [ranks, setRanks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showStart, setShowStart] = useState(false);
  const [milestoneFor, setMilestoneFor] = useState(null);
  const [form, setForm] = useState({
    craft: 'smith',
    mentor_query: '',
    mentor_results: [],
    mentor: null,
    intro_text: '',
    submitting: false,
  });

  const load = useCallback(async () => {
    try {
      const [a, c] = await Promise.all([fetchApprenticeships(characterId), fetchCrafts()]);
      setApps(a.data || []);
      setCrafts(c.data?.crafts || []);
      setRanks(c.data?.ranks || []);
    } catch (e) { console.debug("Silent failure:", e); }
    finally { setLoading(false); }
  }, [characterId]);

  useEffect(() => { load(); }, [load]);

  // Pre-load top mentors for the chosen craft (in the character's nation first,
  // then anywhere) whenever the start-modal opens or the craft selection changes.
  // This way the player never sees an empty mentor list and discovers who's available.
  useEffect(() => {
    if (!showStart) return;
    let cancelled = false;
    const loadDefaults = async () => {
      try {
        // Try same-nation first, then fall back to any nation.
        let r = await searchMentors({ craft: form.craft, nation: character?.nation, limit: 8 });
        let matches = r.data || [];
        if (matches.length === 0) {
          r = await searchMentors({ craft: form.craft, limit: 8 });
          matches = r.data || [];
        }
        if (cancelled) return;
        setForm((f) => ({
          ...f,
          mentor_results: matches.map((n) => ({
            id: n.id,
            name: n.name,
            hint: `${n.role || 'Master'} of ${n.location || n.nation || '?'}`,
          })),
        }));
      } catch (e) { console.debug("Silent failure:", e); }
    };
    loadDefaults();
    return () => { cancelled = true; };
  }, [showStart, form.craft, character?.nation]);

  const searchMentor = async (q) => {
    setForm((f) => ({ ...f, mentor_query: q }));
    const query = q.trim();
    try {
      const params = { craft: form.craft };
      if (query.length >= 1) params.q = query;
      // Bias toward same nation but fall back to all if nothing matches.
      let r = await searchMentors({ ...params, nation: character?.nation, limit: 12 });
      let matches = r.data || [];
      if (matches.length === 0) {
        r = await searchMentors({ ...params, limit: 12 });
        matches = r.data || [];
      }
      setForm((f) => ({
        ...f,
        mentor_results: matches.map((n) => ({
          id: n.id,
          name: n.name,
          hint: `${n.role || 'Master'} of ${n.location || n.nation || '?'}`,
        })),
      }));
    } catch (e) { console.debug("Silent failure:", e); }
  };

  const handleStart = async (e) => {
    e.preventDefault();
    if (!form.mentor) { toast.error('Pick a mentor NPC.'); return; }
    setForm((f) => ({ ...f, submitting: true }));
    try {
      await startApprenticeship({
        character_id: characterId,
        mentor_npc_id: form.mentor.id,
        craft: form.craft,
        intro_text: form.intro_text,
      });
      toast.success('Apprenticeship begun.');
      setShowStart(false);
      setForm((f) => ({ ...f, mentor: null, mentor_query: '', intro_text: '', submitting: false }));
      load();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed.');
      setForm((f) => ({ ...f, submitting: false }));
    }
  };

  const handlePromote = async (app) => {
    const cur = ranks.indexOf(app.rank);
    if (cur === -1 || cur >= ranks.length - 1) return;
    try { await promoteApprentice(app.id, ranks[cur + 1]); toast.success(`Promoted to ${ranks[cur + 1]}.`); load(); }
    catch (err) { toast.error(err.response?.data?.detail || 'Failed.'); }
  };
  const handleGraduate = async (app) => {
    try { await graduateApprentice(app.id); toast.success('Graduated.'); load(); }
    catch (err) { toast.error(err.response?.data?.detail || 'Failed.'); }
  };
  const handleAbandon = async (app) => {
    if (!window.confirm('Walk away from this apprenticeship?')) return;
    try { await abandonApprenticeship(app.id); toast.success('Apprenticeship ended.'); load(); }
    catch (err) { toast.error(err.response?.data?.detail || 'Failed.'); }
  };
  const handleMilestone = async (e) => {
    e.preventDefault();
    const text = e.target.elements.text.value.trim();
    if (!text) return;
    try { await recordMilestone(milestoneFor.id, text); toast.success('Milestone marked.'); setMilestoneFor(null); load(); }
    catch (err) { toast.error(err.response?.data?.detail || 'Failed.'); }
  };

  if (loading) return null;

  return (
    <div data-testid="apprenticeships-panel">
      <div className="flex items-center justify-between mb-3">
        <p className="text-sm text-gray-300">
          Long-term craft training under a master NPC.
        </p>
        <Button size="sm" onClick={() => setShowStart(true)} className="bg-amber-700 hover:bg-amber-600" data-testid="apprenticeship-start-btn">
          <Plus className="w-4 h-4 mr-1" /> New
        </Button>
      </div>

      {apps.length === 0 ? (
        <p className="text-gray-500 italic text-sm">No apprenticeships yet.</p>
      ) : (
        <ul className="space-y-3" data-testid="apprenticeship-list">
          {apps.map((a) => (
            <li key={a.id} className={`p-4 rounded-xl border ${RANK_TINT[a.rank] || RANK_TINT.initiate}`} data-testid={`apprenticeship-${a.id}`}>
              <div className="flex items-start justify-between gap-2 mb-1">
                <div>
                  <p className="text-xs uppercase tracking-widest opacity-80">{a.status === 'active' ? a.craft : `${a.craft} — ${a.status}`}</p>
                  <p className="font-bold">Under {a.mentor_npc_name}</p>
                </div>
                <span className="text-xs uppercase tracking-widest font-bold capitalize">{a.rank}</span>
              </div>
              {a.milestones && a.milestones.length > 0 && (
                <details className="mt-2">
                  <summary className="cursor-pointer text-xs uppercase tracking-widest opacity-80">{a.milestones.length} milestone{a.milestones.length === 1 ? '' : 's'}</summary>
                  <ul className="mt-2 space-y-1 text-sm">
                    {a.milestones.map((m) => (
                      <li key={m.id} className="border-l-2 border-current/40 pl-2 italic">
                        {m.text} <span className="text-xs opacity-60">— as {m.rank_at_time}</span>
                      </li>
                    ))}
                  </ul>
                </details>
              )}
              {a.status === 'active' && (
                <div className="flex flex-wrap gap-2 mt-3">
                  <Button size="sm" variant="outline" onClick={() => setMilestoneFor(a)} data-testid={`apprenticeship-milestone-${a.id}`}>+ Milestone</Button>
                  {a.rank !== 'master' && (
                    <Button size="sm" onClick={() => handlePromote(a)} className="bg-amber-700 hover:bg-amber-600" data-testid={`apprenticeship-promote-${a.id}`}>Promote</Button>
                  )}
                  {a.rank === 'master' && (
                    <Button size="sm" onClick={() => handleGraduate(a)} className="bg-violet-700 hover:bg-violet-600" data-testid={`apprenticeship-graduate-${a.id}`}>
                      <Award className="w-4 h-4 mr-1" /> Graduate
                    </Button>
                  )}
                  <Button size="sm" variant="outline" onClick={() => handleAbandon(a)} className="border-red-500/50 text-red-300 hover:bg-red-500/20">Abandon</Button>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}

      {/* Start modal — portaled to <body> via createPortal to escape the
          parent Apprenticeships Radix Dialog. Radix Dialog uses a CSS
          `transform` to centre itself, which makes that DialogContent the
          containing block for ANY position:fixed descendant. Without the
          portal, our overlay gets sized to the small parent dialog instead
          of the viewport. Portaling moves the DOM node to document.body so
          `fixed inset-0` covers the whole screen as intended.

          IMPORTANT: Radix Dialog also locks `<body>` with
          `pointer-events: none` (via react-remove-scroll) so only the Radix
          DialogContent (which sets `pointer-events: auto`) is clickable.
          Our portaled overlay therefore MUST explicitly set
          `pointer-events: auto` or every click on it is dropped — making
          the whole page feel frozen. */}
      {showStart && createPortal((
        <div
          className="fixed inset-0 z-[60] bg-black/70 flex items-start sm:items-center justify-center p-4 overflow-y-auto pointer-events-auto"
          onClick={() => setShowStart(false)}
          data-testid="apprenticeship-start-modal"
        >
          <form
            onSubmit={handleStart}
            onClick={(e) => e.stopPropagation()}
            className="bg-gray-900 border border-amber-500/40 text-white max-w-lg w-full rounded-2xl p-6 my-6 max-h-[85vh] overflow-y-auto"
          >
            <div className="flex items-start justify-between gap-3 mb-4">
              <h2 className="text-xl text-amber-200 flex items-center gap-2 font-bold">
                <Hammer className="w-5 h-5" /> Apprentice Yourself
              </h2>
              <button
                type="button"
                onClick={() => setShowStart(false)}
                className="text-gray-400 hover:text-white"
                aria-label="Close"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="space-y-3">
              <div>
                <Label className="text-gray-300 text-xs">Craft</Label>
                <select
                  value={form.craft}
                  onChange={(e) => setForm((f) => ({ ...f, craft: e.target.value, mentor: null, mentor_results: [], mentor_query: '' }))}
                  className="mt-1 w-full bg-black/30 border border-amber-500/40 text-white capitalize rounded-md px-3 py-2"
                  data-testid="apprenticeship-craft-select"
                >
                  {crafts.map((c) => (
                    <option key={c} value={c} className="bg-black capitalize" data-testid={`apprenticeship-craft-option-${c}`}>
                      {c}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <Label className="text-gray-300 text-xs">Mentor (master of the chosen craft)</Label>
                {form.mentor ? (
                  <div className="mt-1 flex items-center justify-between p-2 rounded-lg bg-amber-900/30 border border-amber-500/30">
                    <span>{form.mentor.name} <span className="text-gray-400 text-xs">— {form.mentor.hint}</span></span>
                    <button type="button" onClick={() => setForm((f) => ({ ...f, mentor: null, mentor_query: '' }))} className="text-gray-400 hover:text-white"><X className="w-4 h-4" /></button>
                  </div>
                ) : (
                  <>
                    <Input
                      value={form.mentor_query}
                      onChange={(e) => searchMentor(e.target.value)}
                      placeholder={`Search masters of ${form.craft}… (or pick from the list below)`}
                      className="mt-1 bg-black/30 border-amber-500/40 text-white"
                      data-testid="apprenticeship-mentor-search"
                    />
                    {form.mentor_results.length > 0 ? (
                      <ul className="mt-1 bg-black/60 border border-amber-500/30 rounded-lg max-h-48 overflow-auto" data-testid="apprenticeship-mentor-results">
                        {form.mentor_results.map((m) => (
                          <li key={m.id}>
                            <button
                              type="button"
                              onClick={() => setForm((f) => ({ ...f, mentor: m, mentor_results: [] }))}
                              className="block w-full text-left px-3 py-2 hover:bg-amber-600/30 text-gray-200"
                              data-testid={`apprenticeship-mentor-option-${m.id}`}
                            >
                              {m.name} <span className="text-gray-500 text-xs">— {m.hint}</span>
                            </button>
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="mt-2 text-xs italic text-gray-500">No masters of this craft are known yet. Try a different craft.</p>
                    )}
                  </>
                )}
              </div>
              <div>
                <Label className="text-gray-300 text-xs">Opening note (optional)</Label>
                <Textarea
                  value={form.intro_text}
                  onChange={(e) => setForm((f) => ({ ...f, intro_text: e.target.value }))}
                  rows={3}
                  maxLength={400}
                  placeholder="The first sweeping of the forge floor…"
                  className="mt-1 bg-black/30 border-amber-500/40 text-white"
                />
              </div>
              <Button type="submit" disabled={form.submitting} className="bg-amber-700 hover:bg-amber-600 w-full" data-testid="apprenticeship-submit-btn">
                {form.submitting ? 'Binding the oath…' : 'Begin Apprenticeship'}
              </Button>
            </div>
          </form>
        </div>
      ), document.body)}

      {/* Milestone modal — also portaled for the same reason, and also
          MUST set `pointer-events-auto` to escape Radix's body-level
          pointer-events lock (see the Start modal comment above). */}
      {milestoneFor && createPortal((
        <div
          className="fixed inset-0 z-[60] bg-black/70 flex items-center justify-center p-4 pointer-events-auto"
          onClick={() => setMilestoneFor(null)}
          data-testid="apprenticeship-milestone-modal"
        >
          <form
            onSubmit={handleMilestone}
            onClick={(e) => e.stopPropagation()}
            className="bg-gray-900 border border-amber-500/40 text-white max-w-lg w-full rounded-2xl p-6"
          >
            <div className="flex items-start justify-between gap-3 mb-3">
              <h3 className="text-lg text-amber-200 font-bold">Record a milestone</h3>
              <button type="button" onClick={() => setMilestoneFor(null)} className="text-gray-400 hover:text-white" aria-label="Close">
                <X className="w-5 h-5" />
              </button>
            </div>
            <Textarea name="text" rows={4} maxLength={300} placeholder="What did you learn or accomplish?" className="bg-black/30 border-amber-500/40 text-white" required />
            <div className="flex gap-2 mt-3 justify-end">
              <Button type="button" variant="outline" onClick={() => setMilestoneFor(null)}>Cancel</Button>
              <Button type="submit" className="bg-amber-700 hover:bg-amber-600">Mark</Button>
            </div>
          </form>
        </div>
      ), document.body)}
    </div>
  );
};

export default ApprenticeshipsPanel;
