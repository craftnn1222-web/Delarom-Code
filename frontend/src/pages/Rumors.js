import React, { useEffect, useState, useCallback } from 'react';
import { toast } from 'sonner';
import {
  fetchRumors, fetchMyRumors, plantRumor, getMyCharacters,
} from '../utils/api';
import api from '../utils/api';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Textarea } from '../components/ui/textarea';
import { Label } from '../components/ui/label';
import { MessageCircle, Plus, X, Wind } from 'lucide-react';

/**
 * Whispered Rumors panel — embedded inside Quill & Coffer.
 * "what I started" view with judgement labels.
 */

const NATIONS = ['ammeonon', 'selindori', 'dhor-kuldor', 'aigraels', 'veiled-realms'];

const JUDGEMENT_TINT = {
  true:           'bg-emerald-700/30 border-emerald-500/40 text-emerald-100',
  'partly-true':  'bg-amber-700/30 border-amber-500/40 text-amber-100',
  false:          'bg-rose-700/30 border-rose-500/40 text-rose-100',
};

const RumorsPanel = () => {
  const [tab, setTab] = useState('all');
  const [allRumors, setAllRumors] = useState([]);
  const [myRumors, setMyRumors] = useState([]);
  const [characters, setCharacters] = useState([]);
  const [activeCharId, setActiveCharId] = useState(null);
  const [nationFilter, setNationFilter] = useState('');
  const [showPlant, setShowPlant] = useState(false);
  const [loading, setLoading] = useState(true);

  // Plant form
  const [form, setForm] = useState({
    nation: 'ammeonon',
    subject_kind: 'npc',
    subject_query: '',
    subject_results: [],
    subject: null,
    search_attempted: false,
    text: '',
    submitting: false,
  });

  const loadAll = useCallback(async () => {
    try {
      const r = await fetchRumors(nationFilter ? { nation: nationFilter } : {});
      setAllRumors(r.data || []);
    } catch (e) { console.debug('[Rumors] loadAll failed:', e); }
  }, [nationFilter]);

  const loadMy = useCallback(async () => {
    if (!activeCharId) return;
    try {
      const r = await fetchMyRumors(activeCharId);
      setMyRumors(r.data || []);
    } catch (e) { console.debug('[Rumors] loadMy failed:', e); }
  }, [activeCharId]);

  useEffect(() => {
    (async () => {
      try {
        const r = await getMyCharacters();
        const list = (r.data || []).filter((c) => c.is_active !== false);
        setCharacters(list);
        if (list[0]) setActiveCharId(list[0].id);
      } catch (e) { console.debug('[Rumors] getMyCharacters failed:', e); }
      setLoading(false);
    })();
  }, []);
  useEffect(() => { loadAll(); }, [loadAll]);
  useEffect(() => { loadMy(); }, [loadMy]);

  // Subject search — query NPCs (public endpoint) OR characters from the
  // members directory. The user MUST click one of the results to lock the
  // subject in — typing a name alone does not count as a selection.
  const searchSubject = async (q) => {
    setForm((f) => ({ ...f, subject_query: q, subject_results: [], search_attempted: false }));
    if (q.trim().length < 2) return;
    try {
      if (form.subject_kind === 'npc') {
        const r = await api.get('/npcs/search', { params: { q, nation: form.nation, limit: 8 } });
        setForm((f) => ({
          ...f,
          search_attempted: true,
          subject_results: (r.data || []).map((n) => ({ id: n.id, name: n.name, hint: n.role || n.race || n.location || '' })),
        }));
      } else {
        const r = await api.get('/public/members-directory');
        // The endpoint returns a bare list of members, not { members: [...] }.
        const directory = Array.isArray(r.data) ? r.data : (r.data?.members || []);
        const matches = [];
        for (const m of directory) {
          for (const ch of (m.characters || [])) {
            if (ch.name && ch.name.toLowerCase().includes(q.toLowerCase()) && ch.id !== activeCharId) {
              matches.push({ id: ch.id, name: ch.name, hint: m.username });
            }
          }
        }
        setForm((f) => ({ ...f, search_attempted: true, subject_results: matches.slice(0, 8) }));
      }
    } catch (e) {
      console.debug('[Rumors] searchSubject failed:', e);
      setForm((f) => ({ ...f, search_attempted: true }));
    }
  };

  const handlePlant = async (e) => {
    e.preventDefault();
    if (!form.subject) {
      // More helpful than "Pick a subject" — explains what to do.
      if (form.subject_query.trim()) {
        toast.error('Click a name from the suggestions below to set the subject.');
      } else {
        toast.error('Type and pick a subject for the rumor.');
      }
      return;
    }
    if (form.text.trim().length < 10) { toast.error('A rumor needs at least 10 characters of mischief.'); return; }
    setForm((f) => ({ ...f, submitting: true }));
    try {
      await plantRumor({
        planter_character_id: activeCharId,
        nation: form.nation,
        subject_kind: form.subject_kind,
        subject_id: form.subject.id,
        text: form.text,
      });
      toast.success('The rumor begins its travel.');
      setShowPlant(false);
      setForm((f) => ({ ...f, subject: null, subject_query: '', text: '', submitting: false }));
      loadAll();
      loadMy();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'The rumor fizzled.');
      setForm((f) => ({ ...f, submitting: false }));
    }
  };

  if (loading) return null;

  const renderList = (rumors, showJudgement) => (
    <ul className="space-y-2" data-testid={showJudgement ? 'rumors-my-list' : 'rumors-public-list'}>
      {rumors.length === 0 && (
        <li className="text-gray-500 italic text-center py-8">The wind is still.</li>
      )}
      {rumors.map((r) => (
        <li key={r.id} className="glass-dark p-4 rounded-xl border border-gray-700/40">
          <div className="flex items-start justify-between gap-3 mb-2">
            <p className="text-xs text-gray-400 uppercase tracking-widest">
              About {r.subject_name} <span className="text-gray-500">({r.subject_kind})</span> · {r.nation}
            </p>
            {showJudgement && r.judgement && (
              <span className={`text-[10px] uppercase tracking-widest px-2 py-0.5 rounded-full border ${JUDGEMENT_TINT[r.judgement] || ''}`}>
                {r.judgement}
              </span>
            )}
          </div>
          <p className="text-gray-100 italic">"{r.text}"</p>
          <p className="text-xs text-gray-500 mt-2">
            — Whispered by {r.planter_character_name}, {new Date(r.planted_at).toLocaleDateString()}
          </p>
          {showJudgement && r.judgement_note && (
            <p className="text-xs text-gray-400 mt-1 italic">Oracle's note: {r.judgement_note}</p>
          )}
        </li>
      ))}
    </ul>
  );

  return (
    <div className="container mx-auto px-4 py-6 max-w-4xl">
      <header className="mb-6 flex items-start justify-between flex-wrap gap-4">
        <div>
          <h2 className="text-2xl sm:text-3xl font-bold text-purple-200 flex items-center gap-3">
            <Wind className="w-7 h-7" />
            Whispered Rumors
          </h2>
          <p className="text-gray-400 mt-2 max-w-xl text-sm">
            Tongues wag in every tavern. Some words ring true. Some half. Some are pure invention.
          </p>
        </div>
        {characters.length > 0 && (
          <Button onClick={() => setShowPlant(true)} className="bg-purple-700 hover:bg-purple-600" data-testid="plant-rumor-btn">
            <Plus className="w-4 h-4 mr-2" /> Plant a Rumor
          </Button>
        )}
      </header>

        {/* Tabs */}
        <div className="flex gap-2 border-b border-purple-500/30 mb-4">
          {[
            { k: 'all',  label: 'Heard in Taverns' },
            { k: 'mine', label: 'What You Whispered', count: myRumors.length },
          ].map(({ k, label, count }) => (
            <button key={k} onClick={() => setTab(k)} className={`px-4 py-2 text-sm flex items-center gap-2 border-b-2 transition ${tab === k ? 'border-purple-400 text-purple-200' : 'border-transparent text-gray-400 hover:text-white'}`}>
              <MessageCircle className="w-4 h-4" /> {label}
              {count > 0 && <span className="text-[10px] bg-purple-700 rounded-full px-1.5">{count}</span>}
            </button>
          ))}
        </div>

        {/* Nation filter (only on public list) */}
        {tab === 'all' && (
          <div className="flex flex-wrap gap-2 mb-4">
            <button onClick={() => setNationFilter('')} className={`text-xs px-3 py-1 rounded-full border ${nationFilter === '' ? 'bg-purple-600/40 border-purple-400 text-white' : 'bg-black/30 border-gray-600/40 text-gray-300 hover:text-white'}`}>All nations</button>
            {NATIONS.map((n) => (
              <button key={n} onClick={() => setNationFilter(n)} className={`text-xs px-3 py-1 rounded-full border capitalize ${nationFilter === n ? 'bg-purple-600/40 border-purple-400 text-white' : 'bg-black/30 border-gray-600/40 text-gray-300 hover:text-white'}`}>{n.replace('-', ' ')}</button>
            ))}
          </div>
        )}

        {tab === 'all' && renderList(allRumors, false)}
        {tab === 'mine' && renderList(myRumors, true)}

        {/* Plant Modal */}
        {showPlant && (
          <div className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center px-4" onClick={() => setShowPlant(false)}>
            <form onSubmit={handlePlant} onClick={(e) => e.stopPropagation()} className="glass-dark p-6 rounded-2xl max-w-2xl w-full border border-purple-500/40 max-h-[85vh] overflow-auto" data-testid="plant-rumor-modal">
              <div className="flex items-start justify-between gap-3 mb-4">
                <h2 className="text-2xl font-bold text-purple-200">Plant a Rumor</h2>
                <button type="button" onClick={() => setShowPlant(false)} className="text-gray-400 hover:text-white"><X className="w-5 h-5" /></button>
              </div>
              <div className="space-y-3">
                <div>
                  <Label className="text-gray-300 text-xs">As character</Label>
                  <select value={activeCharId || ''} onChange={(e) => setActiveCharId(e.target.value)} className="mt-1 w-full bg-black/30 border border-purple-500/40 text-white rounded-md px-3 py-2">
                    {characters.map((c) => (<option key={c.id} value={c.id} className="bg-black">{c.name}</option>))}
                  </select>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <Label className="text-gray-300 text-xs">Nation</Label>
                    <select value={form.nation} onChange={(e) => setForm((f) => ({ ...f, nation: e.target.value, subject: null, subject_query: '' }))} className="mt-1 w-full bg-black/30 border border-purple-500/40 text-white rounded-md px-3 py-2 capitalize">
                      {NATIONS.map((n) => (<option key={n} value={n} className="bg-black capitalize">{n.replace('-', ' ')}</option>))}
                    </select>
                  </div>
                  <div>
                    <Label className="text-gray-300 text-xs">About</Label>
                    <select value={form.subject_kind} onChange={(e) => setForm((f) => ({ ...f, subject_kind: e.target.value, subject: null, subject_query: '' }))} className="mt-1 w-full bg-black/30 border border-purple-500/40 text-white rounded-md px-3 py-2">
                      <option value="npc" className="bg-black">An NPC</option>
                      <option value="character" className="bg-black">A player character</option>
                    </select>
                  </div>
                </div>
                <div>
                  <Label className="text-gray-300 text-xs">Subject</Label>
                  {form.subject ? (
                    <div className="mt-1 flex items-center justify-between p-2 rounded-lg bg-purple-900/30 border border-purple-500/30">
                      <span>{form.subject.name} <span className="text-gray-400 text-xs">— {form.subject.hint}</span></span>
                      <button type="button" onClick={() => setForm((f) => ({ ...f, subject: null, subject_query: '' }))} className="text-gray-400 hover:text-white"><X className="w-4 h-4" /></button>
                    </div>
                  ) : (
                    <>
                      <Input value={form.subject_query} onChange={(e) => searchSubject(e.target.value)} placeholder="Type a name, then click a suggestion…" className="mt-1 bg-black/30 border-purple-500/40 text-white" data-testid="rumor-subject-search" />
                      {form.subject_results.length > 0 ? (
                        <ul className="mt-1 bg-black/60 border border-purple-500/30 rounded-lg max-h-48 overflow-auto" data-testid="rumor-subject-results">
                          {form.subject_results.map((s) => (
                            <li key={s.id}>
                              <button type="button" onClick={() => setForm((f) => ({ ...f, subject: s, subject_results: [] }))} className="block w-full text-left px-3 py-2 hover:bg-purple-600/30 text-gray-200">
                                {s.name} <span className="text-gray-500 text-xs">— {s.hint}</span>
                              </button>
                            </li>
                          ))}
                        </ul>
                      ) : form.search_attempted && form.subject_query.trim().length >= 2 ? (
                        <p className="mt-2 text-xs italic text-amber-300/70" data-testid="rumor-no-subject-matches">
                          No {form.subject_kind === 'npc' ? `NPCs in ${form.nation}` : 'player characters'} match &ldquo;{form.subject_query}&rdquo;.
                          Try a different name{form.subject_kind === 'npc' ? ', or pick a different nation' : ''}.
                        </p>
                      ) : null}
                    </>
                  )}
                </div>
                <div>
                  <Label className="text-gray-300 text-xs">The rumor (the oracle will judge its truth privately)</Label>
                  <Textarea value={form.text} onChange={(e) => setForm((f) => ({ ...f, text: e.target.value }))} maxLength={400} rows={4} placeholder="They say…" className="mt-1 bg-black/30 border-purple-500/40 text-white" data-testid="rumor-text-input" />
                </div>
                <Button type="submit" disabled={form.submitting} className="bg-purple-700 hover:bg-purple-600 w-full" data-testid="rumor-submit-btn">
                  {form.submitting ? 'The oracle weighs it…' : 'Set the rumor loose'}
                </Button>
              </div>
            </form>
          </div>
        )}
    </div>
  );
};

export default RumorsPanel;
