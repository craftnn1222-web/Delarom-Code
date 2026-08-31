import React, { useEffect, useState, useRef } from 'react';
import { Link } from 'react-router-dom';
import { getMe, getMyCharacters, getTransactions, getContinueState, updateOnboarding } from '../utils/api';
import { useCharacter } from '../contexts/CharacterContext';
import FactionBadge from '../components/factions/FactionBadge';
import useFactionBadges from '../hooks/useFactionBadges';
import AnimatedBackground from '../components/AnimatedBackground';
import Navbar from '../components/Navbar';
import WelcomeOnboarding from '../components/WelcomeOnboarding';
import { Button } from '../components/ui/button';
import { Coins, Scroll, Sword, ShoppingBag, TrendingUp, TrendingDown, Users, Skull, Flag, PlayCircle, MapPin } from 'lucide-react';
import { toast } from 'sonner';

const Dashboard = () => {
  const [user, setUser] = useState(null);
  const [characters, setCharacters] = useState([]);
  const [transactions, setTransactions] = useState([]);
  const [continueState, setContinueState] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showWelcome, setShowWelcome] = useState(false);
  const [welcomeStep, setWelcomeStep] = useState(0);
  const welcomeDismissed = useRef(false);

  const { characters: roster, activeCharacter, switchCharacter } = useCharacter();
  const [switching, setSwitching] = useState(null);

  const heroes = roster.length ? roster : characters;

  const handleSwitch = async (c) => {
    if (activeCharacter?.id === c.id || switching) return;
    setSwitching(c.id);
    try {
      await switchCharacter(c.id);
      toast.success(`Now playing as ${c.name}`);
    } catch (_e) {
      toast.error('Could not switch character');
    } finally {
      setSwitching(null);
    }
  };

  // Visibility pass — fetch faction badges for the user's characters.
  const factionsByChar = useFactionBadges(characters.map((c) => c.id));

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    // allSettled so a transient failure of any one source (e.g. transactions
    // API blip) doesn't wipe out the others. Previously a single failure made
    // the whole dashboard show "Failed to load" with no characters listed.
    const [userRes, charRes, transRes, contRes] = await Promise.allSettled([
      getMe(),
      getMyCharacters(),
      getTransactions(),
      getContinueState()
    ]);
    if (userRes.status === 'fulfilled') {
      const u = userRes.value.data;
      setUser(u);
      // One-time richer welcome flow: show it whenever the account hasn't
      // completed onboarding yet (new sign-ups), resuming at the saved step.
      if (u && u.onboarding_completed === false && !welcomeDismissed.current) {
        setWelcomeStep(u.onboarding_step || 0);
        setShowWelcome(true);
      }
    }
    if (charRes.status === 'fulfilled') setCharacters(charRes.value.data);
    if (transRes.status === 'fulfilled') setTransactions(transRes.value.data.slice(0, 5));
    if (contRes.status === 'fulfilled') setContinueState(contRes.value.data);
    if (userRes.status === 'rejected' && charRes.status === 'rejected') {
      // Both critical sources failed — surface the toast. Single-source
      // failures are tolerated silently with empty defaults.
      toast.error('Failed to load dashboard data');
    }
    setLoading(false);
  };

  if (loading) {
    return (
      <div className="min-h-screen relative">
        <AnimatedBackground />
        <Navbar />
        <div className="relative z-10 container mx-auto px-4 py-20 text-center">
          <div className="text-white text-xl">Loading your realm...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen relative">
      <AnimatedBackground />
      <Navbar />
      <WelcomeOnboarding
        open={showWelcome}
        username={user?.username}
        initialStep={welcomeStep}
        onStepChange={(s) => { updateOnboarding({ step: s }).catch(() => {}); }}
        onClose={() => {
          welcomeDismissed.current = true;
          setShowWelcome(false);
          updateOnboarding({ completed: true }).catch(() => {});
        }}
      />
      
      <div className="relative z-10 container mx-auto px-4 py-8">
        {/* Welcome Header */}
        <div className="glass-dark p-8 rounded-2xl mb-8" data-testid="dashboard-header">
          <h1 className="text-4xl font-bold mb-2 text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-pink-600">
            Welcome back, {user?.username}!
          </h1>
          <p className="text-gray-400">Your adventure in Delarom continues...</p>
        </div>

        {/* Character Switcher — the global "who am I playing" hero */}
        <div className="glass-dark p-6 rounded-2xl mb-8" data-testid="character-switcher">
          <div className="flex items-center gap-3 mb-1">
            <Users className="w-5 h-5 text-purple-300" />
            <h2 className="text-xl font-bold text-purple-200">Playing As</h2>
            {activeCharacter && (
              <span className="text-sm text-purple-300/80" data-testid="active-character-name">
                — {activeCharacter.name}
              </span>
            )}
          </div>
          <p className="text-xs text-gray-500 mb-4">
            Pick your hero once — they&apos;ll be used for roleplay, quests, and everywhere across web and mobile.
          </p>
          {heroes.length === 0 ? (
            <div className="flex items-center justify-between">
              <p className="text-gray-400 text-sm">No characters yet. Forge your first legend.</p>
              <Link to="/characters">
                <Button size="sm" className="bg-gradient-to-r from-purple-600 to-pink-600">Create Character</Button>
              </Link>
            </div>
          ) : (
            <div className="flex flex-wrap gap-3">
              {heroes.map((c) => {
                const isActive = activeCharacter?.id === c.id;
                return (
                  <button
                    key={c.id}
                    data-testid={`switch-character-${c.id}`}
                    onClick={() => handleSwitch(c)}
                    disabled={switching === c.id}
                    className={`flex items-center gap-3 px-4 py-2 rounded-xl border transition-all disabled:opacity-60 ${
                      isActive
                        ? 'border-purple-400 bg-purple-500/20 ring-1 ring-purple-400'
                        : 'border-white/10 bg-white/5 hover:border-purple-400/50'
                    }`}
                  >
                    {c.portrait_url ? (
                      <img src={c.portrait_url} alt={c.name} className="w-9 h-9 rounded-full object-cover" />
                    ) : (
                      <div className="w-9 h-9 rounded-full bg-purple-800/50 flex items-center justify-center text-sm text-white">
                        {c.name?.[0] || '?'}
                      </div>
                    )}
                    <div className="text-left">
                      <p className="text-white text-sm font-semibold leading-tight">{c.name}</p>
                      <p className="text-xs text-gray-400 leading-tight">{c.race} • {c.character_class}</p>
                    </div>
                    {isActive && (
                      <span className="text-[10px] uppercase tracking-wide text-purple-300 ml-1 font-bold">Active</span>
                    )}
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {/* Continue where you left off */}
        {(continueState?.last_scene || continueState?.active_party) && (
          <div className="glass-dark p-6 rounded-2xl mb-8" data-testid="continue-card">
            <div className="flex items-center gap-3 mb-4">
              <PlayCircle className="w-5 h-5 text-emerald-300" />
              <h2 className="text-xl font-bold text-emerald-200">Continue Where You Left Off</h2>
            </div>
            <div className="grid md:grid-cols-2 gap-4">
              {continueState?.last_scene && (
                <Link
                  to={`/roleplay/${continueState.last_scene.nation}/${continueState.last_scene.location}`}
                  data-testid="continue-rp-link"
                  className="flex items-center gap-4 p-4 rounded-xl border border-emerald-400/30 bg-emerald-500/10 hover:border-emerald-400/70 transition-all group"
                >
                  <div className="w-11 h-11 rounded-lg bg-emerald-800/40 flex items-center justify-center shrink-0">
                    <MapPin className="w-6 h-6 text-emerald-300" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-xs uppercase tracking-wide text-emerald-400/80">Last Scene</p>
                    <p className="text-white font-semibold truncate">{continueState.last_scene.location_name}</p>
                    <p className="text-xs text-gray-400 truncate">
                      {continueState.last_scene.city ? `${continueState.last_scene.city} • ` : ''}
                      as {continueState.last_scene.character_name}
                    </p>
                  </div>
                  <span className="ml-auto text-emerald-300 text-sm font-semibold group-hover:translate-x-0.5 transition-transform">Resume →</span>
                </Link>
              )}
              {continueState?.active_party && (
                <Link
                  to={`/parties/${continueState.active_party.id}`}
                  data-testid="continue-party-link"
                  className="flex items-center gap-4 p-4 rounded-xl border border-purple-400/30 bg-purple-500/10 hover:border-purple-400/70 transition-all group"
                >
                  <div className="w-11 h-11 rounded-lg bg-purple-800/40 flex items-center justify-center shrink-0">
                    <Users className="w-6 h-6 text-purple-300" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-xs uppercase tracking-wide text-purple-400/80">Active Party</p>
                    <p className="text-white font-semibold truncate">{continueState.active_party.name}</p>
                    <p className="text-xs text-gray-400 truncate capitalize">
                      {continueState.active_party.status} • {continueState.active_party.member_count} member{continueState.active_party.member_count === 1 ? '' : 's'}
                    </p>
                  </div>
                  <span className="ml-auto text-purple-300 text-sm font-semibold group-hover:translate-x-0.5 transition-transform">Open →</span>
                </Link>
              )}
            </div>
          </div>
        )}

        {/* Stats Grid */}
        <div className="grid md:grid-cols-3 gap-6 mb-8">
          <div className="glass p-6 rounded-xl" data-testid="currency-card">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-400 mb-1">Your Gold</p>
                <p className="text-3xl font-bold text-yellow-400 flex items-center gap-2">
                  <Coins className="w-8 h-8" />
                  {user?.currency}
                </p>
              </div>
            </div>
          </div>

          <div className="glass p-6 rounded-xl" data-testid="characters-card">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-400 mb-1">Characters</p>
                <p className="text-3xl font-bold text-purple-400 flex items-center gap-2">
                  <Scroll className="w-8 h-8" />
                  {characters.length}
                </p>
              </div>
              <Link to="/characters">
                <Button variant="outline" size="sm" className="border-purple-500/50">Manage</Button>
              </Link>
            </div>
          </div>

          <div className="glass p-6 rounded-xl" data-testid="quick-actions-card">
            <p className="text-gray-400 mb-3">Quick Actions</p>
            <div className="grid grid-cols-2 gap-2">
              <Link to="/quests">
                <Button size="sm" className="w-full bg-blue-600 hover:bg-blue-700">
                  <Sword className="w-4 h-4 mr-1" />
                  Quest Board
                </Button>
              </Link>
              <Link to="/my-quests">
                <Button size="sm" className="w-full bg-purple-600 hover:bg-purple-700">
                  <Sword className="w-4 h-4 mr-1" />
                  My Quests
                </Button>
              </Link>
              <Link to="/parties" className="col-span-2">
                <Button size="sm" className="w-full bg-amber-700 hover:bg-amber-800" data-testid="dashboard-parties-btn">
                  <Users className="w-4 h-4 mr-1" />
                  Party Quests
                </Button>
              </Link>
              <Link to="/trade-companies" className="col-span-2">
                <Button size="sm" className="w-full bg-amber-800 hover:bg-amber-900" data-testid="dashboard-trade-companies-btn">
                  <Coins className="w-4 h-4 mr-1" />
                  Trade Companies
                </Button>
              </Link>
              <Link to="/wanted">
                <Button size="sm" className="w-full bg-red-800 hover:bg-red-900" data-testid="dashboard-wanted-btn">
                  <Skull className="w-4 h-4 mr-1" />
                  Wanted
                </Button>
              </Link>
              <Link to="/contested">
                <Button size="sm" className="w-full bg-rose-800 hover:bg-rose-900" data-testid="dashboard-contested-btn">
                  <Flag className="w-4 h-4 mr-1" />
                  Contested
                </Button>
              </Link>
              <Link to="/marketplace" className="col-span-2">
                <Button size="sm" className="w-full bg-green-600 hover:bg-green-700">
                  <ShoppingBag className="w-4 h-4 mr-1" />
                  Shop
                </Button>
              </Link>
            </div>
          </div>
        </div>

        {/* Characters & Transactions */}
        <div className="grid lg:grid-cols-2 gap-6">
          {/* Characters */}
          <div className="glass-dark p-6 rounded-xl">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-2xl font-bold text-purple-300">Your Characters</h2>
              <Link to="/characters">
                <Button size="sm" variant="outline" className="border-purple-500/50">View All</Button>
              </Link>
            </div>
            {characters.length === 0 ? (
              <div className="text-center py-8">
                <p className="text-gray-400 mb-4">No characters yet. Create your first legend!</p>
                <Link to="/characters">
                  <Button className="bg-gradient-to-r from-purple-600 to-pink-600">Create Character</Button>
                </Link>
              </div>
            ) : (
              <div className="space-y-3">
                {characters.slice(0, 3).map((char) => (
                  <div key={char.id} className="glass p-4 rounded-lg" data-testid={`character-${char.id}`}>
                    <div className="flex items-center justify-between">
                      <div>
                        <h3 className="font-bold text-white">{char.name}</h3>
                        <p className="text-sm text-gray-400">{char.race} • {char.character_class}</p>
                        <p className="text-xs text-purple-400">{char.nation}</p>
                        {factionsByChar[char.id] && (
                          <div className="mt-2">
                            <FactionBadge faction={factionsByChar[char.id]} size="sm" showRank />
                          </div>
                        )}
                      </div>
                      <div className="text-right">
                        <p className="text-sm text-gray-400">Level {char.level}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Recent Transactions */}
          <div className="glass-dark p-6 rounded-xl">
            <h2 className="text-2xl font-bold text-purple-300 mb-4">Recent Transactions</h2>
            {transactions.length === 0 ? (
              <div className="text-center py-8 text-gray-400">
                No transactions yet
              </div>
            ) : (
              <div className="space-y-3">
                {transactions.map((trans) => (
                  <div key={trans.id} className="glass p-4 rounded-lg flex items-center justify-between" data-testid={`transaction-${trans.id}`}>
                    <div className="flex items-center gap-3">
                      {trans.amount > 0 ? (
                        <TrendingUp className="w-5 h-5 text-green-400" />
                      ) : (
                        <TrendingDown className="w-5 h-5 text-red-400" />
                      )}
                      <div>
                        <p className="text-white text-sm">{trans.description}</p>
                        <p className="text-xs text-gray-500">{new Date(trans.created_at).toLocaleDateString()}</p>
                      </div>
                    </div>
                    <div className={`font-bold ${trans.amount > 0 ? 'text-green-400' : 'text-red-400'}`}>
                      {trans.amount > 0 ? '+' : ''}{trans.amount}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;