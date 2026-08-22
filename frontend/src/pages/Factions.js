import React, { useEffect, useState, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { Shield, Users, Flame, Skull, TreePine, Hammer, Crown, ScrollText, Plus, Hourglass } from 'lucide-react';
import { listFactions, getMyFactionMemberships, getMyCharters } from '../utils/api';
import AnimatedBackground from '../components/AnimatedBackground';
import Navbar from '../components/Navbar';
import { useAuth } from '../contexts/AuthContext';
import { Button } from '../components/ui/button';
import CharterFactionDialog from '../components/factions/CharterFactionDialog';

const ICONS = {
  shield:  Shield,
  swords:  Shield, // fallback — Swords-from-lucide already used elsewhere
  skull:   Skull,
  tree:    TreePine,
  hammer:  Hammer,
  crown:   Crown,
  scroll:  ScrollText,
  flame:   Flame,
};

const Factions = () => {
  const { currentUser } = useAuth();
  const [factions, setFactions] = useState([]);
  const [myMemberships, setMyMemberships] = useState([]);
  const [myCharters, setMyCharters] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCharter, setShowCharter] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const tasks = [listFactions()];
      if (currentUser) {
        tasks.push(getMyFactionMemberships());
        tasks.push(getMyCharters());
      }
      const results = await Promise.allSettled(tasks);
      if (results[0].status === 'fulfilled') setFactions(results[0].value.data);
      if (results[1] && results[1].status === 'fulfilled') setMyMemberships(results[1].value.data);
      if (results[2] && results[2].status === 'fulfilled') setMyCharters(results[2].value.data);
    } finally {
      setLoading(false);
    }
  }, [currentUser]);

  useEffect(() => { load(); }, [load]);

  // Map faction_id → my membership for quick lookup
  const memberOfId = new Map(myMemberships.map((m) => [m.faction_id, m]));

  return (
    <div className="min-h-screen relative">
      <AnimatedBackground />
      <Navbar />

      <div className="relative z-10 container mx-auto px-4 py-10 max-w-6xl">
        <header className="mb-8 text-center">
          <div className="inline-flex items-center gap-3 mb-2">
            <Shield className="w-7 h-7 text-purple-300" />
            <h1 className="text-4xl sm:text-5xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-purple-200 via-pink-200 to-amber-200" style={{ fontFamily: 'Georgia, serif' }}>
              The Factions
            </h1>
            <Shield className="w-7 h-7 text-purple-300 scale-x-[-1]" />
          </div>
          <p className="text-gray-400 max-w-2xl mx-auto italic text-sm">
            Guilds, courts, cults, and companies. Pledge a character to one — rise through its ranks,
            answer its calls, share in its glory or its doom.
          </p>
          {currentUser && (
            <div className="mt-4">
              <Button
                onClick={() => setShowCharter(true)}
                className="bg-gradient-to-r from-amber-600 to-orange-600"
                data-testid="found-faction-btn"
              >
                <Plus className="w-4 h-4 mr-1" />
                Found Your Own Faction
              </Button>
            </div>
          )}
        </header>

        {/* Pending charter status */}
        {myCharters.some((c) => c.status === 'pending') && (
          <div className="mb-6 glass-dark border border-amber-500/40 rounded-xl p-4" data-testid="my-pending-charter">
            <div className="flex items-start gap-3">
              <Hourglass className="w-5 h-5 text-amber-300 mt-0.5 animate-pulse" />
              <div className="flex-1">
                <p className="text-xs uppercase tracking-widest text-amber-300">Charter in Council Review</p>
                {myCharters.filter((c) => c.status === 'pending').map((c) => (
                  <p key={c.id} className="text-amber-100 mt-1">
                    Your charter for <strong>{c.name}</strong> was filed {new Date(c.created_at).toLocaleDateString()}.
                    The council will speak soon.
                  </p>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Rejection notes for review */}
        {myCharters.some((c) => c.status === 'rejected') && (
          <div className="mb-6 glass-dark border border-red-500/40 rounded-xl p-4" data-testid="my-rejected-charters">
            <p className="text-xs uppercase tracking-widest text-red-300 mb-2">Charters Returned by the Council</p>
            <ul className="space-y-1">
              {myCharters.filter((c) => c.status === 'rejected').slice(0, 3).map((c) => (
                <li key={c.id} className="text-sm text-red-100">
                  <strong>{c.name}</strong> — refunded {c.refunded || 0} gold.
                  {c.review_note && <span className="text-gray-400 italic"> &ldquo;{c.review_note}&rdquo;</span>}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* My memberships banner */}
        {currentUser && myMemberships.length > 0 && (
          <div className="mb-6 glass-dark border border-amber-500/30 rounded-xl p-4" data-testid="my-factions-banner">
            <p className="text-xs uppercase tracking-[0.3em] text-amber-300 mb-2">Your Standing</p>
            <div className="flex flex-wrap gap-2">
              {myMemberships.map((m) => (
                <Link
                  key={m.id}
                  to={`/factions/${m.faction_slug}`}
                  className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-amber-900/40 border border-amber-600/50 text-sm hover:bg-amber-900/60"
                  data-testid={`my-faction-pill-${m.faction_slug}`}
                >
                  <span className="text-amber-200 font-semibold">{m.character_name}</span>
                  <span className="text-gray-400">·</span>
                  <span className="text-amber-100">{m.faction_name}</span>
                  <span className="text-amber-300/70 text-xs uppercase tracking-wide">({m.rank})</span>
                </Link>
              ))}
            </div>
          </div>
        )}

        {loading ? (
          <p className="text-gray-500 italic text-center py-12">The heralds are gathering the rolls…</p>
        ) : factions.length === 0 ? (
          <p className="text-gray-500 italic text-center py-12">No factions have yet been raised in this realm.</p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5" data-testid="faction-grid">
            {factions.map((f) => {
              const Icon = ICONS[f.icon] || Shield;
              const mine = memberOfId.get(f.id);
              return (
                <Link
                  key={f.id}
                  to={`/factions/${f.slug}`}
                  data-testid={`faction-card-${f.slug}`}
                  className="glass-dark rounded-xl border border-purple-500/30 p-5 hover:border-purple-300/60 hover:bg-stone-900/50 transition group"
                  style={{ borderTop: `4px solid ${f.color_hex || '#a855f7'}` }}
                >
                  <div className="flex items-start gap-3 mb-3">
                    <div
                      className="p-2.5 rounded-lg flex-shrink-0"
                      style={{ backgroundColor: `${f.color_hex || '#a855f7'}22`, border: `1px solid ${f.color_hex || '#a855f7'}66` }}
                    >
                      <Icon className="w-5 h-5" style={{ color: f.color_hex || '#a855f7' }} />
                    </div>
                    <div className="min-w-0 flex-1">
                      <h3 className="text-lg font-bold text-gray-100 leading-tight group-hover:text-white" style={{ fontFamily: 'Georgia, serif' }}>
                        {f.name}
                      </h3>
                      {f.motto && (
                        <p className="text-xs italic text-gray-400 leading-snug mt-0.5">&ldquo;{f.motto}&rdquo;</p>
                      )}
                    </div>
                  </div>

                  <p className="text-sm text-gray-300 line-clamp-3 mb-4">{f.description}</p>

                  <div className="flex items-center justify-between text-xs text-gray-400">
                    <span className="inline-flex items-center gap-1">
                      <Users className="w-3 h-3" />
                      {f.member_count || 0} {f.member_count === 1 ? 'member' : 'members'}
                    </span>
                    {f.nation_home && (
                      <span className="uppercase tracking-wider">{f.nation_home.replace('-', ' ')}</span>
                    )}
                  </div>

                  {mine && (
                    <div className="mt-3 pt-3 border-t border-amber-700/30 text-xs text-amber-300">
                      You are a <strong className="uppercase tracking-wide">{mine.rank}</strong> here ({mine.character_name})
                    </div>
                  )}
                </Link>
              );
            })}
          </div>
        )}
      </div>
      <CharterFactionDialog
        open={showCharter}
        onClose={() => setShowCharter(false)}
        onSuccess={load}
        currentUserGold={currentUser?.currency || 0}
      />
    </div>
  );
};

export default Factions;
