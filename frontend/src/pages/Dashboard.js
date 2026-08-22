import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { getMe, getMyCharacters, getTransactions } from '../utils/api';
import FactionBadge from '../components/factions/FactionBadge';
import useFactionBadges from '../hooks/useFactionBadges';
import AnimatedBackground from '../components/AnimatedBackground';
import Navbar from '../components/Navbar';
import { Button } from '../components/ui/button';
import { Coins, Scroll, Sword, ShoppingBag, TrendingUp, TrendingDown, Users, Skull, Flag } from 'lucide-react';
import { toast } from 'sonner';

const Dashboard = () => {
  const [user, setUser] = useState(null);
  const [characters, setCharacters] = useState([]);
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);

  // Visibility pass — fetch faction badges for the user's characters.
  const factionsByChar = useFactionBadges(characters.map((c) => c.id));

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    // allSettled so a transient failure of any one source (e.g. transactions
    // API blip) doesn't wipe out the others. Previously a single failure made
    // the whole dashboard show "Failed to load" with no characters listed.
    const [userRes, charRes, transRes] = await Promise.allSettled([
      getMe(),
      getMyCharacters(),
      getTransactions()
    ]);
    if (userRes.status === 'fulfilled') setUser(userRes.value.data);
    if (charRes.status === 'fulfilled') setCharacters(charRes.value.data);
    if (transRes.status === 'fulfilled') setTransactions(transRes.value.data.slice(0, 5));
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
      
      <div className="relative z-10 container mx-auto px-4 py-8">
        {/* Welcome Header */}
        <div className="glass-dark p-8 rounded-2xl mb-8" data-testid="dashboard-header">
          <h1 className="text-4xl font-bold mb-2 text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-pink-600">
            Welcome back, {user?.username}!
          </h1>
          <p className="text-gray-400">Your adventure in Delarom continues...</p>
        </div>

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