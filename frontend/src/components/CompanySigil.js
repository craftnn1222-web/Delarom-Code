import React from 'react';
import {
  Coins, Shield, Anchor, Sword, Crown, Hammer, Feather, Ship, Truck,
  Star, Moon, Sun, Flame, Key, Gem, ScrollText, Package, Sparkles,
} from 'lucide-react';

/**
 * Trade-company sigil registry. Founders pick one at charter, plus a house
 * colour. Each entry maps a slug → a lucide icon component. Keep the list
 * short and readable — sigils should feel curated, not generic.
 */
export const SIGIL_OPTIONS = [
  { slug: 'coins',    label: 'Coin Purse',      Icon: Coins },
  { slug: 'shield',   label: 'Warded Shield',   Icon: Shield },
  { slug: 'anchor',   label: 'Salted Anchor',   Icon: Anchor },
  { slug: 'sword',    label: 'Legion Blade',    Icon: Sword },
  { slug: 'crown',    label: 'Crown Mint',      Icon: Crown },
  { slug: 'hammer',   label: 'Guild Hammer',    Icon: Hammer },
  { slug: 'feather',  label: 'Scribe Quill',    Icon: Feather },
  { slug: 'ship',     label: 'Trading Cog',     Icon: Ship },
  { slug: 'wagon',    label: 'Overland Wagon',  Icon: Truck },
  { slug: 'star',     label: 'North Star',      Icon: Star },
  { slug: 'moon',     label: 'Moon-Silver',     Icon: Moon },
  { slug: 'sun',      label: 'Aurelion Sun',    Icon: Sun },
  { slug: 'flame',    label: 'Ember-Forge',     Icon: Flame },
  { slug: 'key',      label: 'Vault Key',       Icon: Key },
  { slug: 'gem',      label: 'Cut Gem',         Icon: Gem },
  { slug: 'scroll',   label: 'Charter Scroll',  Icon: ScrollText },
  { slug: 'crate',    label: 'Sealed Crate',    Icon: Package },
  { slug: 'sparkles', label: 'Reagent Vial',    Icon: Sparkles },
];

const SIGIL_LOOKUP = SIGIL_OPTIONS.reduce((acc, s) => { acc[s.slug] = s; return acc; }, {});

/**
 * Render a trade-company sigil. Falls back to the coin purse.
 * Colour is applied inline (the founder's picked house colour).
 */
export const CompanySigil = ({ sigil, color, className = 'w-5 h-5', style = {}, ...rest }) => {
  const entry = SIGIL_LOOKUP[sigil] || SIGIL_LOOKUP.coins;
  const Icon = entry.Icon;
  return (
    <Icon
      className={className}
      style={{ color: color || '#f59e0b', ...style }}
      data-testid={`sigil-${entry.slug}`}
      {...rest}
    />
  );
};

/**
 * Grid picker (18 options) used inside the charter dialog.
 */
export const SigilPicker = ({ value, onChange, color = '#f59e0b' }) => (
  <div className="grid grid-cols-6 gap-2" data-testid="sigil-picker">
    {SIGIL_OPTIONS.map((s) => {
      const Icon = s.Icon;
      const active = value === s.slug;
      return (
        <button
          key={s.slug}
          type="button"
          onClick={() => onChange(s.slug)}
          className={`aspect-square rounded-md border flex items-center justify-center transition ${
            active
              ? 'border-amber-400/70 bg-amber-950/40 shadow-inner'
              : 'border-stone-700 bg-stone-950/60 hover:bg-stone-900'
          }`}
          title={s.label}
          data-testid={`sigil-option-${s.slug}`}
        >
          <Icon className="w-5 h-5" style={{ color: active ? color : '#a8a29e' }} />
        </button>
      );
    })}
  </div>
);

export default CompanySigil;
