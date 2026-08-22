import React, { useEffect, useState, useCallback } from 'react';
import { toast } from 'sonner';
import {
  fetchDreams, sleepAndDream,
  fetchProphecy, receiveProphecy,
  fetchPersona, upsertPersona, togglePersona, dropPersona,
} from '../utils/api';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Textarea } from './ui/textarea';
import { Label } from './ui/label';
import { Moon, Sparkles, Eye, EyeOff, Trash2 } from 'lucide-react';

/**
 * MysteryIdentityPanel — Phase 4 hub. Three tabs:
 *   • Dreams  — once-per-day AI dream sequence + history
 *   • Prophecy — one-time AI prophecy
 *   • Persona — declarable disguise (toggle on/off)
 */

const MOOD_TINTS = {
  serene:     'border-sky-500/40    bg-sky-900/15    text-sky-50',
  unsettling: 'border-purple-500/40 bg-purple-900/20 text-purple-50',
  haunting:   'border-violet-500/40 bg-violet-950/30 text-violet-50',
  radiant:    'border-amber-400/50  bg-amber-900/20  text-amber-50',
  sorrowful:  'border-blue-500/40   bg-blue-900/20   text-blue-50',
  mocking:    'border-rose-500/40   bg-rose-900/20   text-rose-50',
  fevered:    'border-red-500/40    bg-red-900/20    text-red-50',
};

const MysteryIdentityPanel = ({ character }) => {
  const [tab, setTab] = useState('dreams');
  const characterId = character?.id;
  if (!characterId) return null;

  return (
    <div data-testid="mystery-panel">
      <div className="flex gap-2 border-b border-purple-500/30 mb-4">
        {[
          { k: 'dreams',   label: 'Dreams',   icon: Moon },
          { k: 'prophecy', label: 'Prophecy', icon: Sparkles },
          { k: 'persona',  label: 'Persona',  icon: Eye },
        ].map(({ k, label, icon: Icon }) => (
          <button key={k} onClick={() => setTab(k)}
            className={`px-4 py-2 text-sm flex items-center gap-2 border-b-2 transition ${tab === k ? 'border-purple-400 text-purple-200' : 'border-transparent text-gray-400 hover:text-white'}`}
            data-testid={`mystery-tab-${k}`}>
            <Icon className="w-4 h-4" /> {label}
          </button>
        ))}
      </div>
      {tab === 'dreams' && <DreamsTab characterId={characterId} />}
      {tab === 'prophecy' && <ProphecyTab characterId={characterId} characterName={character.name} />}
      {tab === 'persona' && <PersonaTab characterId={characterId} characterName={character.name} />}
    </div>
  );
};


const DreamsTab = ({ characterId }) => {
  const [state, setState] = useState({ dreams: [], can_dream_today: true });
  const [loading, setLoading] = useState(true);
  const [sleeping, setSleeping] = useState(false);
  const [latest, setLatest] = useState(null);

  const load = useCallback(async () => {
    try {
      const r = await fetchDreams(characterId);
      setState(r.data || { dreams: [], can_dream_today: true });
    } catch (e) { console.debug('[Dreams] fetchDreams failed:', e); }
    finally { setLoading(false); }
  }, [characterId]);

  useEffect(() => { load(); }, [load]);

  const handleSleep = async () => {
    setSleeping(true);
    try {
      const r = await sleepAndDream(characterId);
      setLatest(r.data);
      toast.success('You drift away…');
      load();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Sleep would not come.');
    } finally { setSleeping(false); }
  };

  if (loading) return null;

  return (
    <div data-testid="dreams-tab">
      {state.can_dream_today ? (
        <Button onClick={handleSleep} disabled={sleeping} className="bg-indigo-700 hover:bg-indigo-600 mb-4" data-testid="sleep-btn">
          <Moon className="w-4 h-4 mr-2" />
          {sleeping ? 'The dream takes shape…' : 'Sleep and Dream'}
        </Button>
      ) : (
        <p className="text-gray-400 italic mb-4">You have already dreamed today. Try again at dawn.</p>
      )}

      {(latest || state.dreams[0]) && (
        <Dream dream={latest || state.dreams[0]} />
      )}

      {state.dreams.length > 1 && (
        <div className="mt-6">
          <p className="text-xs uppercase tracking-widest text-gray-500 mb-2">Earlier dreams</p>
          <ul className="space-y-2">
            {state.dreams.slice(latest ? 0 : 1).map((d) => (
              <li key={d.id}><Dream dream={d} compact /></li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};

const Dream = ({ dream, compact = false }) => {
  const tint = MOOD_TINTS[dream.mood] || MOOD_TINTS.unsettling;
  return (
    <div className={`p-4 rounded-xl border ${tint}`} data-testid={`dream-${dream.id}`}>
      <p className="text-xs uppercase tracking-widest opacity-80 mb-2">
        {new Date(dream.dreamed_at).toLocaleDateString()} — Mood: {dream.mood}
      </p>
      <p className={`whitespace-pre-wrap leading-relaxed ${compact ? 'text-sm' : ''}`}>{dream.body}</p>
    </div>
  );
};


const ProphecyTab = ({ characterId, characterName }) => {
  const [prophecy, setProphecy] = useState(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [context, setContext] = useState('');

  const load = useCallback(async () => {
    try {
      const r = await fetchProphecy(characterId);
      setProphecy(r.data || null);
    } catch (e) { console.debug('[Prophecy] fetchProphecy failed:', e); }
    finally { setLoading(false); }
  }, [characterId]);

  useEffect(() => { load(); }, [load]);

  const handleReceive = async () => {
    setGenerating(true);
    try {
      const r = await receiveProphecy(characterId, context);
      setProphecy(r.data);
      toast.success('The oracle has spoken.');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'The oracle is silent.');
    } finally { setGenerating(false); }
  };

  if (loading) return null;

  if (prophecy) {
    return (
      <div data-testid="prophecy-revealed" className="p-6 rounded-xl border border-violet-500/40 bg-violet-900/20">
        <p className="text-xs uppercase tracking-widest text-violet-300 mb-3">
          The oracle's words to {characterName}
        </p>
        <blockquote className="text-violet-100 text-lg leading-relaxed italic font-serif whitespace-pre-wrap" data-testid="prophecy-text">
          {prophecy.text}
        </blockquote>
        <p className="text-xs text-gray-500 mt-4">
          Spoken {new Date(prophecy.delivered_at).toLocaleDateString()}
          {prophecy.fulfilled && <span className="ml-3 text-amber-300">— FULFILLED</span>}
        </p>
        {prophecy.context && (
          <p className="text-xs text-gray-500 mt-1 italic">"{prophecy.context}"</p>
        )}
      </div>
    );
  }

  return (
    <div data-testid="prophecy-blank">
      <p className="text-gray-300 mb-3">
        The oracle speaks only once for any soul. Once received, the prophecy is permanent.
      </p>
      <Label className="text-gray-300 text-xs">Where does the oracle find you? (optional flavour)</Label>
      <Input value={context} onChange={(e) => setContext(e.target.value)} maxLength={400}
        placeholder="A fortune-teller at the docks; a dream at the temple…"
        className="mt-1 bg-black/30 border-violet-500/40 text-white mb-3"
        data-testid="prophecy-context-input" />
      <Button onClick={handleReceive} disabled={generating} className="bg-violet-700 hover:bg-violet-600" data-testid="prophecy-receive-btn">
        <Sparkles className="w-4 h-4 mr-2" />
        {generating ? 'The oracle gathers her words…' : 'Hear the Oracle'}
      </Button>
    </div>
  );
};


const PersonaTab = ({ characterId, characterName }) => {
  const [persona, setPersona] = useState(null);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({ name: '', race: '', background: '' });

  const load = useCallback(async () => {
    try {
      const r = await fetchPersona(characterId);
      setPersona(r.data || null);
      if (r.data) {
        setForm({ name: r.data.name || '', race: r.data.race || '', background: r.data.background || '' });
      }
    } catch (e) { console.debug('[Persona] fetchPersona failed:', e); }
    finally { setLoading(false); }
  }, [characterId]);

  useEffect(() => { load(); }, [load]);

  const handleSave = async (e) => {
    e.preventDefault();
    if (!form.name.trim()) { toast.error('A persona needs a name.'); return; }
    try {
      const r = await upsertPersona(characterId, form);
      setPersona(r.data);
      setEditing(false);
      toast.success('Persona declared.');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Save failed.');
    }
  };

  const handleToggle = async () => {
    try {
      const r = await togglePersona(characterId, !persona.active);
      setPersona(r.data);
      toast.success(r.data.active ? 'Disguise activated.' : 'Disguise dropped.');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed.');
    }
  };

  const handleDrop = async () => {
    try {
      await dropPersona(characterId);
      setPersona(null);
      setForm({ name: '', race: '', background: '' });
      toast.success('Persona forgotten.');
    } catch (_err) {
      toast.error('Failed.');
    }
  };

  if (loading) return null;

  if (!persona || editing) {
    return (
      <form onSubmit={handleSave} data-testid="persona-edit-form">
        <p className="text-gray-300 mb-3">
          Declare a persona — a name and face you wear when you do not wish the world to see {characterName}.
        </p>
        <div className="space-y-3">
          <div>
            <Label className="text-gray-300 text-xs">Persona name</Label>
            <Input value={form.name} onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))} maxLength={80} className="mt-1 bg-black/30 border-purple-500/40 text-white" data-testid="persona-name-input" />
          </div>
          <div>
            <Label className="text-gray-300 text-xs">Apparent race (optional)</Label>
            <Input value={form.race} onChange={(e) => setForm((f) => ({ ...f, race: e.target.value }))} maxLength={60} className="mt-1 bg-black/30 border-purple-500/40 text-white" />
          </div>
          <div>
            <Label className="text-gray-300 text-xs">Pretended background (optional)</Label>
            <Textarea value={form.background} onChange={(e) => setForm((f) => ({ ...f, background: e.target.value }))} maxLength={600} rows={3} className="mt-1 bg-black/30 border-purple-500/40 text-white" data-testid="persona-bg-input" />
          </div>
          <div className="flex gap-2 justify-end">
            {persona && <Button type="button" variant="outline" onClick={() => setEditing(false)}>Cancel</Button>}
            <Button type="submit" className="bg-purple-700 hover:bg-purple-600" data-testid="persona-save-btn">Save Persona</Button>
          </div>
        </div>
      </form>
    );
  }

  return (
    <div data-testid="persona-view" className={`p-4 rounded-xl border ${persona.active ? 'border-emerald-500/40 bg-emerald-900/15' : 'border-gray-700/40 bg-black/20'}`}>
      <div className="flex items-start justify-between gap-2 mb-3">
        <div>
          <p className="text-xs uppercase tracking-widest text-gray-400">Persona</p>
          <h4 className="text-xl font-bold text-purple-200">{persona.name}</h4>
          {persona.race && <p className="text-sm text-gray-300">{persona.race}</p>}
        </div>
        <span className={`text-xs px-2 py-1 rounded-full uppercase tracking-widest font-bold ${persona.active ? 'bg-emerald-700/40 text-emerald-100' : 'bg-gray-700/40 text-gray-300'}`}>
          {persona.active ? 'Worn' : 'Set aside'}
        </span>
      </div>
      {persona.background && <p className="text-gray-300 italic mb-3">{persona.background}</p>}
      <div className="flex gap-2 flex-wrap">
        <Button size="sm" onClick={handleToggle} className={persona.active ? 'bg-gray-700 hover:bg-gray-600' : 'bg-emerald-700 hover:bg-emerald-600'} data-testid="persona-toggle-btn">
          {persona.active ? <><EyeOff className="w-4 h-4 mr-1" /> Drop disguise</> : <><Eye className="w-4 h-4 mr-1" /> Wear disguise</>}
        </Button>
        <Button size="sm" variant="outline" onClick={() => setEditing(true)} data-testid="persona-edit-btn">Edit</Button>
        <Button size="sm" variant="outline" onClick={handleDrop} className="border-red-500/50 text-red-300 hover:bg-red-500/20" data-testid="persona-forget-btn">
          <Trash2 className="w-4 h-4 mr-1" /> Forget
        </Button>
      </div>
    </div>
  );
};

export default MysteryIdentityPanel;
