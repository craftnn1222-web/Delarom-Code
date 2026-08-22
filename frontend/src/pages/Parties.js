import React, { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { Loader2, Plus, Sparkles, Users, MapPin, ScrollText } from 'lucide-react';
import api from '../utils/api';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Textarea } from '../components/ui/textarea';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../components/ui/dialog';

const STATUS_BADGE = {
  recruiting: { label: 'Recruiting', className: 'bg-emerald-950/60 border-emerald-500/40 text-emerald-200' },
  active:     { label: 'In session', className: 'bg-amber-950/60 border-amber-500/40 text-amber-200' },
  finished:   { label: 'Ended',      className: 'bg-stone-800/60 border-stone-500/40 text-stone-300' },
};

const Parties = () => {
  const navigate = useNavigate();
  const [parties, setParties] = useState([]);
  const [myParties, setMyParties] = useState([]);
  const [characters, setCharacters] = useState([]);
  const [loading, setLoading] = useState(true);
  const [openCreate, setOpenCreate] = useState(false);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({
    name: '',
    location: '',
    scene_description: '',
    host_character_id: '',
    max_members: 6,
  });

  const refresh = async () => {
    try {
      const [pRes, mineRes, cRes] = await Promise.all([
        api.get('/parties').catch(() => ({ data: [] })),
        api.get('/parties/mine').catch(() => ({ data: [] })),
        api.get('/characters').catch(() => ({ data: [] })),
      ]);
      setParties(Array.isArray(pRes.data) ? pRes.data : []);
      setMyParties(Array.isArray(mineRes.data) ? mineRes.data : []);
      const chars = Array.isArray(cRes.data) ? cRes.data : (cRes.data?.characters || []);
      setCharacters(chars);
      setForm((f) => (
        !f.host_character_id && chars[0]?.id ? { ...f, host_character_id: chars[0].id } : f
      ));
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to load parties.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { refresh(); }, []);

  const openIds = useMemo(
    () => new Set(myParties.map((p) => p.id)),
    [myParties],
  );

  const handleCreate = async () => {
    if (!form.name || form.name.trim().length < 3) {
      toast.error('Give the party a name (3+ characters).'); return;
    }
    if (!form.location || form.location.trim().length < 2) {
      toast.error('Where does this party happen?'); return;
    }
    if (!form.scene_description || form.scene_description.trim().length < 20) {
      toast.error('Describe the opening scene (20+ characters).'); return;
    }
    if (!form.host_character_id) {
      toast.error('Pick which character you\'re playing as.'); return;
    }
    if (creating) return;
    setCreating(true);
    try {
      const r = await api.post('/parties', {
        name: form.name.trim(),
        location: form.location.trim(),
        scene_description: form.scene_description.trim(),
        host_character_id: form.host_character_id,
        max_members: Number(form.max_members) || 6,
      });
      setOpenCreate(false);
      setForm({ name: '', location: '', scene_description: '', host_character_id: characters[0]?.id || '', max_members: 6 });
      toast.success('Party created — invite your friends by sharing the link.');
      navigate(`/parties/${r.data.id}`);
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Could not create the party.');
    } finally {
      setCreating(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center text-stone-300 bg-black">
        <Loader2 className="w-6 h-6 mr-2 animate-spin" />
        Gathering the party board…
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-zinc-950 via-stone-950 to-black text-stone-100">
      <div className="max-w-5xl mx-auto px-6 py-12">
        <div className="mb-10 flex flex-wrap items-start justify-between gap-4">
          <div>
            <Link to="/dashboard" className="text-sm text-stone-400 hover:text-stone-200 transition" data-testid="parties-back-link">
              ← Dashboard
            </Link>
            <h1 className="mt-4 text-4xl sm:text-5xl font-bold tracking-tight flex items-center gap-3">
              <Users className="w-10 h-10 text-amber-300" />
              <span>Party Quests</span>
            </h1>
            <p className="mt-3 text-stone-400 max-w-3xl">
              Gather a small circle of friends for a shared RP session. One
              player hosts, sets the scene, and starts the story — after
              that, the Master of Ceremonies narrates each turn while the
              party takes it in turns to act.
            </p>
          </div>
          <Button
            onClick={() => setOpenCreate(true)}
            className="bg-gradient-to-r from-amber-700 to-stone-700 hover:from-amber-800 hover:to-stone-800 text-stone-100"
            data-testid="open-create-party-btn"
          >
            <Plus className="w-4 h-4 mr-2" />
            Host a Party
          </Button>
        </div>

        {myParties.length > 0 && (
          <div className="mb-10">
            <h2 className="text-lg font-semibold mb-3 text-stone-200 flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-amber-300" />
              Your Parties
            </h2>
            <div className="grid sm:grid-cols-2 gap-4" data-testid="my-parties-list">
              {myParties.map((p) => (
                <PartyCard key={p.id} party={p} showMine />
              ))}
            </div>
          </div>
        )}

        <div>
          <h2 className="text-lg font-semibold mb-3 text-stone-200 flex items-center gap-2">
            <ScrollText className="w-4 h-4 text-stone-400" />
            Open Parties
          </h2>
          {parties.length === 0 ? (
            <div className="rounded-xl border border-stone-700/60 bg-stone-950/40 p-8 text-center text-stone-400">
              No parties are open right now. Host the first one!
            </div>
          ) : (
            <div className="grid sm:grid-cols-2 gap-4" data-testid="open-parties-list">
              {parties.map((p) => (
                <PartyCard key={p.id} party={p} showJoined={openIds.has(p.id)} />
              ))}
            </div>
          )}
        </div>
      </div>

      <Dialog open={openCreate} onOpenChange={setOpenCreate}>
        <DialogContent
          className="bg-stone-950 border-stone-700 text-stone-100 max-w-lg"
          data-testid="create-party-dialog"
        >
          <DialogHeader>
            <DialogTitle className="text-2xl text-amber-200">
              Host a Party
            </DialogTitle>
            <DialogDescription className="text-stone-400">
              Set the scene, name the party, and invite your friends.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <div>
              <label className="text-sm text-stone-400">Party Name</label>
              <Input
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                maxLength={120}
                placeholder="e.g. Last Lantern in Selincoast"
                className="bg-stone-900 border-stone-700 text-stone-100"
                data-testid="party-name-input"
              />
            </div>
            <div>
              <label className="text-sm text-stone-400">Location</label>
              <Input
                value={form.location}
                onChange={(e) => setForm({ ...form, location: e.target.value })}
                maxLength={160}
                placeholder="e.g. Selincoast Docks, Selindori"
                className="bg-stone-900 border-stone-700 text-stone-100"
                data-testid="party-location-input"
              />
            </div>
            <div>
              <label className="text-sm text-stone-400">Opening Scene</label>
              <Textarea
                value={form.scene_description}
                onChange={(e) => setForm({ ...form, scene_description: e.target.value })}
                maxLength={1500}
                rows={4}
                placeholder="Describe the moment we begin — where, when, and what's happening around the party…"
                className="bg-stone-900 border-stone-700 text-stone-100"
                data-testid="party-scene-input"
              />
              <div className="text-xs text-stone-500 mt-1">
                {form.scene_description.length}/1500
              </div>
            </div>
            <div>
              <label className="text-sm text-stone-400">Play as</label>
              {characters.length === 0 ? (
                <div className="text-sm text-stone-500 italic">
                  Create a character first to host a party.
                </div>
              ) : (
                <select
                  value={form.host_character_id}
                  onChange={(e) => setForm({ ...form, host_character_id: e.target.value })}
                  className="w-full bg-stone-900 border border-stone-700 rounded-md px-3 py-2 text-stone-100"
                  data-testid="party-host-character-select"
                >
                  {characters.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name} — {c.race}{c.character_class ? ` (${c.character_class})` : ''}
                    </option>
                  ))}
                </select>
              )}
            </div>
            <div>
              <label className="text-sm text-stone-400">Max party size (2-8)</label>
              <Input
                type="number"
                min={2}
                max={8}
                value={form.max_members}
                onChange={(e) => setForm({ ...form, max_members: e.target.value })}
                className="bg-stone-900 border-stone-700 text-stone-100"
                data-testid="party-max-members-input"
              />
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="ghost"
              onClick={() => setOpenCreate(false)}
              className="text-stone-300 hover:text-stone-100"
              data-testid="cancel-create-party-btn"
            >
              Cancel
            </Button>
            <Button
              onClick={handleCreate}
              disabled={creating || characters.length === 0}
              className="bg-gradient-to-r from-amber-700 to-stone-700 hover:from-amber-800 hover:to-stone-800 text-stone-100"
              data-testid="submit-create-party-btn"
            >
              {creating ? (
                <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Creating…</>
              ) : (
                <><Plus className="w-4 h-4 mr-2" /> Host Party</>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

const PartyCard = ({ party, showMine = false, showJoined = false }) => {
  const badge = STATUS_BADGE[party.status] || STATUS_BADGE.finished;
  return (
    <Link
      to={`/parties/${party.id}`}
      className="block rounded-xl border border-stone-700/60 bg-stone-950/60 p-4 hover:bg-stone-900/60 hover:border-amber-700/40 transition"
      data-testid={`party-card-${party.id}`}
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        <h3 className="text-lg font-semibold text-stone-100 line-clamp-1">{party.name}</h3>
        <span className={`text-[10px] uppercase tracking-widest rounded border px-2 py-0.5 ${badge.className}`}>
          {badge.label}
        </span>
      </div>
      <div className="text-xs text-stone-400 flex items-center gap-1.5 mb-2">
        <MapPin className="w-3 h-3" />
        <span className="line-clamp-1">{party.location}</span>
      </div>
      <p className="text-sm text-stone-300/90 line-clamp-3 italic mb-3">
        {party.scene_description}
      </p>
      <div className="text-xs text-stone-500 flex items-center justify-between">
        <span>
          {party.members?.length || 0}/{party.max_members} members
        </span>
        {(showMine || showJoined) && (
          <span className="text-amber-300/80">
            {showMine ? 'You\'re in' : 'Joined'}
          </span>
        )}
      </div>
    </Link>
  );
};

export default Parties;
