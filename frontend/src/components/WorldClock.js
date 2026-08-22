import React from 'react';
import { Sun, Sunset, Sunrise, Moon, Sparkles } from 'lucide-react';

/**
 * WorldClock — displays the current in-world Delarom date, time-of-day,
 * and any active festivals in this nation.
 *
 * Renders nothing if `clock` is missing. Defensive against partial data.
 */

const ICON_MAP = {
  sunrise: Sunrise,
  sun: Sun,
  sunset: Sunset,
  moon: Moon,
};

const PHASE_TINT = {
  dawn:      'border-amber-400/40   bg-amber-900/15  text-amber-100',
  morning:   'border-yellow-400/40  bg-yellow-900/10 text-yellow-50',
  midday:    'border-yellow-300/50  bg-yellow-700/15 text-yellow-50',
  afternoon: 'border-orange-400/40  bg-orange-900/15 text-orange-50',
  dusk:      'border-rose-400/50    bg-rose-900/20   text-rose-50',
  night:     'border-indigo-400/40  bg-indigo-900/30 text-indigo-100',
};

const WorldClock = ({ clock, festivals = [] }) => {
  if (!clock || !clock.time_of_day) return null;

  const phase = clock.time_of_day.phase || 'day';
  const iconKey = clock.time_of_day.icon || 'sun';
  const Icon = ICON_MAP[iconKey] || Sun;
  const tint = PHASE_TINT[phase] || PHASE_TINT.midday;
  const vibe = clock.time_of_day.vibe || '';

  return (
    <div
      className={`p-3 rounded-xl border ${tint} flex flex-col sm:flex-row sm:items-center gap-3`}
      data-testid="world-clock"
    >
      <div className="flex items-center gap-3 flex-shrink-0">
        <Icon className="w-6 h-6" />
        <div>
          <p className="text-xs uppercase tracking-widest opacity-80">
            {clock.delarom_date}
          </p>
          <p className="font-bold capitalize" data-testid="world-clock-phase">
            {phase}
          </p>
        </div>
      </div>
      {vibe && (
        <p className="text-sm italic opacity-90 flex-1 min-w-0">
          {vibe}
        </p>
      )}

      {festivals.length > 0 && (
        <div
          className="flex items-center gap-2 px-3 py-2 rounded-lg bg-black/30 border border-purple-400/40 text-purple-100 flex-shrink-0"
          data-testid="active-festivals"
        >
          <Sparkles className="w-4 h-4 text-purple-300" />
          <div>
            <p className="text-[10px] uppercase tracking-widest opacity-80">
              Festival
            </p>
            <p className="text-sm font-bold" data-testid="festival-name">
              {festivals[0].name}
              {festivals.length > 1 && (
                <span className="opacity-70"> +{festivals.length - 1} more</span>
              )}
            </p>
          </div>
        </div>
      )}
    </div>
  );
};

export default WorldClock;
