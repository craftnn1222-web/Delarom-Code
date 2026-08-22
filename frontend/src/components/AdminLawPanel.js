import React, { useEffect, useState } from 'react';
import api from '../utils/api';
import { toast } from 'sonner';
import { Button } from './ui/button';
import { Card } from './ui/card';
import { Loader2, Scale, Lock, Gavel, X } from 'lucide-react';

/**
 * AdminLawPanel — admin tab for monitoring + intervening in the law system.
 * Lists open crimes (filterable by status) and active imprisonments, with
 * pardon / expunge / release actions.
 */
const AdminLawPanel = () => {
  const [crimes, setCrimes] = useState([]);
  const [imprisonments, setImprisonments] = useState([]);
  const [loading, setLoading] = useState(false);
  const [statusFilter, setStatusFilter] = useState('open');

  const fetchData = async () => {
    setLoading(true);
    try {
      const [crimesRes, impsRes] = await Promise.all([
        api.get(`/admin/crimes${statusFilter ? `?status=${statusFilter}` : ''}`),
        api.get('/admin/imprisonments'),
      ]);
      setCrimes(crimesRes.data || []);
      setImprisonments(impsRes.data || []);
    } catch (err) {
      console.error('Failed to load law panel:', err);
      toast.error('Failed to load law data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    // eslint-disable-next-line
  }, [statusFilter]);

  const handlePardon = async (crime) => {
    if (!window.confirm(`Pardon ${crime.character_name}'s ${crime.crime_type} (${crime.severity})?`)) return;
    try {
      await api.post(`/admin/crimes/${crime.id}/pardon`, { reason: 'Admin pardon via panel' });
      toast.success('Crime pardoned');
      await fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Pardon failed');
    }
  };

  const handleExpunge = async (crime) => {
    if (!window.confirm(`Expunge this record permanently? It will be erased from history.`)) return;
    try {
      await api.delete(`/admin/crimes/${crime.id}`);
      toast.success('Crime expunged');
      await fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Expunge failed');
    }
  };

  const handleRelease = async (imp) => {
    if (!window.confirm(`Release ${imp.character_name} from ${imp.jail_location}?`)) return;
    try {
      await api.post(`/admin/imprisonments/${imp.id}/release`, {
        status: 'pardoned',
        reason: 'Admin pardon',
      });
      toast.success('Prisoner released');
      await fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Release failed');
    }
  };

  return (
    <div className="space-y-6" data-testid="admin-law-panel">
      <Card className="p-6 bg-black/30 border-amber-500/30">
        <h2 className="text-2xl font-bold text-amber-300 flex items-center gap-2 mb-4">
          <Lock className="w-6 h-6" /> Active Imprisonments ({imprisonments.length})
        </h2>
        {imprisonments.length === 0 ? (
          <p className="text-sm text-gray-400 italic">No one is currently imprisoned.</p>
        ) : (
          <div className="space-y-2">
            {imprisonments.map((imp) => (
              <div key={imp.id} className="p-3 rounded-lg border border-red-500/30 bg-red-900/15 flex items-center justify-between gap-3" data-testid={`imp-row-${imp.id}`}>
                <div>
                  <p className="text-red-200 font-semibold">
                    {imp.character_name} — {imp.jail_location} ({imp.nation})
                  </p>
                  <p className="text-xs text-red-100/70">
                    Served {imp.turns_served} / {imp.sentence_turns} turns · {imp.crime_ids?.length || 0} crime(s) consumed
                  </p>
                </div>
                <Button
                  type="button"
                  onClick={() => handleRelease(imp)}
                  className="bg-amber-600/30 border border-amber-500/40 hover:bg-amber-600/50 text-amber-100 text-sm"
                  data-testid={`release-${imp.id}`}
                >
                  <X className="w-3 h-3 mr-1" /> Release
                </Button>
              </div>
            ))}
          </div>
        )}
      </Card>

      <Card className="p-6 bg-black/30 border-rose-500/30">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-2xl font-bold text-rose-300 flex items-center gap-2">
            <Scale className="w-6 h-6" /> Crimes ({crimes.length})
          </h2>
          <div className="flex gap-2">
            {['open', 'served', 'paid', 'pardoned', 'expunged', ''].map((s) => (
              <button
                key={s || 'all'}
                onClick={() => setStatusFilter(s)}
                className={`text-xs px-2 py-1 rounded-full border ${statusFilter === s ? 'bg-rose-600/40 border-rose-400 text-white' : 'bg-black/30 border-gray-600/30 text-gray-400 hover:text-white'}`}
                data-testid={`law-filter-${s || 'all'}`}
              >
                {s || 'all'}
              </button>
            ))}
          </div>
        </div>

        {loading && <Loader2 className="w-5 h-5 animate-spin text-rose-300" />}

        {!loading && crimes.length === 0 && (
          <p className="text-sm text-gray-400 italic">No crimes matching this filter.</p>
        )}

        {!loading && crimes.length > 0 && (
          <div className="space-y-2 max-h-[60vh] overflow-y-auto pr-1">
            {crimes.map((c) => (
              <div key={c.id} className="p-3 rounded-lg border border-rose-500/30 bg-rose-900/10" data-testid={`law-crime-${c.id}`}>
                <div className="flex items-center justify-between gap-2">
                  <p className="text-rose-100 font-semibold capitalize">
                    {c.crime_type.replaceAll('_', ' ')}
                    <span className="ml-2 text-[10px] uppercase tracking-widest opacity-70">[{c.severity}]</span>
                    <span className="ml-2 text-[10px] uppercase tracking-widest opacity-70">{c.status}</span>
                  </p>
                  <p className="text-sm font-mono text-rose-200">{c.bounty.toLocaleString()}g</p>
                </div>
                <p className="text-xs text-rose-100/80 mt-1">
                  {c.character_name} · {c.location}, {c.nation} · vs {c.victim_name || '(no victim)'}
                </p>
                {c.description && (
                  <p className="text-xs italic text-rose-100/70 mt-1">{c.description}</p>
                )}
                {c.status === 'open' && (
                  <div className="flex gap-2 mt-2">
                    <Button
                      type="button"
                      onClick={() => handlePardon(c)}
                      className="bg-emerald-600/30 border border-emerald-500/40 hover:bg-emerald-600/50 text-emerald-100 text-xs h-7"
                      data-testid={`pardon-${c.id}`}
                    >
                      <Gavel className="w-3 h-3 mr-1" /> Pardon
                    </Button>
                    <Button
                      type="button"
                      onClick={() => handleExpunge(c)}
                      className="bg-gray-600/30 border border-gray-500/40 hover:bg-gray-600/50 text-gray-100 text-xs h-7"
                      data-testid={`expunge-${c.id}`}
                    >
                      <X className="w-3 h-3 mr-1" /> Expunge
                    </Button>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
};

export default AdminLawPanel;
