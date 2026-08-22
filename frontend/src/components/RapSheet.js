import React, { useEffect, useState } from 'react';
import api from '../utils/api';
import { toast } from 'sonner';
import { Button } from './ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from './ui/dialog';
import { Scale, Lock, Coins, AlertTriangle, Loader2 } from 'lucide-react';

/**
 * RapSheet — read-only view of a character's open crimes, bounties per nation,
 * and active imprisonment. Opened from a button on the Character page.
 */
const SEVERITY_COLORS = {
  petty:    'bg-yellow-900/30 text-yellow-200 border-yellow-500/30',
  minor:    'bg-orange-900/30 text-orange-200 border-orange-500/30',
  major:    'bg-red-900/30 text-red-200 border-red-500/30',
  capital:  'bg-rose-900/40 text-rose-100 border-rose-500/50',
  regicide: 'bg-fuchsia-900/40 text-fuchsia-100 border-fuchsia-500/50',
};

const RapSheet = ({ open, onOpenChange, character }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (open && character?.id) fetchRapSheet();
    // eslint-disable-next-line
  }, [open, character?.id]);

  const fetchRapSheet = async () => {
    if (!character?.id) return;
    setLoading(true);
    try {
      const res = await api.get(`/characters/${character.id}/rap-sheet`);
      setData(res.data);
    } catch (err) {
      console.error('Failed to fetch rap sheet:', err);
      toast.error('Failed to load rap sheet');
    } finally {
      setLoading(false);
    }
  };

  const openCrimes = (data?.crimes || []).filter((c) => c.status === 'open');
  const resolvedCrimes = (data?.crimes || []).filter((c) => c.status !== 'open');

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className="bg-gray-900 border-amber-500/30 text-white max-w-3xl max-h-[90vh] overflow-y-auto"
        data-testid="rap-sheet-modal"
      >
        <DialogHeader>
          <DialogTitle className="text-2xl text-amber-300 flex items-center gap-2">
            <Scale className="w-6 h-6" />
            Rap Sheet — {character?.name || ''}
          </DialogTitle>
          <DialogDescription className="text-sm text-gray-400">
            Crimes recorded, bounties posted, and any active imprisonment for this character.
          </DialogDescription>
        </DialogHeader>

        {loading && (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-6 h-6 animate-spin text-amber-300" />
          </div>
        )}

        {!loading && data && (
          <div className="space-y-5">
            {/* Imprisonment banner */}
            {data.imprisonment && (
              <div className="p-4 border border-red-500/50 bg-red-900/20 rounded-lg flex items-start gap-3" data-testid="rap-imprisonment">
                <Lock className="w-6 h-6 text-red-300 flex-shrink-0 mt-1" />
                <div>
                  <p className="font-bold text-red-200">
                    INCARCERATED in {data.imprisonment.jail_location}, {data.imprisonment.nation}
                  </p>
                  <p className="text-sm text-red-100/80 mt-1">
                    Sentence served: {data.imprisonment.turns_served} / {data.imprisonment.sentence_turns} turns
                  </p>
                  {data.imprisonment.narration && (
                    <p className="text-xs italic text-red-100/70 mt-2">
                      “{data.imprisonment.narration}”
                    </p>
                  )}
                </div>
              </div>
            )}

            {/* Active bounties per nation */}
            {data.bounties.length > 0 && (
              <div data-testid="rap-bounties">
                <h3 className="text-sm uppercase tracking-widest text-amber-300/80 mb-2 flex items-center gap-2">
                  <Coins className="w-4 h-4" /> Active Bounties
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {data.bounties.map((b) => (
                    <div key={b.nation} className="p-3 rounded-lg border border-amber-500/30 bg-amber-900/10">
                      <p className="text-amber-200 font-semibold capitalize">{b.nation}</p>
                      <p className="text-xs text-gray-300">
                        {b.total_bounty.toLocaleString()}g — {b.open_crime_count} open crime{b.open_crime_count === 1 ? '' : 's'} (worst: {b.worst_severity})
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Open crimes */}
            <div>
              <h3 className="text-sm uppercase tracking-widest text-red-300/80 mb-2 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4" /> Open Crimes ({openCrimes.length})
              </h3>
              {openCrimes.length === 0 ? (
                <p className="text-sm text-gray-400 italic">No open charges. Walk freely.</p>
              ) : (
                <div className="space-y-2" data-testid="rap-open-crimes">
                  {openCrimes.map((c) => (
                    <CrimeRow key={c.id} crime={c} />
                  ))}
                </div>
              )}
            </div>

            {/* Resolved crimes (collapsed style) */}
            {resolvedCrimes.length > 0 && (
              <details className="text-sm">
                <summary className="cursor-pointer text-gray-400 hover:text-gray-200">
                  Resolved Crimes ({resolvedCrimes.length})
                </summary>
                <div className="space-y-2 mt-2" data-testid="rap-resolved-crimes">
                  {resolvedCrimes.map((c) => (
                    <CrimeRow key={c.id} crime={c} dimmed />
                  ))}
                </div>
              </details>
            )}

            {!data.law_system_enabled && (
              <p className="text-xs text-gray-500">
                Law system is currently disabled by an administrator.
              </p>
            )}
          </div>
        )}

        <Button
          type="button"
          onClick={() => onOpenChange(false)}
          className="mt-3 w-full bg-amber-600/20 border border-amber-500/30 text-amber-200 hover:bg-amber-600/40"
        >
          Close
        </Button>
      </DialogContent>
    </Dialog>
  );
};

const CrimeRow = ({ crime, dimmed = false }) => (
  <div
    className={`p-3 rounded-lg border ${SEVERITY_COLORS[crime.severity] || SEVERITY_COLORS.minor} ${dimmed ? 'opacity-60' : ''}`}
    data-testid={`rap-crime-${crime.id}`}
  >
    <div className="flex items-center justify-between gap-2">
      <p className="font-semibold capitalize">
        {crime.crime_type.replaceAll('_', ' ')}
        <span className="ml-2 text-xs uppercase tracking-widest opacity-80">[{crime.severity}]</span>
      </p>
      <p className="text-sm font-mono">{crime.bounty.toLocaleString()}g</p>
    </div>
    <p className="text-xs mt-1 opacity-90">
      {crime.victim_name ? `Against ${crime.victim_name} (${crime.victim_importance})` : '(no named victim)'}
      <span className="ml-2 opacity-70">· in {crime.location}, {crime.nation}</span>
    </p>
    {crime.description && (
      <p className="text-xs italic mt-1 opacity-80">{crime.description}</p>
    )}
    {crime.status !== 'open' && (
      <p className="text-[10px] uppercase tracking-widest mt-2 opacity-70">
        {crime.status}{crime.resolved_reason ? ` — ${crime.resolved_reason}` : ''}
      </p>
    )}
  </div>
);

export default RapSheet;
