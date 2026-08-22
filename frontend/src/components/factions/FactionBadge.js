import React from 'react';
import { Link } from 'react-router-dom';
import {
  Shield, Swords, Skull, TreePine, Hammer, Crown, ScrollText, Flame,
} from 'lucide-react';

/**
 * Tiny coloured pill for a character's faction allegiance. Used everywhere
 * a character name appears (profile page, forum threads, comments, RP scene
 * participants). Renders nothing when the character has no active faction.
 *
 * Props:
 *   faction: { faction_name, faction_slug, icon, color_hex, motto, rank, nation_home } | null
 *   size:    'sm' | 'md'  (default 'sm')
 *   linkTo:  bool         (default true — wraps in <Link> to /factions/:slug)
 *   showRank: bool        (default false — appends rank label if true)
 */

const ICONS = {
  shield: Shield, swords: Swords, skull: Skull, tree: TreePine,
  hammer: Hammer, crown: Crown, scroll: ScrollText, flame: Flame,
};

const SIZE = {
  sm: { pad: 'px-1.5 py-0.5', text: 'text-[10px]', icon: 'w-3 h-3', gap: 'gap-1' },
  md: { pad: 'px-2 py-1',     text: 'text-xs',     icon: 'w-3.5 h-3.5', gap: 'gap-1.5' },
};

const FactionBadge = ({ faction, size = 'sm', linkTo = true, showRank = false }) => {
  if (!faction || !faction.faction_slug) return null;
  const Icon = ICONS[faction.icon] || Shield;
  const s = SIZE[size] || SIZE.sm;
  const color = faction.color_hex || '#888';

  const inner = (
    <span
      className={`inline-flex items-center ${s.gap} ${s.pad} ${s.text} rounded-full font-semibold uppercase tracking-wider whitespace-nowrap`}
      style={{
        backgroundColor: `${color}22`,
        border: `1px solid ${color}66`,
        color,
      }}
      title={faction.motto ? `${faction.faction_name} — "${faction.motto}"` : faction.faction_name}
      data-testid={`faction-badge-${faction.faction_slug}`}
    >
      <Icon className={s.icon} />
      <span>{faction.faction_name}</span>
      {showRank && (
        <span className="opacity-70 normal-case font-normal">· {faction.rank}</span>
      )}
    </span>
  );

  if (!linkTo) return inner;

  return (
    <Link
      to={`/factions/${faction.faction_slug}`}
      onClick={(e) => e.stopPropagation()}
      className="hover:opacity-80 transition-opacity"
    >
      {inner}
    </Link>
  );
};

export default FactionBadge;
