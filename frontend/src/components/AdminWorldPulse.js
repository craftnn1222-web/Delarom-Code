import React, { useEffect, useState, useCallback } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Textarea } from './ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from './ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { Globe, History, Send, Plus, Swords } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const authHeader = () => ({
  // Bearer token is injected globally by axios interceptor in utils/api.js.
  // No withCredentials — production proxy rewrites CORS origin to '*' which
  // forbids credentials-include mode.
});

const NATIONS = ['ammeonon', 'selindori', 'dhor-kuldor', 'aigraels'];

const STANCE_COLOR = {
  war: 'bg-red-700/30 text-red-200 border-red-700/40',
  cold_war: 'bg-orange-700/30 text-orange-200 border-orange-700/40',
  tense: 'bg-amber-700/30 text-amber-200 border-amber-700/40',
  neutral: 'bg-gray-700/30 text-gray-200 border-gray-700/40',
  friendly: 'bg-emerald-700/30 text-emerald-200 border-emerald-700/40',
  alliance: 'bg-blue-700/30 text-blue-200 border-blue-700/40',
};

const AdminWorldPulse = () => {
  const [relations, setRelations] = useState([]);
  const [worldEvents, setWorldEvents] = useState([]);
  const [cascades, setCascades] = useState([]);
  const [loading, setLoading] = useState(false);

  // Diplomacy editor
  const [diploDraft, setDiploDraft] = useState({ nation_a: 'ammeonon', nation_b: 'selindori', score: 0, reason: '' });
  const [adjustDraft, setAdjustDraft] = useState({ nation_a: 'ammeonon', nation_b: 'selindori', delta: 0, reason: '' });
  const [eventDraft, setEventDraft] = useState({
    event_type: 'royal_decree',
    scope: 'world',
    summary: '',
    details: '',
    nations: '',
  });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [relRes, evRes, casRes] = await Promise.all([
        axios.get(`${BACKEND_URL}/api/admin/diplomacy`, authHeader()),
        axios.get(`${BACKEND_URL}/api/admin/world-events?limit=50`, authHeader()),
        axios.get(`${BACKEND_URL}/api/admin/cascade-queue`, authHeader()),
      ]);
      setRelations(relRes.data || []);
      setWorldEvents(evRes.data || []);
      setCascades(casRes.data || []);
    } catch (_err) {
      toast.error('Failed to load world state');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const setRelation = async () => {
    try {
      await axios.post(`${BACKEND_URL}/api/admin/diplomacy/set`, diploDraft, authHeader());
      toast.success('Relation set');
      load();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed');
    }
  };

  const adjustRelation = async () => {
    try {
      await axios.post(`${BACKEND_URL}/api/admin/diplomacy/adjust`, adjustDraft, authHeader());
      toast.success('Relation adjusted');
      load();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed');
    }
  };

  const createWorldEvent = async () => {
    if (!eventDraft.summary.trim()) {
      toast.error('Summary is required');
      return;
    }
    try {
      const payload = {
        event_type: eventDraft.event_type,
        scope: eventDraft.scope,
        summary: eventDraft.summary,
        details: eventDraft.details,
        nations: eventDraft.nations
          ? eventDraft.nations.split(',').map((s) => s.trim()).filter(Boolean)
          : [],
      };
      await axios.post(`${BACKEND_URL}/api/admin/world-events`, payload, authHeader());
      toast.success('World event recorded');
      setEventDraft({ ...eventDraft, summary: '', details: '' });
      load();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed');
    }
  };

  return (
    <div className="space-y-6" data-testid="world-pulse">
      <Tabs defaultValue="diplomacy" className="space-y-4">
        <TabsList className="bg-gray-900/50 border border-purple-500/30">
          <TabsTrigger value="diplomacy" className="data-[state=active]:bg-purple-600">
            <Globe className="w-4 h-4 mr-2" /> Diplomacy ({relations.length})
          </TabsTrigger>
          <TabsTrigger value="world" className="data-[state=active]:bg-amber-600">
            <History className="w-4 h-4 mr-2" /> World Events ({worldEvents.length})
          </TabsTrigger>
          <TabsTrigger value="cascades" className="data-[state=active]:bg-pink-600">
            <Send className="w-4 h-4 mr-2" /> Pending Cascades ({cascades.length})
          </TabsTrigger>
        </TabsList>

        {/* DIPLOMACY */}
        <TabsContent value="diplomacy" className="space-y-4">
          <div className="grid md:grid-cols-2 gap-4">
            <div className="glass-dark p-4 rounded-xl space-y-3">
              <h4 className="text-white font-semibold flex items-center gap-2">
                <Swords className="w-4 h-4" /> Set relation (overwrites score)
              </h4>
              <div className="grid grid-cols-2 gap-2">
                <NationSelect value={diploDraft.nation_a} onChange={(v) => setDiploDraft({ ...diploDraft, nation_a: v })} testid="diplo-set-a" />
                <NationSelect value={diploDraft.nation_b} onChange={(v) => setDiploDraft({ ...diploDraft, nation_b: v })} testid="diplo-set-b" />
              </div>
              <div>
                <Label className="text-purple-300 text-xs">Score (-100 … 100)</Label>
                <Input
                  type="number"
                  value={diploDraft.score}
                  onChange={(e) => setDiploDraft({ ...diploDraft, score: parseInt(e.target.value, 10) || 0 })}
                  className="bg-black/30 border-purple-500/30 text-white"
                  data-testid="diplo-set-score"
                />
              </div>
              <Input
                value={diploDraft.reason}
                onChange={(e) => setDiploDraft({ ...diploDraft, reason: e.target.value })}
                placeholder="Reason (optional)"
                className="bg-black/30 border-purple-500/30 text-white"
                data-testid="diplo-set-reason"
              />
              <Button onClick={setRelation} className="bg-purple-600 hover:bg-purple-700 w-full" data-testid="diplo-set-btn">Set</Button>
            </div>

            <div className="glass-dark p-4 rounded-xl space-y-3">
              <h4 className="text-white font-semibold">Adjust by delta</h4>
              <div className="grid grid-cols-2 gap-2">
                <NationSelect value={adjustDraft.nation_a} onChange={(v) => setAdjustDraft({ ...adjustDraft, nation_a: v })} testid="diplo-adj-a" />
                <NationSelect value={adjustDraft.nation_b} onChange={(v) => setAdjustDraft({ ...adjustDraft, nation_b: v })} testid="diplo-adj-b" />
              </div>
              <div>
                <Label className="text-purple-300 text-xs">Delta (-40 … +40)</Label>
                <Input
                  type="number"
                  value={adjustDraft.delta}
                  onChange={(e) => setAdjustDraft({ ...adjustDraft, delta: parseInt(e.target.value, 10) || 0 })}
                  className="bg-black/30 border-purple-500/30 text-white"
                  data-testid="diplo-adj-delta"
                />
              </div>
              <Input
                value={adjustDraft.reason}
                onChange={(e) => setAdjustDraft({ ...adjustDraft, reason: e.target.value })}
                placeholder="Reason (optional)"
                className="bg-black/30 border-purple-500/30 text-white"
                data-testid="diplo-adj-reason"
              />
              <Button onClick={adjustRelation} className="bg-purple-600 hover:bg-purple-700 w-full" data-testid="diplo-adj-btn">Apply</Button>
            </div>
          </div>

          <div>
            <h4 className="text-white font-semibold mb-2">Current nation relations</h4>
            {loading && <p className="text-gray-400">Loading…</p>}
            {!loading && relations.length === 0 && (
              <p className="text-gray-400">No diplomatic deltas recorded yet — every nation pair is implicitly neutral.</p>
            )}
            <div className="grid md:grid-cols-2 gap-2">
              {relations.map((rel) => (
                <div
                  key={`${rel.nation_a}-${rel.nation_b}`}
                  className={`p-3 rounded-lg border ${STANCE_COLOR[rel.stance] || STANCE_COLOR.neutral}`}
                  data-testid={`relation-${rel.nation_a}-${rel.nation_b}`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-semibold capitalize">
                      {rel.nation_a} ⇄ {rel.nation_b}
                    </span>
                    <span className="text-xs uppercase tracking-wide">{rel.stance.replace('_', ' ')}</span>
                  </div>
                  <p className="text-xs opacity-80 mt-1">
                    Score: {rel.score >= 0 ? '+' : ''}{rel.score}/100
                    {rel.last_event_at && ` • Updated ${new Date(rel.last_event_at).toLocaleString()}`}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </TabsContent>

        {/* WORLD EVENTS */}
        <TabsContent value="world" className="space-y-4">
          <div className="glass-dark p-4 rounded-xl space-y-3">
            <h4 className="text-white font-semibold flex items-center gap-2">
              <Plus className="w-4 h-4" /> Seed world event
            </h4>
            <div className="grid grid-cols-2 gap-2">
              <Input
                placeholder="event_type (e.g., royal_decree, plague, festival)"
                value={eventDraft.event_type}
                onChange={(e) => setEventDraft({ ...eventDraft, event_type: e.target.value })}
                className="bg-black/30 border-amber-500/30 text-white"
                data-testid="world-event-type"
              />
              <Select value={eventDraft.scope} onValueChange={(v) => setEventDraft({ ...eventDraft, scope: v })}>
                <SelectTrigger className="bg-black/30 border-amber-500/30 text-white" data-testid="world-event-scope">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="world">world</SelectItem>
                  <SelectItem value="diplomatic">diplomatic</SelectItem>
                  <SelectItem value="local">local</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <Input
              placeholder="Summary (1-line, visible in admin only)"
              value={eventDraft.summary}
              onChange={(e) => setEventDraft({ ...eventDraft, summary: e.target.value })}
              className="bg-black/30 border-amber-500/30 text-white"
              data-testid="world-event-summary"
            />
            <Textarea
              placeholder="Details (richer context)"
              value={eventDraft.details}
              onChange={(e) => setEventDraft({ ...eventDraft, details: e.target.value })}
              className="bg-black/30 border-amber-500/30 text-white min-h-[60px]"
              data-testid="world-event-details"
            />
            <Input
              placeholder="Involved nations (comma-separated slugs, optional)"
              value={eventDraft.nations}
              onChange={(e) => setEventDraft({ ...eventDraft, nations: e.target.value })}
              className="bg-black/30 border-amber-500/30 text-white"
              data-testid="world-event-nations"
            />
            <Button onClick={createWorldEvent} className="bg-amber-600 hover:bg-amber-700 w-full" data-testid="world-event-save">Record event</Button>
          </div>

          <div className="space-y-2">
            {worldEvents.length === 0 ? (
              <p className="text-gray-400">No world events yet. As players interact with high-tier NPCs, ripples will accrue here.</p>
            ) : (
              worldEvents.map((ev) => (
                <div key={ev.id} className="glass-dark p-3 rounded-xl border border-amber-500/20" data-testid={`world-event-${ev.id}`}>
                  <div className="flex items-center justify-between flex-wrap gap-2">
                    <span className="text-amber-200 font-semibold">[{ev.event_type}] {ev.summary}</span>
                    <span className="text-xs text-gray-400">{new Date(ev.created_at).toLocaleString()}</span>
                  </div>
                  {ev.details && <p className="text-sm text-gray-300 mt-1">{ev.details}</p>}
                  {ev.nations?.length > 0 && (
                    <p className="text-xs text-gray-500 mt-1">Nations: {ev.nations.join(', ')} • Scope: {ev.scope}</p>
                  )}
                </div>
              ))
            )}
          </div>
        </TabsContent>

        {/* CASCADES */}
        <TabsContent value="cascades" className="space-y-3">
          {cascades.length === 0 ? (
            <p className="text-gray-400">No cascades pending. Provoke a noble or higher and watch this fill up.</p>
          ) : (
            cascades.map((c) => (
              <div key={c.id} className="glass-dark p-3 rounded-xl border border-pink-500/20" data-testid={`cascade-${c.id}`}>
                <div className="flex items-center justify-between flex-wrap gap-2">
                  <span className="text-pink-200 font-semibold">
                    [{c.cascade_type}] {c.memory_text || c.reason}
                  </span>
                  <span className="text-xs text-gray-400">
                    Deliver after: {new Date(c.deliver_after).toLocaleString()}
                  </span>
                </div>
                <p className="text-xs text-gray-400 mt-1">
                  Target: {c.nation_filter || 'any nation'}{c.location_filter ? ` / ${c.location_filter}` : ''}
                  {' '}• Tier ≥ {c.importance_min} • Sentiment {c.sentiment_delta >= 0 ? '+' : ''}{c.sentiment_delta}
                </p>
              </div>
            ))
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
};

const NationSelect = ({ value, onChange, testid }) => (
  <Select value={value} onValueChange={onChange}>
    <SelectTrigger className="bg-black/30 border-purple-500/30 text-white capitalize" data-testid={testid}>
      <SelectValue />
    </SelectTrigger>
    <SelectContent>
      {NATIONS.map((n) => (
        <SelectItem key={n} value={n} className="capitalize">{n}</SelectItem>
      ))}
    </SelectContent>
  </Select>
);

export default AdminWorldPulse;
