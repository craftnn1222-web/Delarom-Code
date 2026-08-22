import React, { useEffect, useState, useCallback } from 'react';
import { toast } from 'sonner';
import { fetchBallads, commissionBallad, getMyCharacters } from '../utils/api';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Textarea } from '../components/ui/textarea';
import { Label } from '../components/ui/label';
import { Music, Sparkles, X, Plus } from 'lucide-react';

/**
 * Ballads panel — embedded inside Quill & Coffer.
 */

const TONES = ['heroic', 'tragic', 'mocking', 'sombre', 'haunting'];

const BalladsPanel = () => {
  const [ballads, setBallads] = useState([]);
  const [open, setOpen] = useState(null);
  const [showCommission, setShowCommission] = useState(false);
  const [characters, setCharacters] = useState([]);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState({
    character_id: '',
    tone: 'heroic',
    title_hint: '',
    event_summary: '',
    submitting: false,
  });

  const load = useCallback(async () => {
    try {
      const r = await fetchBallads();
      setBallads(r.data || []);
    } catch (e) { console.debug("Silent failure:", e); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => {
    load();
    getMyCharacters().then((r) => {
      const list = (r.data || []).filter((c) => c.is_active !== false);
      setCharacters(list);
      if (list.length > 0) {
        setForm((f) => f.character_id ? f : { ...f, character_id: list[0].id });
      }
    }).catch(() => {});
  }, [load]);

  const handleCommission = async (e) => {
    e.preventDefault();
    if (!form.character_id) { toast.error('Pick a character.'); return; }
    if (form.event_summary.trim().length < 10) {
      toast.error('Describe the event in at least 10 characters.');
      return;
    }
    setForm((f) => ({ ...f, submitting: true }));
    try {
      const r = await commissionBallad({
        character_id: form.character_id,
        tone: form.tone,
        title_hint: form.title_hint,
        event_summary: form.event_summary,
      });
      toast.success('The bard has finished the verse.');
      setShowCommission(false);
      setForm((f) => ({ ...f, title_hint: '', event_summary: '', submitting: false }));
      setOpen(r.data);
      load();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'The bard would not sing.');
      setForm((f) => ({ ...f, submitting: false }));
    }
  };

  if (loading) return null;

  return (
    <div className="container mx-auto px-4 py-6 max-w-5xl">
      <header className="mb-6 flex items-start justify-between flex-wrap gap-4">
        <div>
          <h2 className="text-2xl sm:text-3xl font-bold text-amber-200 flex items-center gap-3">
            <Music className="w-7 h-7" />
            Ballads & Folk Tales
          </h2>
          <p className="text-gray-400 mt-2 max-w-2xl text-sm">
            The bards remember what histories forget. Deeds become songs; songs become legend.
          </p>
        </div>
        {characters.length > 0 && (
          <Button onClick={() => setShowCommission(true)} className="bg-amber-700 hover:bg-amber-600" data-testid="commission-ballad-btn">
            <Plus className="w-4 h-4 mr-2" /> Commission a Ballad
          </Button>
        )}
      </header>

        {ballads.length === 0 ? (
          <p className="text-gray-500 italic text-center py-12">
            No songs have yet been sung. Be the first to commission one.
          </p>
        ) : (
          <ul className="space-y-3" data-testid="ballads-list">
            {ballads.map((b) => (
              <li key={b.id}>
                <button onClick={() => setOpen(b)} className="w-full text-left glass-dark p-4 rounded-xl border border-amber-700/30 hover:border-amber-500/50 transition">
                  <div className="flex items-baseline justify-between gap-3">
                    <h3 className="text-lg font-bold text-amber-200">{b.title}</h3>
                    <span className="text-xs text-gray-400 capitalize flex items-center gap-1 flex-shrink-0">
                      <Sparkles className="w-3 h-3" /> {b.tone}
                    </span>
                  </div>
                  <p className="text-sm text-gray-400 italic mt-1">
                    Of {b.subject_character_name} — composed by {b.bard}
                  </p>
                </button>
              </li>
            ))}
          </ul>
        )}

        {open && (
          <div className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center px-4" onClick={() => setOpen(null)}>
            <div className="glass-dark p-6 rounded-2xl max-w-2xl w-full border border-amber-500/40 max-h-[85vh] overflow-auto" onClick={(e) => e.stopPropagation()} data-testid="ballad-modal">
              <div className="flex items-start justify-between gap-3 mb-3">
                <div>
                  <h2 className="text-3xl font-bold text-amber-200">{open.title}</h2>
                  <p className="text-xs uppercase tracking-widest text-gray-400 mt-1">
                    Composed by {open.bard}
                  </p>
                </div>
                <button onClick={() => setOpen(null)} className="text-gray-400 hover:text-white"><X className="w-5 h-5" /></button>
              </div>
              <pre className="text-gray-100 whitespace-pre-wrap font-serif leading-relaxed text-base" data-testid="ballad-body">{open.body}</pre>
              <p className="text-xs text-gray-500 mt-4 italic">
                In honour of {open.subject_character_name} — {new Date(open.composed_at).toLocaleDateString()}
              </p>
            </div>
          </div>
        )}

        {showCommission && (
          <div className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center px-4" onClick={() => setShowCommission(false)}>
            <form onSubmit={handleCommission} onClick={(e) => e.stopPropagation()} className="glass-dark p-6 rounded-2xl max-w-2xl w-full border border-amber-500/40 max-h-[85vh] overflow-auto" data-testid="commission-modal">
              <div className="flex items-start justify-between gap-3 mb-4">
                <h2 className="text-2xl font-bold text-amber-200">Commission a Ballad</h2>
                <button type="button" onClick={() => setShowCommission(false)} className="text-gray-400 hover:text-white"><X className="w-5 h-5" /></button>
              </div>
              <div className="space-y-4">
                <div>
                  <Label className="text-gray-300">For which character?</Label>
                  <select value={form.character_id} onChange={(e) => setForm((f) => ({ ...f, character_id: e.target.value }))} className="mt-1 w-full bg-black/30 border border-amber-500/40 text-white rounded-md px-3 py-2" data-testid="ballad-char-select">
                    {characters.map((c) => (<option key={c.id} value={c.id} className="bg-black">{c.name}</option>))}
                  </select>
                </div>
                <div>
                  <Label className="text-gray-300">Tone</Label>
                  <select value={form.tone} onChange={(e) => setForm((f) => ({ ...f, tone: e.target.value }))} className="mt-1 w-full bg-black/30 border border-amber-500/40 text-white rounded-md px-3 py-2 capitalize" data-testid="ballad-tone-select">
                    {TONES.map((t) => (<option key={t} value={t} className="bg-black capitalize">{t}</option>))}
                  </select>
                </div>
                <div>
                  <Label className="text-gray-300">Title hint (optional)</Label>
                  <Input value={form.title_hint} onChange={(e) => setForm((f) => ({ ...f, title_hint: e.target.value }))} maxLength={120} className="mt-1 bg-black/30 border-amber-500/40 text-white" />
                </div>
                <div>
                  <Label className="text-gray-300">Describe the event (the bard will compose 3-6 stanzas)</Label>
                  <Textarea value={form.event_summary} onChange={(e) => setForm((f) => ({ ...f, event_summary: e.target.value }))} maxLength={1000} rows={6} placeholder="Set the scene — who, what, where, the weight of it…" className="mt-1 bg-black/30 border-amber-500/40 text-white" data-testid="ballad-event-summary" />
                </div>
                <Button type="submit" disabled={form.submitting} className="bg-amber-700 hover:bg-amber-600 w-full" data-testid="ballad-submit-btn">
                  {form.submitting ? 'The bard composes…' : 'Commission'}
                </Button>
              </div>
            </form>
          </div>
        )}
    </div>
  );
};

export default BalladsPanel;
