import React, { useEffect, useState, useCallback } from 'react';
import { toast } from 'sonner';
import {
  ScrollText, Plus, Sparkles, Coins, Star, Lock, Check, Loader2, X,
} from 'lucide-react';
import {
  listFactionQuests, createFactionQuest, aiGenerateFactionQuest,
  completeFactionQuest, closeFactionQuest,
} from '../../utils/api';
import { Button } from '../ui/button';
import { Textarea } from '../ui/textarea';

const RANKS = ['initiate', 'member', 'officer', 'leader'];
const _idx = (r) => RANKS.indexOf(r);

const FactionQuestsTab = ({ slug, myCharsInFaction, factionName }) => {
  const [quests, setQuests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [creating, setCreating] = useState(false);
  const [aiBusy, setAiBusy] = useState(false);
  const [completing, setCompleting] = useState({});
  const [activeCharByQuest, setActiveCharByQuest] = useState({});
  const [proofByQuest, setProofByQuest] = useState({});

  const [createForm, setCreateForm] = useState({
    actor_character_id: '',
    title: '',
    objective: '',
    flavour: '',
    reward_gold: 50,
    reward_reputation: 10,
    max_completions: 5,
  });

  const officerActors = myCharsInFaction.filter((m) => _idx(m.rank) >= _idx('officer'));
  const canIssue = officerActors.length > 0;
  const defaultActorId = officerActors[0]?.character_id || '';
  const defaultMemberId = myCharsInFaction[0]?.character_id || '';

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await listFactionQuests(slug);
      setQuests(r.data || []);
    } finally { setLoading(false); }
  }, [slug]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    setCreateForm((f) => ({ ...f, actor_character_id: f.actor_character_id || defaultActorId }));
  }, [defaultActorId]);

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!createForm.actor_character_id) { toast.error('Pick an officer to issue this quest.'); return; }
    setCreating(true);
    try {
      await createFactionQuest(slug, createForm);
      toast.success('Quest issued.');
      setShowCreate(false);
      setCreateForm({
        actor_character_id: defaultActorId,
        title: '', objective: '', flavour: '',
        reward_gold: 50, reward_reputation: 10, max_completions: 5,
      });
      await load();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to issue quest.');
    } finally { setCreating(false); }
  };

  const handleAiGenerate = async () => {
    if (!defaultActorId) { toast.error('Only Officers or the Leader can summon the Quest Captain.'); return; }
    setAiBusy(true);
    try {
      const r = await aiGenerateFactionQuest(slug, {
        actor_character_id: defaultActorId,
        reward_gold: 75,
        reward_reputation: 15,
        max_completions: 5,
      });
      toast.success(`The Quest Captain authored «${r.data.title}».`);
      await load();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'AI generation failed.');
    } finally { setAiBusy(false); }
  };

  const handleComplete = async (quest) => {
    const charId = activeCharByQuest[quest.id] || defaultMemberId;
    if (!charId) { toast.error('Pick a character to claim this quest.'); return; }
    setCompleting((b) => ({ ...b, [quest.id]: true }));
    try {
      const r = await completeFactionQuest(slug, quest.id, charId, proofByQuest[quest.id] || '');
      toast.success(`Quest complete — +${r.data.completion.gold_paid}g, +${r.data.completion.reputation_paid} rep.`);
      setProofByQuest((p) => ({ ...p, [quest.id]: '' }));
      await load();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to complete quest.');
    } finally {
      setCompleting((b) => ({ ...b, [quest.id]: false }));
    }
  };

  const handleClose = async (quest) => {
    if (!defaultActorId) return;
    if (!window.confirm(`Close the quest «${quest.title}» for ${factionName}?`)) return;
    try {
      await closeFactionQuest(slug, quest.id, defaultActorId);
      toast.success('Quest closed.');
      await load();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to close quest.');
    }
  };

  if (loading) return <p className="text-gray-500 italic text-center py-8">The Quest Captain is sorting the rolls…</p>;

  return (
    <div data-testid="faction-quests-tab">
      <div className="flex items-start justify-between gap-3 mb-4">
        <p className="text-xs text-gray-400 italic max-w-md">
          Commissions issued by the faction. Each member may claim a quest only once.
          Rewards roll into your purse and into the faction's standing.
        </p>
        {canIssue && (
          <div className="flex gap-2 flex-shrink-0">
            <Button
              size="sm"
              variant="outline"
              onClick={handleAiGenerate}
              disabled={aiBusy}
              className="border-purple-500/50 text-purple-200 hover:bg-purple-900/30"
              data-testid="ai-generate-quest-btn"
            >
              {aiBusy ? <Loader2 className="w-3 h-3 mr-1 animate-spin" /> : <Sparkles className="w-3 h-3 mr-1" />}
              Summon Quest Captain
            </Button>
            <Button
              size="sm"
              onClick={() => setShowCreate(true)}
              className="bg-gradient-to-r from-amber-600 to-orange-600"
              data-testid="new-quest-btn"
            >
              <Plus className="w-3 h-3 mr-1" /> New Commission
            </Button>
          </div>
        )}
      </div>

      {quests.length === 0 ? (
        <p className="text-gray-500 italic text-center py-10" data-testid="quests-empty">
          No commissions are open. {canIssue && 'Issue one to put your faction to work.'}
        </p>
      ) : (
        <ul className="space-y-3">
          {quests.map((q) => {
            const isFull = q.completion_count >= q.max_completions;
            return (
              <li
                key={q.id}
                className="glass-dark border border-amber-700/30 rounded-lg p-4 relative"
                data-testid={`quest-row-${q.id}`}
              >
                <header className="flex items-start gap-2 justify-between">
                  <div className="min-w-0 flex-1">
                    <h4 className="font-bold text-amber-200 text-lg flex items-center gap-2" style={{ fontFamily: 'Georgia, serif' }}>
                      <ScrollText className="w-4 h-4 flex-shrink-0" />
                      <span className="truncate">{q.title}</span>
                      {q.source === 'ai' && (
                        <span className="ml-1 text-[10px] uppercase tracking-wider bg-purple-900/40 border border-purple-500/40 text-purple-200 px-1.5 py-0.5 rounded">
                          AI
                        </span>
                      )}
                    </h4>
                    <p className="text-xs text-gray-400 mt-0.5">
                      Issued by <span className="text-gray-300">{q.issued_by_character_name}</span> ({q.issued_by_rank}) ·{' '}
                      {new Date(q.created_at).toLocaleDateString()}
                    </p>
                  </div>
                  {canIssue && (
                    <button
                      onClick={() => handleClose(q)}
                      className="text-gray-500 hover:text-red-300 text-xs"
                      title="Close quest"
                      data-testid={`close-quest-${q.id}`}
                    >
                      <X className="w-4 h-4" />
                    </button>
                  )}
                </header>

                <p className="text-gray-200 mt-2 whitespace-pre-wrap">{q.objective}</p>
                {q.flavour && (
                  <p className="text-sm text-amber-200/70 italic mt-2 border-l-2 border-amber-700/40 pl-3">
                    &ldquo;{q.flavour}&rdquo;
                  </p>
                )}

                <div className="flex flex-wrap items-center gap-3 mt-3 text-xs">
                  <span className="inline-flex items-center gap-1 text-amber-300" data-testid={`quest-gold-${q.id}`}>
                    <Coins className="w-3 h-3" /> {q.reward_gold} gold
                  </span>
                  <span className="inline-flex items-center gap-1 text-blue-300" data-testid={`quest-rep-${q.id}`}>
                    <Star className="w-3 h-3" /> +{q.reward_reputation} reputation
                  </span>
                  <span className="text-gray-400">
                    {q.completion_count} / {q.max_completions} completed
                  </span>
                  {isFull && (
                    <span className="text-red-300 inline-flex items-center gap-1">
                      <Lock className="w-3 h-3" /> Full
                    </span>
                  )}
                </div>

                {myCharsInFaction.length > 0 && !isFull && (
                  <div className="mt-3 pt-3 border-t border-gray-700/40 space-y-2" data-testid={`quest-claim-${q.id}`}>
                    <div className="flex flex-wrap items-center gap-2">
                      <label className="text-xs uppercase tracking-wider text-gray-400">Claim as</label>
                      <select
                        value={activeCharByQuest[q.id] || defaultMemberId}
                        onChange={(e) => setActiveCharByQuest((m) => ({ ...m, [q.id]: e.target.value }))}
                        className="bg-black/40 border border-gray-600 rounded px-2 py-1 text-sm text-gray-200"
                        data-testid={`quest-claim-as-${q.id}`}
                      >
                        {myCharsInFaction.map((m) => (
                          <option key={m.character_id} value={m.character_id}>
                            {m.character_name} ({m.rank})
                          </option>
                        ))}
                      </select>
                    </div>
                    <Textarea
                      value={proofByQuest[q.id] || ''}
                      onChange={(e) => setProofByQuest((p) => ({ ...p, [q.id]: e.target.value }))}
                      placeholder="(Optional) Recount what your character did to complete this commission…"
                      rows={2}
                      maxLength={600}
                      className="bg-black/40 border-gray-600 text-gray-100 text-sm"
                      data-testid={`quest-proof-${q.id}`}
                    />
                    <Button
                      size="sm"
                      onClick={() => handleComplete(q)}
                      disabled={completing[q.id]}
                      className="bg-gradient-to-r from-green-600 to-emerald-600"
                      data-testid={`quest-complete-${q.id}`}
                    >
                      {completing[q.id] ? <Loader2 className="w-3 h-3 mr-1 animate-spin" /> : <Check className="w-3 h-3 mr-1" />}
                      Mark Complete
                    </Button>
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      )}

      {/* Create modal */}
      {showCreate && (
        <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4" onClick={() => setShowCreate(false)}>
          <form
            onSubmit={handleCreate}
            onClick={(e) => e.stopPropagation()}
            className="glass-dark border border-amber-500/40 rounded-xl p-6 w-full max-w-md space-y-3 max-h-[90vh] overflow-y-auto"
            data-testid="new-quest-form"
          >
            <h3 className="text-xl font-bold text-amber-200" style={{ fontFamily: 'Georgia, serif' }}>
              Issue a Commission
            </h3>
            <div>
              <label className="text-xs uppercase tracking-wider text-gray-400 block mb-1">Issuing officer</label>
              <select
                value={createForm.actor_character_id}
                onChange={(e) => setCreateForm((f) => ({ ...f, actor_character_id: e.target.value }))}
                className="w-full bg-black/40 border border-gray-600 rounded px-3 py-2 text-gray-100"
                required
                data-testid="new-quest-actor-select"
              >
                {officerActors.map((m) => (
                  <option key={m.character_id} value={m.character_id}>
                    {m.character_name} ({m.rank})
                  </option>
                ))}
              </select>
            </div>
            <input
              type="text" required maxLength={120} placeholder="Quest title"
              value={createForm.title}
              onChange={(e) => setCreateForm((f) => ({ ...f, title: e.target.value }))}
              className="w-full bg-black/40 border border-gray-600 rounded px-3 py-2 text-gray-100"
              data-testid="new-quest-title-input"
            />
            <Textarea
              required maxLength={600} rows={4}
              placeholder="What must the member do?"
              value={createForm.objective}
              onChange={(e) => setCreateForm((f) => ({ ...f, objective: e.target.value }))}
              className="bg-black/40 border-gray-600 text-gray-100"
              data-testid="new-quest-objective-input"
            />
            <input
              type="text" maxLength={200} placeholder="(Optional) A single in-character line"
              value={createForm.flavour}
              onChange={(e) => setCreateForm((f) => ({ ...f, flavour: e.target.value }))}
              className="w-full bg-black/40 border border-gray-600 rounded px-3 py-2 text-gray-100 italic"
              data-testid="new-quest-flavour-input"
            />
            <div className="grid grid-cols-3 gap-2">
              <label className="text-xs text-gray-400">
                Gold
                <input
                  type="number" min={0} max={5000}
                  value={createForm.reward_gold}
                  onChange={(e) => setCreateForm((f) => ({ ...f, reward_gold: parseInt(e.target.value, 10) || 0 }))}
                  className="w-full bg-black/40 border border-gray-600 rounded px-2 py-1 text-gray-100 mt-1"
                  data-testid="new-quest-gold-input"
                />
              </label>
              <label className="text-xs text-gray-400">
                Rep
                <input
                  type="number" min={0} max={200}
                  value={createForm.reward_reputation}
                  onChange={(e) => setCreateForm((f) => ({ ...f, reward_reputation: parseInt(e.target.value, 10) || 0 }))}
                  className="w-full bg-black/40 border border-gray-600 rounded px-2 py-1 text-gray-100 mt-1"
                  data-testid="new-quest-rep-input"
                />
              </label>
              <label className="text-xs text-gray-400">
                Slots
                <input
                  type="number" min={1} max={100}
                  value={createForm.max_completions}
                  onChange={(e) => setCreateForm((f) => ({ ...f, max_completions: parseInt(e.target.value, 10) || 1 }))}
                  className="w-full bg-black/40 border border-gray-600 rounded px-2 py-1 text-gray-100 mt-1"
                  data-testid="new-quest-slots-input"
                />
              </label>
            </div>
            <div className="flex gap-2 justify-end pt-2">
              <Button type="button" variant="outline" onClick={() => setShowCreate(false)}>Cancel</Button>
              <Button type="submit" disabled={creating} className="bg-gradient-to-r from-amber-600 to-orange-600" data-testid="new-quest-submit-btn">
                {creating ? <Loader2 className="w-3 h-3 mr-1 animate-spin" /> : null}
                Issue
              </Button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
};

export default FactionQuestsTab;
