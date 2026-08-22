import React, { useEffect, useState, useCallback } from 'react';
import { toast } from 'sonner';
import {
  Shield, Swords, Skull, TreePine, Hammer, Crown, ScrollText, Flame,
  Hourglass, CheckCircle2, XCircle, Loader2, Coins, User as UserIcon,
} from 'lucide-react';
import { adminListCharters, adminApproveCharter, adminRejectCharter } from '../../utils/api';
import { Button } from '../ui/button';
import { Textarea } from '../ui/textarea';

const ICONS = { shield: Shield, swords: Swords, skull: Skull, tree: TreePine, hammer: Hammer, crown: Crown, scroll: ScrollText, flame: Flame };

const CharterReviewTab = () => {
  const [charters, setCharters] = useState([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('pending');
  const [notes, setNotes] = useState({});
  const [busy, setBusy] = useState({});

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await adminListCharters(statusFilter);
      setCharters(r.data || []);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to load charters.');
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => { load(); }, [load]);

  const handle = async (charterId, action) => {
    setBusy((b) => ({ ...b, [charterId]: action }));
    try {
      const note = notes[charterId] || '';
      if (action === 'approve') {
        const r = await adminApproveCharter(charterId, note);
        toast.success(`Approved — ${r.data.faction.name} stands.`);
      } else {
        const r = await adminRejectCharter(charterId, note);
        toast.success(`Rejected — ${r.data.refunded || 0} gold refunded to applicant.`);
      }
      setNotes((n) => ({ ...n, [charterId]: '' }));
      await load();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Action failed.');
    } finally {
      setBusy((b) => ({ ...b, [charterId]: null }));
    }
  };

  return (
    <div className="glass-dark p-6 rounded-xl" data-testid="charter-review-tab">
      <div className="flex items-start justify-between mb-4 flex-wrap gap-3">
        <div>
          <h2 className="text-2xl font-bold text-amber-200" style={{ fontFamily: 'Georgia, serif' }}>
            Faction Charters
          </h2>
          <p className="text-sm text-gray-400">
            Review player applications to found new factions. Approving auto-creates the faction,
            promotes the applicant's character to Leader, and seeds 3 founding NPC members.
            Rejecting refunds the 5,000 gold charter fee.
          </p>
        </div>
        <div className="flex gap-1 bg-black/40 rounded-lg p-1">
          {['pending', 'approved', 'rejected', 'all'].map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => setStatusFilter(s)}
              className={`px-3 py-1 text-xs uppercase tracking-wider rounded transition ${
                statusFilter === s ? 'bg-amber-600 text-white' : 'text-gray-400 hover:text-gray-200'
              }`}
              data-testid={`charter-filter-${s}`}
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <p className="text-gray-500 italic text-center py-12">Reading the petitions…</p>
      ) : charters.length === 0 ? (
        <p className="text-gray-500 italic text-center py-12" data-testid="no-charters">
          No charters under {statusFilter === 'all' ? 'any' : statusFilter} status.
        </p>
      ) : (
        <ul className="space-y-4">
          {charters.map((c) => {
            const Icon = ICONS[c.icon] || Shield;
            const isPending = c.status === 'pending';
            return (
              <li
                key={c.id}
                className="rounded-lg border border-gray-700/50 bg-black/30 p-4"
                data-testid={`charter-row-${c.id}`}
                style={{ borderLeftColor: c.color_hex || '#a855f7', borderLeftWidth: 4 }}
              >
                <div className="flex items-start gap-3 flex-wrap">
                  <div
                    className="p-2.5 rounded-lg flex-shrink-0"
                    style={{ backgroundColor: `${c.color_hex || '#a855f7'}22`, border: `1px solid ${c.color_hex || '#a855f7'}66` }}
                  >
                    <Icon className="w-5 h-5" style={{ color: c.color_hex || '#a855f7' }} />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <h3 className="text-lg font-bold text-amber-100" style={{ fontFamily: 'Georgia, serif' }}>{c.name}</h3>
                      {c.status === 'pending'  && <span className="text-xs px-2 py-0.5 rounded-full bg-amber-900/40 border border-amber-600/60 text-amber-200 inline-flex items-center gap-1"><Hourglass className="w-3 h-3" />Pending</span>}
                      {c.status === 'approved' && <span className="text-xs px-2 py-0.5 rounded-full bg-green-900/40 border border-green-600/60 text-green-200 inline-flex items-center gap-1"><CheckCircle2 className="w-3 h-3" />Approved</span>}
                      {c.status === 'rejected' && <span className="text-xs px-2 py-0.5 rounded-full bg-red-900/40 border border-red-600/60 text-red-200 inline-flex items-center gap-1"><XCircle className="w-3 h-3" />Rejected · {c.refunded || 0}g refunded</span>}
                    </div>
                    {c.motto && <p className="text-sm text-gray-400 italic mt-0.5">&ldquo;{c.motto}&rdquo;</p>}
                    <p className="text-xs text-gray-500 mt-2 flex items-center gap-3 flex-wrap">
                      <span className="inline-flex items-center gap-1"><UserIcon className="w-3 h-3" />{c.applicant_username} as <span className="text-gray-300">{c.character_name}</span></span>
                      {c.nation_home && <span className="uppercase tracking-wider">{c.nation_home.replace('-', ' ')}</span>}
                      <span className="inline-flex items-center gap-1"><Coins className="w-3 h-3" />{c.cost_paid || 0}g paid</span>
                      <span>filed {new Date(c.created_at).toLocaleDateString()}</span>
                      <span className="text-gray-600">slug: {c.slug}</span>
                    </p>
                    <p className="text-sm text-gray-200 mt-3 whitespace-pre-wrap">{c.description}</p>
                    {c.review_note && (
                      <p className="text-xs italic text-gray-400 mt-2 border-l-2 border-gray-700/40 pl-3">
                        Council note: {c.review_note}
                      </p>
                    )}
                  </div>
                </div>

                {isPending && (
                  <div className="mt-3 pt-3 border-t border-gray-700/40 space-y-2">
                    <Textarea
                      value={notes[c.id] || ''}
                      onChange={(e) => setNotes((n) => ({ ...n, [c.id]: e.target.value }))}
                      placeholder="(Optional) Council note to the applicant…"
                      rows={2}
                      maxLength={400}
                      className="bg-black/40 border-gray-600 text-gray-100 text-sm"
                      data-testid={`charter-note-${c.id}`}
                    />
                    <div className="flex gap-2 justify-end">
                      <Button
                        size="sm"
                        variant="outline"
                        disabled={!!busy[c.id]}
                        onClick={() => handle(c.id, 'reject')}
                        className="border-red-500/50 text-red-300 hover:bg-red-900/30"
                        data-testid={`charter-reject-${c.id}`}
                      >
                        {busy[c.id] === 'reject' ? <Loader2 className="w-3 h-3 mr-1 animate-spin" /> : <XCircle className="w-3 h-3 mr-1" />}
                        Reject &amp; Refund
                      </Button>
                      <Button
                        size="sm"
                        disabled={!!busy[c.id]}
                        onClick={() => handle(c.id, 'approve')}
                        className="bg-gradient-to-r from-amber-600 to-orange-600"
                        data-testid={`charter-approve-${c.id}`}
                      >
                        {busy[c.id] === 'approve' ? <Loader2 className="w-3 h-3 mr-1 animate-spin" /> : <CheckCircle2 className="w-3 h-3 mr-1" />}
                        Approve &amp; Found
                      </Button>
                    </div>
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
};

export default CharterReviewTab;
