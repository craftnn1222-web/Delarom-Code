import React, { useEffect, useState, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import {
  Shield, Users, ArrowLeft, ChevronUp, ChevronDown, UserMinus, LogOut, UserPlus, Skull, TreePine, Hammer, Crown, ScrollText, Flame, MessageSquare, Star, Coins, Swords,
} from 'lucide-react';
import {
  getFaction, listFactionMembers, getMyFactionMemberships, joinFaction, leaveFaction,
  promoteFactionMember, demoteFactionMember, expelFactionMember, getMyCharacters,
  getFactionTreasury, donateToFactionTreasury,
} from '../utils/api';
import AnimatedBackground from '../components/AnimatedBackground';
import Navbar from '../components/Navbar';
import { Button } from '../components/ui/button';
import { Textarea } from '../components/ui/textarea';
import { useAuth } from '../contexts/AuthContext';
import FactionThreadsTab from '../components/factions/FactionThreadsTab';
import FactionReputationTab from '../components/factions/FactionReputationTab';
import FactionQuestsTab from '../components/factions/FactionQuestsTab';
import FactionRivalriesTab from '../components/factions/FactionRivalriesTab';
import FactionNpcRosterTab from '../components/factions/FactionNpcRosterTab';
import FactionSpecialtiesTab from '../components/factions/FactionSpecialtiesTab';
import FactionTradeRoutesTab from '../components/factions/FactionTradeRoutesTab';
import CaravansBoard from '../components/CaravansBoard';

const ICONS = { shield: Shield, swords: Swords, skull: Skull, tree: TreePine, hammer: Hammer, crown: Crown, scroll: ScrollText, flame: Flame };

const RANK_LABELS = { initiate: 'Initiate', member: 'Member', officer: 'Officer', leader: 'Leader' };
const RANK_TONE = {
  initiate: 'bg-gray-800/40 text-gray-300 border-gray-600/40',
  member:   'bg-blue-900/40 text-blue-200 border-blue-700/40',
  officer:  'bg-purple-900/40 text-purple-200 border-purple-700/40',
  leader:   'bg-amber-900/40 text-amber-200 border-amber-600/60',
};

const FactionDetail = () => {
  const { slug } = useParams();
  const navigate = useNavigate();
  const { currentUser } = useAuth();

  const [faction, setFaction] = useState(null);
  const [members, setMembers] = useState([]);
  const [myCharacters, setMyCharacters] = useState([]);
  const [myMemberships, setMyMemberships] = useState([]);
  const [treasury, setTreasury] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showJoin, setShowJoin] = useState(false);
  const [showDonate, setShowDonate] = useState(false);
  const [donateForm, setDonateForm] = useState({ character_id: '', amount: 25 });
  const [joinForm, setJoinForm] = useState({ character_id: '', pitch: '' });
  const [busy, setBusy] = useState({});
  const [activeTab, setActiveTab] = useState('roster');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const tasks = [getFaction(slug), listFactionMembers(slug), getFactionTreasury(slug)];
      if (currentUser) {
        tasks.push(getMyCharacters());
        tasks.push(getMyFactionMemberships());
      }
      const results = await Promise.allSettled(tasks);
      if (results[0].status === 'fulfilled') setFaction(results[0].value.data);
      if (results[1].status === 'fulfilled') setMembers(results[1].value.data);
      if (results[2].status === 'fulfilled') setTreasury(results[2].value.data);
      if (results[3] && results[3].status === 'fulfilled') setMyCharacters(results[3].value.data);
      if (results[4] && results[4].status === 'fulfilled') setMyMemberships(results[4].value.data);
    } finally { setLoading(false); }
  }, [slug, currentUser]);

  useEffect(() => { load(); }, [load]);

  const charsInThisFaction = myMemberships.filter((m) => m.faction_slug === slug);
  const myActiveCharIds = new Set(myMemberships.map((m) => m.character_id));
  const charsAvailableToJoin = myCharacters.filter((c) => !myActiveCharIds.has(c.id));

  // The highest-rank actor character I have in this faction (used for admin actions)
  const actorMembership =
    charsInThisFaction.find((m) => m.rank === 'leader') ||
    charsInThisFaction.find((m) => m.rank === 'officer') || null;

  const handleJoinSubmit = async (e) => {
    e.preventDefault();
    if (!joinForm.character_id) { toast.error('Pick a character first.'); return; }
    try {
      await joinFaction(slug, joinForm.character_id, joinForm.pitch);
      toast.success(`Pledged to ${faction.name}.`);
      setShowJoin(false);
      setJoinForm({ character_id: '', pitch: '' });
      await load();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to join.');
    }
  };

  const handleLeave = async (charId, charName) => {
    if (!window.confirm(`Are you sure you want ${charName} to leave ${faction.name}?`)) return;
    try {
      await leaveFaction(slug, charId);
      toast.success(`${charName} has left ${faction.name}.`);
      await load();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to leave.');
    }
  };

  const handleDonateSubmit = async (e) => {
    e.preventDefault();
    if (!donateForm.character_id) { toast.error('Pick a character to donate from.'); return; }
    if (!donateForm.amount || donateForm.amount < 1) { toast.error('Donate at least 1 gold.'); return; }
    try {
      await donateToFactionTreasury(slug, donateForm.character_id, donateForm.amount);
      toast.success(`${donateForm.amount} gold added to the coffer.`);
      setShowDonate(false);
      setDonateForm({ character_id: charsInThisFaction[0]?.character_id || '', amount: 25 });
      await load();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to donate.');
    }
  };

  const guardedAction = async (id, fn) => {
    setBusy((b) => ({ ...b, [id]: true }));
    try { await fn(); await load(); }
    catch (err) { toast.error(err.response?.data?.detail || 'Action failed.'); }
    finally { setBusy((b) => ({ ...b, [id]: false })); }
  };

  if (loading) {
    return (
      <div className="min-h-screen relative">
        <AnimatedBackground /><Navbar />
        <p className="relative z-10 text-center text-gray-500 italic py-20">The heralds are riding…</p>
      </div>
    );
  }
  if (!faction) {
    return (
      <div className="min-h-screen relative">
        <AnimatedBackground /><Navbar />
        <p className="relative z-10 text-center text-gray-400 py-20">Faction not found.</p>
      </div>
    );
  }

  const Icon = ICONS[faction.icon] || Shield;
  const color = faction.color_hex || '#a855f7';

  return (
    <div className="min-h-screen relative">
      <AnimatedBackground />
      <Navbar />

      <div className="relative z-10 container mx-auto px-4 py-8 max-w-5xl" data-testid={`faction-detail-${slug}`}>
        <button
          onClick={() => navigate('/factions')}
          className="text-gray-400 hover:text-white flex items-center gap-2 mb-6 text-sm"
          data-testid="faction-back-btn"
        >
          <ArrowLeft className="w-4 h-4" /> All Factions
        </button>

        {/* Header */}
        <header
          className="glass-dark rounded-2xl p-6 mb-6 border"
          style={{ borderColor: `${color}66`, borderTop: `5px solid ${color}` }}
        >
          <div className="flex items-start gap-4">
            <div
              className="p-4 rounded-xl flex-shrink-0"
              style={{ backgroundColor: `${color}22`, border: `1px solid ${color}66` }}
            >
              <Icon className="w-8 h-8" style={{ color }} />
            </div>
            <div className="flex-1 min-w-0">
              <h1 className="text-3xl sm:text-4xl font-bold text-gray-100" style={{ fontFamily: 'Georgia, serif' }} data-testid="faction-name">
                {faction.name}
              </h1>
              {faction.motto && (
                <p className="text-base italic text-gray-300 mt-1" data-testid="faction-motto">&ldquo;{faction.motto}&rdquo;</p>
              )}
              <div className="flex flex-wrap gap-2 mt-3 text-xs text-gray-400">
                {faction.nation_home && (
                  <span className="uppercase tracking-wider px-2 py-0.5 rounded-full bg-purple-900/30 border border-purple-600/40 text-purple-200">
                    {faction.nation_home.replace('-', ' ')}
                  </span>
                )}
                <span className="inline-flex items-center gap-1">
                  <Users className="w-3 h-3" />
                  {faction.member_count || 0} {faction.member_count === 1 ? 'member' : 'members'}
                </span>
                {faction.founded_at && (
                  <span>Founded {new Date(faction.founded_at).toLocaleDateString()}</span>
                )}
                {treasury && (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-amber-900/30 border border-amber-600/40 text-amber-200" data-testid="faction-treasury-pill">
                    <Coins className="w-3 h-3" />
                    {treasury.balance.toLocaleString()} in the coffer
                  </span>
                )}
              </div>
            </div>

            {currentUser && charsInThisFaction.length === 0 && charsAvailableToJoin.length > 0 && (
              <Button
                onClick={() => setShowJoin(true)}
                className="bg-gradient-to-r from-purple-600 to-pink-600"
                data-testid="join-faction-btn"
              >
                <UserPlus className="w-4 h-4 mr-2" /> Pledge a Character
              </Button>
            )}
            {currentUser && charsInThisFaction.length > 0 && (
              <Button
                onClick={() => {
                  setDonateForm({ character_id: charsInThisFaction[0]?.character_id || '', amount: 25 });
                  setShowDonate(true);
                }}
                variant="outline"
                className="border-amber-500/50 text-amber-200 hover:bg-amber-900/30"
                data-testid="donate-coffer-btn"
              >
                <Coins className="w-4 h-4 mr-2" /> Add to Coffer
              </Button>
            )}
          </div>

          <p className="text-gray-300 leading-relaxed mt-6" data-testid="faction-description">{faction.description}</p>
        </header>

        {/* My characters in this faction */}
        {charsInThisFaction.length > 0 && (
          <section className="mb-6" data-testid="my-stake-section">
            <h2 className="text-sm uppercase tracking-[0.3em] text-amber-300 mb-3">Your Stake</h2>
            <div className="space-y-2">
              {charsInThisFaction.map((m) => (
                <div key={m.id} className="glass-dark border border-amber-500/30 rounded-lg p-3 flex items-center justify-between" data-testid={`my-stake-${m.character_id}`}>
                  <div className="flex items-center gap-3">
                    <span className={`px-2.5 py-1 rounded-full text-xs border ${RANK_TONE[m.rank]}`}>{RANK_LABELS[m.rank]}</span>
                    <span className="text-gray-100 font-semibold">{m.character_name}</span>
                    <span className="text-xs text-gray-500">since {new Date(m.joined_at).toLocaleDateString()}</span>
                  </div>
                  <Button
                    onClick={() => handleLeave(m.character_id, m.character_name)}
                    size="sm" variant="outline"
                    className="border-red-500/50 text-red-300 hover:bg-red-900/30"
                    data-testid={`leave-faction-${m.character_id}`}
                  >
                    <LogOut className="w-3 h-3 mr-1" /> Leave
                  </Button>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Tab strip */}
        <div className="flex gap-2 mb-4 border-b border-gray-700/40 flex-wrap" data-testid="faction-tabs">
          {[
            { id: 'roster',      label: 'Roster',      icon: Users,          count: members.length },
            { id: 'lifeblood',   label: 'Lifeblood',   icon: Users,          count: null },
            { id: 'specialties', label: 'Offerings',   icon: Coins,          count: null },
            { id: 'trade',       label: 'Trade Routes',icon: Coins,          count: null },
            { id: 'caravans',    label: 'Caravans',    icon: Coins,          count: null },
            { id: 'quests',      label: 'Quests',      icon: ScrollText,     count: null },
            { id: 'threads',     label: 'Threads',     icon: MessageSquare,  count: null },
            { id: 'reputation',  label: 'Reputation',  icon: Star,           count: null },
            { id: 'rivalries',   label: 'Rivalries',   icon: Swords,         count: null },
          ].map((t) => {
            const TabIcon = t.icon;
            const active = activeTab === t.id;
            return (
              <button
                key={t.id}
                type="button"
                onClick={() => setActiveTab(t.id)}
                data-testid={`faction-tab-${t.id}`}
                className={`flex items-center gap-2 px-4 py-2 text-sm border-b-2 transition ${
                  active
                    ? 'border-amber-400 text-amber-200 font-semibold'
                    : 'border-transparent text-gray-400 hover:text-gray-200'
                }`}
              >
                <TabIcon className="w-4 h-4" />
                {t.label}
                {t.count !== null && (
                  <span className={`text-xs ${active ? 'text-amber-300/80' : 'text-gray-500'}`}>({t.count})</span>
                )}
              </button>
            );
          })}
        </div>

        {/* Roster tab */}
        {activeTab === 'roster' && (
        <section data-testid="member-roster-section">
          <h2 className="text-sm uppercase tracking-[0.3em] text-gray-400 mb-3">Roster ({members.length})</h2>
          {members.length === 0 ? (
            <p className="text-gray-500 italic">No one has yet pledged to this banner.</p>
          ) : (
            <ul className="divide-y divide-gray-800/60 glass-dark rounded-xl border border-gray-700/40">
              {members.map((m) => {
                const canManage = actorMembership && actorMembership.rank_index > (m.rank_index ?? 0);
                const isLeaderActor = actorMembership && actorMembership.rank === 'leader';
                return (
                  <li key={m.id} className="px-4 py-3 flex items-center justify-between" data-testid={`member-row-${m.character_id}`}>
                    <div className="flex items-center gap-3 min-w-0 flex-1">
                      <span className={`px-2.5 py-1 rounded-full text-xs border whitespace-nowrap ${RANK_TONE[m.rank]}`}>
                        {RANK_LABELS[m.rank]}
                      </span>
                      <span className="text-gray-100 font-semibold truncate">{m.character_name}</span>
                      <span className="text-xs text-gray-500 truncate hidden sm:inline">
                        since {new Date(m.joined_at).toLocaleDateString()}
                      </span>
                    </div>
                    {canManage && (
                      <div className="flex items-center gap-1">
                        <Button
                          size="sm" variant="outline" disabled={busy[m.id] || m.rank === 'officer'}
                          className="border-blue-500/40 text-blue-300 hover:bg-blue-900/30 h-7 px-2"
                          onClick={() => guardedAction(m.id, () => promoteFactionMember(slug, m.character_id, actorMembership.character_id))}
                          data-testid={`promote-${m.character_id}`}
                          title="Promote"
                        >
                          <ChevronUp className="w-3 h-3" />
                        </Button>
                        <Button
                          size="sm" variant="outline" disabled={busy[m.id] || m.rank === 'initiate'}
                          className="border-yellow-500/40 text-yellow-300 hover:bg-yellow-900/30 h-7 px-2"
                          onClick={() => guardedAction(m.id, () => demoteFactionMember(slug, m.character_id, actorMembership.character_id))}
                          data-testid={`demote-${m.character_id}`}
                          title="Demote"
                        >
                          <ChevronDown className="w-3 h-3" />
                        </Button>
                        {isLeaderActor && (
                          <Button
                            size="sm" variant="outline" disabled={busy[m.id]}
                            className="border-red-500/40 text-red-300 hover:bg-red-900/30 h-7 px-2"
                            onClick={() => {
                              if (window.confirm(`Expel ${m.character_name} from ${faction.name}?`)) {
                                guardedAction(m.id, () => expelFactionMember(slug, m.character_id, actorMembership.character_id));
                              }
                            }}
                            data-testid={`expel-${m.character_id}`}
                            title="Expel"
                          >
                            <UserMinus className="w-3 h-3" />
                          </Button>
                        )}
                      </div>
                    )}
                  </li>
                );
              })}
            </ul>
          )}
        </section>
        )}

        {/* Threads tab */}
        {activeTab === 'threads' && (
          <FactionThreadsTab slug={slug} myCharsInFaction={charsInThisFaction} />
        )}

        {/* Quests tab */}
        {activeTab === 'quests' && (
          <FactionQuestsTab slug={slug} myCharsInFaction={charsInThisFaction} factionName={faction.name} />
        )}

        {/* Reputation tab */}
        {activeTab === 'reputation' && (
          <FactionReputationTab slug={slug} />
        )}

        {/* Rivalries tab */}
        {activeTab === 'rivalries' && (
          <FactionRivalriesTab slug={slug} myCharsInFaction={charsInThisFaction} factionName={faction.name} />
        )}

        {/* Lifeblood tab — NPC roster */}
        {activeTab === 'lifeblood' && (
          <FactionNpcRosterTab slug={slug} faction={faction} />
        )}

        {/* Specialties tab — what this faction produces / charges */}
        {activeTab === 'specialties' && (
          <FactionSpecialtiesTab
            factionSlug={slug}
            canEdit={Boolean(
              (currentUser && (currentUser.role === 'admin' || currentUser.role === 'moderator')) ||
              charsInThisFaction.some((m) => m.rank === 'leader')
            )}
          />
        )}

        {/* Trade Routes tab — standing contracts originating from this faction */}
        {activeTab === 'trade' && (
          <FactionTradeRoutesTab
            factionSlug={slug}
            canEdit={Boolean(
              (currentUser && (currentUser.role === 'admin' || currentUser.role === 'moderator')) ||
              charsInThisFaction.some((m) => m.rank === 'leader')
            )}
          />
        )}

        {/* Caravans tab — one-off paid hauls posted by this faction */}
        {activeTab === 'caravans' && (
          <CaravansBoard
            factionSlug={slug}
            canPost={Boolean(
              (currentUser && (currentUser.role === 'admin' || currentUser.role === 'moderator')) ||
              charsInThisFaction.some((m) => m.rank === 'leader')
            )}
            currentUserCharacterIds={charsInThisFaction.map((m) => m.character_id)}
          />
        )}

        {/* Join Modal */}
        {showJoin && (
          <div
            className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4"
            onClick={() => setShowJoin(false)}
          >
            <form
              onSubmit={handleJoinSubmit}
              onClick={(e) => e.stopPropagation()}
              className="glass-dark border border-purple-500/40 rounded-xl p-6 w-full max-w-md space-y-4"
              data-testid="join-faction-form"
            >
              <h3 className="text-xl font-bold text-purple-200">Pledge to {faction.name}</h3>
              <div>
                <label className="text-xs uppercase tracking-wider text-gray-400 block mb-1">Character</label>
                <select
                  value={joinForm.character_id}
                  onChange={(e) => setJoinForm({ ...joinForm, character_id: e.target.value })}
                  className="w-full bg-black/50 border border-gray-600 rounded px-3 py-2 text-gray-100"
                  required
                  data-testid="join-character-select"
                >
                  <option value="">Choose a character…</option>
                  {charsAvailableToJoin.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name} — {c.race} {c.character_class}
                    </option>
                  ))}
                </select>
                {charsAvailableToJoin.length === 0 && (
                  <p className="text-xs text-red-300 mt-2">
                    All your characters are already pledged elsewhere. A character can hold only one faction at a time.
                  </p>
                )}
              </div>
              <div>
                <label className="text-xs uppercase tracking-wider text-gray-400 block mb-1">Your Pitch (optional)</label>
                <Textarea
                  value={joinForm.pitch}
                  onChange={(e) => setJoinForm({ ...joinForm, pitch: e.target.value })}
                  placeholder="Why does your character seek this banner?"
                  rows={4}
                  maxLength={600}
                  className="bg-black/40 border-gray-600 text-gray-100"
                  data-testid="join-pitch-input"
                />
              </div>
              <div className="flex gap-2 justify-end">
                <Button type="button" variant="outline" onClick={() => setShowJoin(false)}>Cancel</Button>
                <Button type="submit" className="bg-gradient-to-r from-purple-600 to-pink-600" data-testid="join-submit-btn">
                  Pledge
                </Button>
              </div>
            </form>
          </div>
        )}

        {/* Donate Modal */}
        {showDonate && (
          <div
            className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4"
            onClick={() => setShowDonate(false)}
          >
            <form
              onSubmit={handleDonateSubmit}
              onClick={(e) => e.stopPropagation()}
              className="glass-dark border border-amber-500/40 rounded-xl p-6 w-full max-w-md space-y-3"
              data-testid="donate-coffer-form"
            >
              <h3 className="text-xl font-bold text-amber-200" style={{ fontFamily: 'Georgia, serif' }}>
                Add to the {faction.name} Coffer
              </h3>
              <p className="text-xs text-gray-400 italic">
                Donations come from your personal purse and join the faction's standing balance.
              </p>
              <div>
                <label className="text-xs uppercase tracking-wider text-gray-400 block mb-1">Donating as</label>
                <select
                  value={donateForm.character_id}
                  onChange={(e) => setDonateForm({ ...donateForm, character_id: e.target.value })}
                  className="w-full bg-black/40 border border-gray-600 rounded px-3 py-2 text-gray-100"
                  required
                  data-testid="donate-character-select"
                >
                  {charsInThisFaction.map((m) => (
                    <option key={m.character_id} value={m.character_id}>
                      {m.character_name} ({m.rank})
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-xs uppercase tracking-wider text-gray-400 block mb-1">Amount (gold)</label>
                <input
                  type="number"
                  min={1}
                  max={100000}
                  value={donateForm.amount}
                  onChange={(e) => setDonateForm({ ...donateForm, amount: parseInt(e.target.value, 10) || 0 })}
                  className="w-full bg-black/40 border border-gray-600 rounded px-3 py-2 text-gray-100"
                  data-testid="donate-amount-input"
                />
                <p className="text-xs text-gray-500 mt-1">Your purse: {currentUser?.currency?.toLocaleString?.() ?? 0} gold</p>
              </div>
              <div className="flex gap-2 justify-end pt-2">
                <Button type="button" variant="outline" onClick={() => setShowDonate(false)}>Cancel</Button>
                <Button type="submit" className="bg-gradient-to-r from-amber-600 to-orange-600" data-testid="donate-submit-btn">
                  <Coins className="w-4 h-4 mr-1" /> Donate
                </Button>
              </div>
            </form>
          </div>
        )}
      </div>
    </div>
  );
};

export default FactionDetail;
