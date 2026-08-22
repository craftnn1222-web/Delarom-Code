import React, { useEffect, useState, useCallback } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Textarea } from './ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from './ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from './ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { Users, Flame, Plus, Trash2, RotateCcw, Edit2 } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const STATUS_OPTIONS = ['alive', 'wounded', 'dead', 'fled', 'missing'];
const IMPORTANCE_OPTIONS = ['commoner', 'notable', 'noble', 'ruler', 'monarch'];
const INTENSITY_OPTIONS = ['mild', 'moderate', 'severe', 'epic'];
const EVENT_STATUS_OPTIONS = ['active', 'resolved', 'decayed'];

const authHeader = () => ({
  // Bearer token is injected globally by axios interceptor in utils/api.js.
  // No withCredentials — production proxy rewrites CORS origin to '*' which
  // forbids credentials-include mode.
});

const emptyNpcDraft = {
  name: '',
  race: '',
  role: '',
  appearance: '',
  personality: '',
  motivation: '',
  background: '',
  quirks: '',
  importance: 'commoner',
  status: 'alive',
  status_note: '',
  mood_score: 0,
};

const emptyEventDraft = {
  event_type: 'incident',
  summary: '',
  description: '',
  intensity: 'moderate',
};

const AdminNPCManager = () => {
  // Scope = 'location' (browse by nation/location) or 'faction' (browse by faction).
  // The original UI required typing nation+location slugs from memory, which is
  // why seeded NPCs like Orion (a faction member) and the royals/masters were
  // invisible to admins. Now backed by /api/admin/npc-scopes which lists every
  // bucket that actually contains NPCs.
  const [scope, setScope] = useState('location');
  const [nation, setNation] = useState('');
  const [location, setLocation] = useState('');
  const [factionSlug, setFactionSlug] = useState('');
  const [scopes, setScopes] = useState({ locations: [], factions: [] });
  const [search, setSearch] = useState('');
  const [npcs, setNpcs] = useState([]);
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(false);
  const [npcDialog, setNpcDialog] = useState({ open: false, mode: 'create', draft: emptyNpcDraft, id: null });
  const [eventDialog, setEventDialog] = useState({ open: false, draft: emptyEventDraft });
  const [memoriesDialog, setMemoriesDialog] = useState({ open: false, npc: null, relationships: [] });

  // Fetch the list of every (nation, location) bucket and every faction that
  // has NPCs in it. Cheap: just an aggregate over a few thousand docs.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const r = await axios.get(`${BACKEND_URL}/api/admin/npc-scopes`, authHeader());
        if (!cancelled) setScopes(r.data || { locations: [], factions: [] });
      } catch (err) {
        console.error('Failed to load NPC scopes:', err);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  // Unique nations present in the scope data (for the cascading nation→location pickers).
  const availableNations = Array.from(
    new Set((scopes.locations || []).map((b) => b.nation).filter(Boolean))
  ).sort();
  const availableLocations = (scopes.locations || [])
    .filter((b) => !nation || b.nation === nation)
    .filter((b) => b.location)
    .sort((a, b) => a.location.localeCompare(b.location));

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      if (scope === 'faction' && factionSlug) {
        const r = await axios.get(
          `${BACKEND_URL}/api/admin/faction-npcs?faction_slug=${encodeURIComponent(factionSlug)}`,
          authHeader(),
        );
        setNpcs(r.data || []);
        setEvents([]);
      } else if (scope === 'location' && nation && location) {
        const [npcsRes, eventsRes] = await Promise.all([
          axios.get(`${BACKEND_URL}/api/admin/npcs?nation=${nation}&location=${location}&include_factions=false`, authHeader()),
          axios.get(`${BACKEND_URL}/api/admin/scene-events?nation=${nation}&location=${location}`, authHeader()),
        ]);
        setNpcs(npcsRes.data || []);
        setEvents(eventsRes.data || []);
      } else if (scope === 'all') {
        // Unified — pull every visible NPC (location + faction) for a single
        // searchable list. Capped at 2000 rows server-side.
        const r = await axios.get(`${BACKEND_URL}/api/admin/npcs?include_factions=true`, authHeader());
        setNpcs(r.data || []);
        setEvents([]);
      } else {
        setNpcs([]);
        setEvents([]);
      }
    } catch (_err) {
      toast.error('Failed to load NPCs / events');
    } finally {
      setLoading(false);
    }
  }, [scope, nation, location, factionSlug]);

  useEffect(() => { loadData(); }, [loadData]);

  // Free-text filter applied client-side to whatever NPCs the scope loaded.
  const filteredNpcs = (() => {
    const q = search.trim().toLowerCase();
    if (!q) return npcs;
    return npcs.filter((n) => {
      const hay = `${n.name || ''} ${n.role || ''} ${n.race || ''} ${n.location || ''} ${n.faction_name || ''}`.toLowerCase();
      return hay.includes(q);
    });
  })();

  // ---------- NPC handlers ----------
  const openCreateNpc = () => {
    if (!nation || !location) {
      toast.error('Enter nation slug and location slug first');
      return;
    }
    setNpcDialog({ open: true, mode: 'create', draft: emptyNpcDraft, id: null });
  };

  const openEditNpc = (npc) => {
    setNpcDialog({
      open: true,
      mode: 'edit',
      id: npc.id,
      draft: {
        name: npc.name || '',
        race: npc.race || '',
        role: npc.role || '',
        appearance: npc.appearance || '',
        personality: npc.personality || '',
        motivation: npc.motivation || '',
        background: npc.background || '',
        quirks: npc.quirks || '',
        importance: npc.importance || 'commoner',
        status: npc.status || 'alive',
        status_note: npc.status_note || '',
        mood_score: npc.mood_score || 0,
      },
    });
  };

  const saveNpc = async () => {
    const { mode, id, draft } = npcDialog;
    if (!draft.name.trim()) {
      toast.error('NPC name required');
      return;
    }
    try {
      if (mode === 'create') {
        await axios.post(
          `${BACKEND_URL}/api/admin/npcs/${nation}/${location}`,
          { ...draft, mood_score: parseInt(draft.mood_score, 10) || 0 },
          authHeader()
        );
        toast.success('NPC created');
      } else {
        await axios.patch(
          `${BACKEND_URL}/api/admin/npcs/${id}`,
          { ...draft, mood_score: parseInt(draft.mood_score, 10) || 0 },
          authHeader()
        );
        toast.success('NPC updated');
      }
      setNpcDialog({ open: false, mode: 'create', draft: emptyNpcDraft, id: null });
      loadData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Save failed');
    }
  };

  const deleteNpc = async (npc) => {
    if (!window.confirm(`Delete NPC "${npc.name}"? All relationships with this NPC will also be erased.`)) return;
    try {
      await axios.delete(`${BACKEND_URL}/api/admin/npcs/${npc.id}`, authHeader());
      toast.success('NPC deleted');
      loadData();
    } catch (_err) {
      toast.error('Delete failed');
    }
  };

  const resetNpcMemory = async (npc) => {
    if (!window.confirm(`Reset all of ${npc.name}'s memories and reset their mood to neutral?`)) return;
    try {
      await axios.post(`${BACKEND_URL}/api/admin/npcs/${npc.id}/reset-memory`, {}, authHeader());
      toast.success('Memories cleared');
      loadData();
    } catch (_err) {
      toast.error('Reset failed');
    }
  };

  const viewRelationships = async (npc) => {
    try {
      const res = await axios.get(`${BACKEND_URL}/api/admin/npcs/${npc.id}/relationships`, authHeader());
      setMemoriesDialog({ open: true, npc, relationships: res.data || [] });
    } catch (_err) {
      toast.error('Failed to load relationships');
    }
  };

  // ---------- Event handlers ----------
  const openCreateEvent = () => {
    if (!nation || !location) {
      toast.error('Enter nation slug and location slug first');
      return;
    }
    setEventDialog({ open: true, draft: emptyEventDraft });
  };

  const saveEvent = async () => {
    const { draft } = eventDialog;
    if (!draft.summary.trim()) {
      toast.error('Event summary required');
      return;
    }
    try {
      await axios.post(`${BACKEND_URL}/api/admin/scene-events/${nation}/${location}`, draft, authHeader());
      toast.success('Event created');
      setEventDialog({ open: false, draft: emptyEventDraft });
      loadData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Save failed');
    }
  };

  const setEventStatus = async (ev, status) => {
    let resolution_note = null;
    if (status !== 'active') {
      resolution_note = window.prompt('Optional resolution note?', '') || null;
    }
    try {
      await axios.patch(`${BACKEND_URL}/api/admin/scene-events/${ev.id}/status`, { status, resolution_note }, authHeader());
      toast.success(`Event marked ${status}`);
      loadData();
    } catch (_err) {
      toast.error('Update failed');
    }
  };

  const deleteEvent = async (ev) => {
    if (!window.confirm('Delete this event permanently?')) return;
    try {
      await axios.delete(`${BACKEND_URL}/api/admin/scene-events/${ev.id}`, authHeader());
      toast.success('Event deleted');
      loadData();
    } catch (_err) {
      toast.error('Delete failed');
    }
  };

  // ---------- Render ----------
  return (
    <div className="space-y-6" data-testid="npc-manager">
      {/* Scope-aware filter bar. Three modes:
            location  — cascading nation→location dropdowns
            faction   — single faction dropdown
            all       — unified everything (capped at 2000 rows server-side)
          plus a free-text search applied to whatever's loaded. */}
      <div className="glass-dark p-4 rounded-xl space-y-3">
        <div className="flex flex-wrap items-end gap-3">
          <div>
            <Label className="text-purple-300 text-xs uppercase">Browse</Label>
            <select
              value={scope}
              onChange={(e) => {
                setScope(e.target.value);
                setNation(''); setLocation(''); setFactionSlug('');
              }}
              className="mt-1 w-44 bg-black/30 border border-purple-500/30 text-white rounded-md px-3 py-2 text-sm"
              data-testid="npc-scope-select"
            >
              <option value="location" className="bg-gray-900">By Location</option>
              <option value="faction" className="bg-gray-900">By Faction</option>
              <option value="all" className="bg-gray-900">All NPCs (unified)</option>
            </select>
          </div>

          {scope === 'location' && (
            <>
              <div className="flex-1 min-w-[180px]">
                <Label className="text-purple-300 text-xs uppercase">Nation</Label>
                <select
                  value={nation}
                  onChange={(e) => { setNation(e.target.value); setLocation(''); }}
                  className="mt-1 w-full bg-black/30 border border-purple-500/30 text-white rounded-md px-3 py-2 text-sm"
                  data-testid="npc-nation-select"
                >
                  <option value="">— pick a nation —</option>
                  {availableNations.map((n) => (
                    <option key={n} value={n} className="bg-gray-900">{n}</option>
                  ))}
                </select>
              </div>
              <div className="flex-1 min-w-[200px]">
                <Label className="text-purple-300 text-xs uppercase">Location</Label>
                <select
                  value={location}
                  onChange={(e) => setLocation(e.target.value)}
                  disabled={!nation}
                  className="mt-1 w-full bg-black/30 border border-purple-500/30 text-white rounded-md px-3 py-2 text-sm disabled:opacity-50"
                  data-testid="npc-location-select"
                >
                  <option value="">— pick a location —</option>
                  {availableLocations.map((b) => (
                    <option key={`${b.nation}/${b.location}`} value={b.location} className="bg-gray-900">
                      {b.location} ({b.count})
                    </option>
                  ))}
                </select>
              </div>
            </>
          )}

          {scope === 'faction' && (
            <div className="flex-1 min-w-[260px]">
              <Label className="text-purple-300 text-xs uppercase">Faction</Label>
              <select
                value={factionSlug}
                onChange={(e) => setFactionSlug(e.target.value)}
                className="mt-1 w-full bg-black/30 border border-purple-500/30 text-white rounded-md px-3 py-2 text-sm"
                data-testid="npc-faction-select"
              >
                <option value="">— pick a faction —</option>
                {(scopes.factions || []).map((f) => (
                  <option key={f.slug} value={f.slug} className="bg-gray-900">
                    {f.name} ({f.count})
                  </option>
                ))}
              </select>
            </div>
          )}

          <div className="flex-1 min-w-[220px]">
            <Label className="text-purple-300 text-xs uppercase">Search</Label>
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="name, role, race…"
              className="bg-black/30 border-purple-500/30 text-white"
              data-testid="npc-search-input"
            />
          </div>
        </div>
        <p className="text-xs text-gray-500">
          {scope === 'location' && (!nation || !location)
            ? 'Pick a nation and location to load NPCs.'
            : scope === 'faction' && !factionSlug
              ? 'Pick a faction to list its members.'
              : `${filteredNpcs.length} NPC${filteredNpcs.length === 1 ? '' : 's'} loaded.`}
        </p>
      </div>

      <Tabs defaultValue="npcs" className="space-y-4">
        <TabsList className="bg-gray-900/50 border border-purple-500/30">
          <TabsTrigger value="npcs" className="data-[state=active]:bg-purple-600">
            <Users className="w-4 h-4 mr-2" /> Persistent NPCs ({filteredNpcs.length})
          </TabsTrigger>
          <TabsTrigger value="events" className="data-[state=active]:bg-amber-600">
            <Flame className="w-4 h-4 mr-2" /> Scene Events ({events.length})
          </TabsTrigger>
        </TabsList>

        <TabsContent value="npcs" className="space-y-3">
          <div className="flex justify-end">
            <Button onClick={openCreateNpc} className="bg-purple-600 hover:bg-purple-700" data-testid="npc-create-btn">
              <Plus className="w-4 h-4 mr-2" /> New NPC
            </Button>
          </div>
          {filteredNpcs.length === 0 ? (
            <p className="text-gray-400 text-center py-8">
              {loading ? 'Loading…' : 'No NPCs match the current scope.'}
            </p>
          ) : (
            <div className="grid md:grid-cols-2 gap-3">
              {filteredNpcs.map((npc) => (
                <div key={npc.id} className="glass-dark p-4 rounded-xl border border-purple-500/20" data-testid={`npc-card-${npc.id}`}>
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <h4 className="text-lg font-bold text-white">
                        {npc.name}
                        <span className="ml-2 text-xs text-gray-400 font-normal">{npc.race || ''}{npc.race && npc.role ? ' • ' : ''}{npc.role || ''}</span>
                      </h4>
                      <p className="text-xs text-gray-500">
                        {npc.kind === 'faction' ? (
                          <>Faction: <span className="text-purple-300">{npc.faction_name || npc.faction_slug}</span> • Rank: <span className="capitalize">{npc.importance || 'member'}</span></>
                        ) : (
                          <>
                            {npc.nation && npc.location && <>At: <span className="text-purple-300">{npc.nation}/{npc.location}</span> • </>}
                            Tier: <span className="capitalize">{npc.importance || 'commoner'}</span> • Mood: <span className="capitalize">{npc.overall_mood}</span> ({npc.mood_score >= 0 ? '+' : ''}{npc.mood_score}) • Status: {npc.status}
                            {npc.is_admin_seeded ? ' • admin-seeded' : ''}
                          </>
                        )}
                      </p>
                    </div>
                  </div>
                  <p className="text-sm text-gray-300 mt-2 line-clamp-3">{npc.personality}</p>
                  <div className="flex flex-wrap gap-2 mt-3">
                    <Button size="sm" variant="outline" onClick={() => openEditNpc(npc)} data-testid={`npc-edit-${npc.id}`}>
                      <Edit2 className="w-3 h-3 mr-1" /> Edit
                    </Button>
                    <Button size="sm" variant="outline" onClick={() => viewRelationships(npc)} data-testid={`npc-relationships-${npc.id}`}>
                      Relationships
                    </Button>
                    <Button size="sm" variant="outline" onClick={() => resetNpcMemory(npc)} data-testid={`npc-reset-${npc.id}`}>
                      <RotateCcw className="w-3 h-3 mr-1" /> Reset memory
                    </Button>
                    <Button size="sm" variant="destructive" onClick={() => deleteNpc(npc)} data-testid={`npc-delete-${npc.id}`}>
                      <Trash2 className="w-3 h-3 mr-1" /> Delete
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="events" className="space-y-3">
          <div className="flex justify-end">
            <Button onClick={openCreateEvent} className="bg-amber-600 hover:bg-amber-700" data-testid="event-create-btn">
              <Plus className="w-4 h-4 mr-2" /> New Event
            </Button>
          </div>
          {events.length === 0 ? (
            <p className="text-gray-400 text-center py-8">
              {nation && location ? 'No scene events in this location yet.' : 'Enter a nation and location slug above and click Load.'}
            </p>
          ) : (
            <div className="space-y-2">
              {events.map((ev) => (
                <div key={ev.id} className="glass-dark p-4 rounded-xl border border-amber-500/20" data-testid={`event-card-${ev.id}`}>
                  <div className="flex items-start justify-between gap-3 flex-wrap">
                    <div>
                      <p className="text-amber-200 font-semibold">
                        [{ev.event_type}] {ev.summary}
                      </p>
                      <p className="text-xs text-gray-400 mt-1">
                        Intensity: {ev.intensity} • Status: {ev.status} • Started: {new Date(ev.started_at).toLocaleString()}
                      </p>
                      {ev.description && <p className="text-sm text-gray-300 mt-2">{ev.description}</p>}
                      {ev.resolution_note && (
                        <p className="text-xs text-gray-500 mt-1">Resolution: {ev.resolution_note}</p>
                      )}
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {ev.status === 'active' && (
                        <>
                          <Button size="sm" variant="outline" onClick={() => setEventStatus(ev, 'resolved')} data-testid={`event-resolve-${ev.id}`}>
                            Resolve
                          </Button>
                          <Button size="sm" variant="outline" onClick={() => setEventStatus(ev, 'decayed')} data-testid={`event-decay-${ev.id}`}>
                            Decay
                          </Button>
                        </>
                      )}
                      {ev.status !== 'active' && (
                        <Button size="sm" variant="outline" onClick={() => setEventStatus(ev, 'active')} data-testid={`event-reactivate-${ev.id}`}>
                          Reactivate
                        </Button>
                      )}
                      <Button size="sm" variant="destructive" onClick={() => deleteEvent(ev)} data-testid={`event-delete-${ev.id}`}>
                        <Trash2 className="w-3 h-3" />
                      </Button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </TabsContent>
      </Tabs>

      {/* NPC create/edit dialog */}
      <Dialog open={npcDialog.open} onOpenChange={(open) => setNpcDialog((d) => ({ ...d, open }))}>
        <DialogContent
          className="bg-gray-900 border-purple-500/30 max-w-2xl max-h-[90vh] overflow-y-auto"
          onPointerDownOutside={(e) => e.preventDefault()}
          onInteractOutside={(e) => e.preventDefault()}
        >
          <DialogHeader>
            <DialogTitle className="text-white">
              {npcDialog.mode === 'create' ? 'New persistent NPC' : `Edit ${npcDialog.draft.name}`}
            </DialogTitle>
          </DialogHeader>
          <div className="grid grid-cols-2 gap-3">
            {['name', 'race', 'role'].map((field) => (
              <div key={field}>
                <Label className="text-purple-300 capitalize">{field}</Label>
                <Input
                  value={npcDialog.draft[field]}
                  onChange={(e) =>
                    setNpcDialog((d) => ({ ...d, draft: { ...d.draft, [field]: e.target.value } }))
                  }
                  className="bg-black/30 border-purple-500/30 text-white"
                  data-testid={`npc-form-${field}`}
                />
              </div>
            ))}
            <div>
              <Label className="text-purple-300">Status</Label>
              <Select
                value={npcDialog.draft.status}
                onValueChange={(v) => setNpcDialog((d) => ({ ...d, draft: { ...d.draft, status: v } }))}
              >
                <SelectTrigger className="bg-black/30 border-purple-500/30 text-white" data-testid="npc-form-status">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {STATUS_OPTIONS.map((s) => (
                    <SelectItem key={s} value={s} className="capitalize">{s}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label className="text-purple-300">Importance tier</Label>
              <Select
                value={npcDialog.draft.importance}
                onValueChange={(v) => setNpcDialog((d) => ({ ...d, draft: { ...d.draft, importance: v } }))}
              >
                <SelectTrigger className="bg-black/30 border-purple-500/30 text-white" data-testid="npc-form-importance">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {IMPORTANCE_OPTIONS.map((s) => (
                    <SelectItem key={s} value={s} className="capitalize">{s}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label className="text-purple-300">Mood score (-100 … 100)</Label>
              <Input
                type="number"
                value={npcDialog.draft.mood_score}
                onChange={(e) => setNpcDialog((d) => ({ ...d, draft: { ...d.draft, mood_score: e.target.value } }))}
                className="bg-black/30 border-purple-500/30 text-white"
                data-testid="npc-form-mood"
              />
            </div>
            <div>
              <Label className="text-purple-300">Status note</Label>
              <Input
                value={npcDialog.draft.status_note}
                onChange={(e) => setNpcDialog((d) => ({ ...d, draft: { ...d.draft, status_note: e.target.value } }))}
                className="bg-black/30 border-purple-500/30 text-white"
                data-testid="npc-form-status-note"
              />
            </div>
            {['appearance', 'personality', 'motivation', 'background', 'quirks'].map((field) => (
              <div key={field} className="col-span-2">
                <Label className="text-purple-300 capitalize">{field}</Label>
                <Textarea
                  value={npcDialog.draft[field]}
                  onChange={(e) => setNpcDialog((d) => ({ ...d, draft: { ...d.draft, [field]: e.target.value } }))}
                  className="bg-black/30 border-purple-500/30 text-white min-h-[60px]"
                  data-testid={`npc-form-${field}`}
                />
              </div>
            ))}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setNpcDialog((d) => ({ ...d, open: false }))}>Cancel</Button>
            <Button onClick={saveNpc} className="bg-purple-600 hover:bg-purple-700" data-testid="npc-save-btn">
              Save
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Event create dialog */}
      <Dialog open={eventDialog.open} onOpenChange={(open) => setEventDialog((d) => ({ ...d, open }))}>
        <DialogContent
          className="bg-gray-900 border-amber-500/30 max-w-xl"
          onPointerDownOutside={(e) => e.preventDefault()}
          onInteractOutside={(e) => e.preventDefault()}
        >
          <DialogHeader>
            <DialogTitle className="text-white">New scene event</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <div>
              <Label className="text-amber-300">Type</Label>
              <Input
                value={eventDialog.draft.event_type}
                onChange={(e) => setEventDialog((d) => ({ ...d, draft: { ...d.draft, event_type: e.target.value } }))}
                placeholder="brawl, festival, fire, mystery…"
                className="bg-black/30 border-amber-500/30 text-white"
                data-testid="event-form-type"
              />
            </div>
            <div>
              <Label className="text-amber-300">Intensity</Label>
              <Select
                value={eventDialog.draft.intensity}
                onValueChange={(v) => setEventDialog((d) => ({ ...d, draft: { ...d.draft, intensity: v } }))}
              >
                <SelectTrigger className="bg-black/30 border-amber-500/30 text-white" data-testid="event-form-intensity">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {INTENSITY_OPTIONS.map((i) => (
                    <SelectItem key={i} value={i} className="capitalize">{i}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label className="text-amber-300">Summary</Label>
              <Input
                value={eventDialog.draft.summary}
                onChange={(e) => setEventDialog((d) => ({ ...d, draft: { ...d.draft, summary: e.target.value } }))}
                className="bg-black/30 border-amber-500/30 text-white"
                placeholder="A bar brawl has broken out"
                data-testid="event-form-summary"
              />
            </div>
            <div>
              <Label className="text-amber-300">Description</Label>
              <Textarea
                value={eventDialog.draft.description}
                onChange={(e) => setEventDialog((d) => ({ ...d, draft: { ...d.draft, description: e.target.value } }))}
                className="bg-black/30 border-amber-500/30 text-white min-h-[80px]"
                placeholder="Vivid details for the AI to weave into responses…"
                data-testid="event-form-description"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEventDialog((d) => ({ ...d, open: false }))}>Cancel</Button>
            <Button onClick={saveEvent} className="bg-amber-600 hover:bg-amber-700" data-testid="event-save-btn">
              Save
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Relationships dialog */}
      <Dialog open={memoriesDialog.open} onOpenChange={(open) => setMemoriesDialog((d) => ({ ...d, open }))}>
        <DialogContent className="bg-gray-900 border-purple-500/30 max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-white">
              {memoriesDialog.npc ? `${memoriesDialog.npc.name}'s relationships` : 'Relationships'}
            </DialogTitle>
          </DialogHeader>
          {memoriesDialog.relationships.length === 0 ? (
            <p className="text-gray-400 text-sm">No-one has interacted with this NPC yet.</p>
          ) : (
            <div className="space-y-3">
              {memoriesDialog.relationships.map((rel) => (
                <div key={rel.id} className="p-3 rounded-lg bg-black/30 border border-purple-500/20">
                  <p className="text-white font-semibold">
                    {rel.character_name || rel.character_id}
                    <span className="ml-2 text-xs text-gray-400 capitalize">
                      ({rel.relationship_label}, {rel.relationship_score >= 0 ? '+' : ''}{rel.relationship_score})
                    </span>
                  </p>
                  <p className="text-xs text-gray-500">{rel.interaction_count} interactions</p>
                  {rel.memories?.length > 0 && (
                    <ul className="mt-2 list-disc list-inside text-sm text-gray-300 space-y-1">
                      {rel.memories.map((m) => (
                        <li key={m.id || `${m.text}-${m.created_at || ''}`}>{m.text}</li>
                      ))}
                    </ul>
                  )}
                </div>
              ))}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

// Suppress unused-warning for constants tied to the API contract
const _kept = EVENT_STATUS_OPTIONS;

export default AdminNPCManager;
