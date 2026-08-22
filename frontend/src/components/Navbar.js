import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { getMe } from '../utils/api';
import { useAuth } from '../contexts/AuthContext';
import { Button } from './ui/button';
import { Coins, User, LogOut, Sword, ShoppingBag, MessageSquare, Scroll, CheckSquare, Map, Shield, Users as UsersIcon, BookOpen, Feather, Settings as SettingsIcon, TrendingUp, Sparkles, Swords, Skull, Flag } from 'lucide-react';
const Navbar = () => {
  const navigate = useNavigate();
  const { logout } = useAuth();
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [worldDate, setWorldDate] = useState(null);

  useEffect(() => {
    fetchUser();
    fetchWorldDate();
    const id = setInterval(fetchWorldDate, 60_000);   // refresh once a minute
    return () => clearInterval(id);
  }, []);

  const fetchUser = async () => {
    try {
      const response = await getMe();
      setUser(response.data);
    } catch (error) {
      console.error('Failed to fetch user:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchWorldDate = async () => {
    try {
      const r = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/world/calendar`);
      if (r.ok) setWorldDate(await r.json());
    } catch { /* silent — pill will fall back to '215 A.E.' */ }
  };

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  if (loading) return null;

  return (
    <nav className="glass-dark border-b border-purple-500/30">
      <div className="container mx-auto px-4 py-4">
        <div className="flex items-center justify-between gap-4">
          <Link to="/dashboard" className="flex flex-col whitespace-nowrap flex-shrink-0">
            <span className="text-2xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-pink-600">
              Continents of Delarom
            </span>
            <span
              className="text-[10px] tracking-[0.35em] text-amber-300/80 -mt-1"
              data-testid="world-clock-pill"
              title={worldDate?.formatted}
            >
              · {worldDate?.compact || '215 A.E.'} ·
            </span>
          </Link>

          <div className="flex items-center gap-5 text-sm flex-wrap justify-end">
            <Link to="/dashboard" className="text-gray-300 hover:text-white transition flex items-center gap-2 whitespace-nowrap">
              <User className="w-4 h-4" />
              Dashboard
            </Link>
            <Link to="/characters" className="text-gray-300 hover:text-white transition flex items-center gap-2 whitespace-nowrap">
              <Scroll className="w-4 h-4" />
              Characters
            </Link>
            <Link to="/quests" className="text-gray-300 hover:text-white transition flex items-center gap-2 whitespace-nowrap">
              <Sword className="w-4 h-4" />
              Quest Board
            </Link>
            <Link to="/my-quests" className="text-gray-300 hover:text-white transition flex items-center gap-2 whitespace-nowrap">
              <CheckSquare className="w-4 h-4" />
              My Quests
            </Link>
            <Link to="/marketplace" className="text-gray-300 hover:text-white transition flex items-center gap-2 whitespace-nowrap">
              <ShoppingBag className="w-4 h-4" />
              Marketplace
            </Link>
            <Link to="/forums" className="text-gray-300 hover:text-white transition flex items-center gap-2 whitespace-nowrap">
              <MessageSquare className="w-4 h-4" />
              Forums
            </Link>
            <Link to="/nations" className="text-gray-300 hover:text-white transition flex items-center gap-2 whitespace-nowrap">
              <Map className="w-4 h-4" />
              Nations
            </Link>
            <Link to="/members" className="text-gray-300 hover:text-white transition flex items-center gap-2 whitespace-nowrap">
              <UsersIcon className="w-4 h-4" />
              Members
            </Link>
            <Link to="/factions" className="text-purple-200 hover:text-purple-100 transition flex items-center gap-2 whitespace-nowrap" data-testid="nav-factions">
              <Shield className="w-4 h-4" />
              Factions
            </Link>
            <Link to="/quill-and-coffer" className="text-amber-300 hover:text-amber-200 transition flex items-center gap-2 whitespace-nowrap" data-testid="nav-quill-and-coffer">
              <Feather className="w-4 h-4" />
              Quill &amp; Coffer
            </Link>
            <Link to="/markets" className="text-amber-300 hover:text-amber-200 transition flex items-center gap-2 whitespace-nowrap" data-testid="nav-markets">
              <TrendingUp className="w-4 h-4" />
              Markets
            </Link>
            <Link to="/prayers" className="text-emerald-300 hover:text-emerald-200 transition flex items-center gap-2 whitespace-nowrap" data-testid="nav-prayers">
              <Sparkles className="w-4 h-4" />
              Prayers
            </Link>
            <Link to="/tongue-of-yros" className="text-orange-300 hover:text-orange-200 transition flex items-center gap-2 whitespace-nowrap" data-testid="nav-tongue-of-yros">
              <Swords className="w-4 h-4" />
              Tongue of Y&apos;ros
            </Link>
            <Link to="/wanted" className="text-red-300 hover:text-red-200 transition flex items-center gap-2 whitespace-nowrap" data-testid="nav-wanted">
              <Skull className="w-4 h-4" />
              Wanted
            </Link>
            <Link to="/contested" className="text-rose-300 hover:text-rose-200 transition flex items-center gap-2 whitespace-nowrap" data-testid="nav-contested">
              <Flag className="w-4 h-4" />
              Contested
            </Link>
            <Link to="/t1-tutorial" className="text-yellow-400 hover:text-yellow-300 transition flex items-center gap-2 whitespace-nowrap">
              <BookOpen className="w-4 h-4" />
              T1 Guide
            </Link>
            {user && (user.role === 'admin' || user.role === 'moderator') && (
              <Link to="/admin" className="text-purple-400 hover:text-purple-300 transition flex items-center gap-2 font-bold whitespace-nowrap">
                <Shield className="w-4 h-4" />
                Admin
              </Link>
            )}
          </div>

          <div className="flex items-center gap-3 flex-shrink-0">
            {user && (
              <div className="glass px-4 py-2 rounded-lg flex items-center gap-2 text-yellow-400">
                <Coins className="w-5 h-5" />
                <span className="font-bold">{user.currency}</span>
              </div>
            )}
            <Link
              to="/settings"
              className="text-gray-400 hover:text-white transition flex items-center"
              title="Account Settings"
              data-testid="navbar-settings-link"
            >
              <SettingsIcon className="w-5 h-5" />
            </Link>
            <Button onClick={handleLogout} variant="outline" className="border-red-500/50 hover:bg-red-500/20">
              <LogOut className="w-4 h-4 mr-2" />
              Logout
            </Button>
          </div>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;
