import React, { useEffect, useState, useCallback } from 'react';
import {
  Users, Shield, Swords, Skull, TreePine, Hammer, Crown, ScrollText, Flame,
} from 'lucide-react';
import { listFactionNpcs, factionTick } from '../../utils/api';

const ICONS = { shield: Shield, swords: Swords, skull: Skull, tree: TreePine, hammer: Hammer, crown: Crown, scroll: ScrollText, flame: Flame };

/**
 * NPC roster panel — read-only listing of in-world NPC members of a faction.
 * Opportunistically nudges the world-tick on mount (backend self-throttles to
 * once per 6h) so player-founded factions feel like they slowly grow.
 */
const FactionNpcRosterTab = ({ slug, faction }) => {
  const [npcs, setNpcs] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await listFactionNpcs(slug);
      setNpcs(r.data || []);
    } finally { setLoading(false); }
  }, [slug]);

  useEffect(() => {
    load();
    // Lazy tick — fire-and-forget, server-side throttle handles spam.
    factionTick(slug).catch(() => {});
  }, [load, slug]);

  if (loading) return <p className="text-gray-500 italic text-center py-8">Calling the roll…</p>;

  if (npcs.length === 0) {
    return (
      <div data-testid="faction-npcs-tab">
        <p className="text-gray-500 italic text-center py-10" data-testid="npcs-empty">
          No NPC members have yet sworn to {faction?.name || 'this faction'}.
          {faction?.founded_by_user_id
            ? ' Player-founded factions seed three founding members at approval.'
            : ' Starter factions have not been peopled with NPCs.'}
        </p>
      </div>
    );
  }

  const officers = npcs.filter((n) => n.rank === 'officer');
  const members = npcs.filter((n) => n.rank !== 'officer');

  const Card = ({ n }) => {
    const color = faction?.color_hex || '#a855f7';
    const Icon = ICONS[faction?.icon] || Shield;
    return (
      <li
        className="rounded-lg border border-gray-700/40 bg-black/30 p-4"
        data-testid={`npc-card-${n.id}`}
      >
        <header className="flex items-start gap-3">
          <div
            className="p-2 rounded-lg flex-shrink-0"
            style={{ backgroundColor: `${color}22`, border: `1px solid ${color}66` }}
          >
            <Icon className="w-4 h-4" style={{ color }} />
          </div>
          <div className="min-w-0 flex-1">
            <h4 className="font-bold text-gray-100 truncate" style={{ fontFamily: 'Georgia, serif' }}>
              {n.name}
            </h4>
            <p className="text-xs uppercase tracking-wider text-amber-300/80">
              {n.title}{n.rank === 'officer' ? ' · Officer' : ''}
            </p>
          </div>
        </header>
        <p className="text-sm text-gray-200 mt-2 leading-snug">{n.bio}</p>
        {n.personality && (
          <p className="text-xs italic text-gray-400 mt-2">— {n.personality}</p>
        )}
      </li>
    );
  };

  return (
    <div data-testid="faction-npcs-tab">
      <div className="flex items-start justify-between mb-4 gap-3">
        <p className="text-xs text-gray-400 italic max-w-md">
          Sworn members of the faction who go about their own business in the world.
          They occasionally answer threads and take up open commissions on their own —
          treasury and reputation grow with them.
        </p>
        <span className="text-xs text-gray-500 inline-flex items-center gap-1">
          <Users className="w-3 h-3" /> {npcs.length} sworn
        </span>
      </div>

      {officers.length > 0 && (
        <section className="mb-5">
          <h3 className="text-xs uppercase tracking-[0.2em] text-amber-300 mb-2">Officers</h3>
          <ul className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {officers.map((n) => <Card key={n.id} n={n} />)}
          </ul>
        </section>
      )}
      {members.length > 0 && (
        <section>
          <h3 className="text-xs uppercase tracking-[0.2em] text-gray-300 mb-2">Sworn Members</h3>
          <ul className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {members.map((n) => <Card key={n.id} n={n} />)}
          </ul>
        </section>
      )}
    </div>
  );
};

export default FactionNpcRosterTab;
