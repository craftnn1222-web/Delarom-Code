import React, { useEffect, useState, useCallback } from 'react';
import { toast } from 'sonner';
import {
  fetchMyBonds, acceptBond, declineBond, breakBond, fetchBondTypes,
  proposeBond, getMyCharacters,
} from '../utils/api';
import api from '../utils/api';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Textarea } from '../components/ui/textarea';
import { Label } from '../components/ui/label';
import { Heart, Swords, X, Plus, Users } from 'lucide-react';

/**
 * Sworn Bonds panel — embedded inside Quill & Coffer.
 *
 * Shows incoming proposals, outgoing proposals, accepted bonds, and history.
 * Also lets the player propose a new bond by picking one of their characters
 * and searching for another player's character.
 */

const BOND_ICONS = {
  'blood-brothers':    Swords,
  'mentor-apprentice': Users,
  'sworn-friends':     Heart,
  'rivals':            Swords,
  'parent-child':      Users,
};

const BondsPanel = () => {
  const [bonds, setBonds] = useState({ incoming_proposals: [], outgoing_proposals: [], accepted: [], history: [] });
  const [bondTypes, setBondTypes] = useState({});
  const [characters, setCharacters] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showPropose, setShowPropose] = useState(false);
  const [breaking, setBreaking] = useState(null); // bond being broken

  // Propose form
  const [form, setForm] = useState({
    sender_char_id: '',
    bond_type: 'sworn-friends',
    recipient_query: '',
    recipient_results: [],
    recipient: null,
    proposal_text: '',
    submitting: false,
  });

  const reload = useCallback(async () => {
    // Use allSettled so a transient failure of bonds-or-types doesn't also
    // wipe out characters — that mismatch was hiding the "Propose a Bond"
    // button for users who genuinely had characters.
    const [b, t, c] = await Promise.allSettled([fetchMyBonds(), fetchBondTypes(), getMyCharacters()]);
    if (b.status === 'fulfilled') {
      setBonds(b.value.data || { incoming_proposals: [], outgoing_proposals: [], accepted: [], history: [] });
    } else {
      console.error('Failed to load bonds:', b.reason);
    }
    if (t.status === 'fulfilled') setBondTypes(t.value.data || {});
    if (c.status === 'fulfilled') {
      const chars = c.value.data || [];
      setCharacters(chars);
      if (chars.length > 0) {
        setForm((f) => f.sender_char_id ? f : { ...f, sender_char_id: chars[0].id });
      }
    } else {
      console.error('Failed to load characters:', c.reason);
    }
    setLoading(false);
  }, []);

  useEffect(() => { reload(); }, [reload]);

  const handleAccept = async (id) => {
    try { await acceptBond(id); toast.success('Bond accepted.'); reload(); }
    catch (e) { toast.error(e.response?.data?.detail || 'Failed to accept'); }
  };
  const handleDecline = async (id) => {
    try { await declineBond(id); toast.success('Bond declined.'); reload(); }
    catch (e) { toast.error(e.response?.data?.detail || 'Failed to decline'); }
  };
  const handleBreak = async (id, reason) => {
    try { await breakBond(id, reason); toast.success('Bond broken.'); setBreaking(null); reload(); }
    catch (e) { toast.error(e.response?.data?.detail || 'Failed to break'); }
  };

  const searchRecipients = async (q) => {
    setForm((f) => ({ ...f, recipient_query: q, recipient_results: [] }));
    if (q.trim().length < 2) return;
    try {
      const r = await api.get('/public/members-directory');
      // Endpoint returns a bare list of members, not { members: [...] }.
      const all = Array.isArray(r.data) ? r.data : (r.data?.members || []);
      const myCharIds = new Set(characters.map((c) => c.id));
      const results = [];
      for (const m of all) {
        for (const ch of (m.characters || [])) {
          if (ch.name && ch.name.toLowerCase().includes(q.toLowerCase()) && !myCharIds.has(ch.id)) {
            results.push({ id: ch.id, name: ch.name, owner: m.username });
          }
        }
      }
      setForm((f) => ({ ...f, recipient_results: results.slice(0, 8) }));
    } catch (e) { console.debug("Silent failure:", e); }
  };

  const handlePropose = async (e) => {
    e.preventDefault();
    if (!form.recipient) { toast.error('Pick a character to bond with.'); return; }
    if (!form.proposal_text.trim()) { toast.error('Write a proposal.'); return; }
    setForm((f) => ({ ...f, submitting: true }));
    try {
      await proposeBond(form.sender_char_id, {
        target_character_id: form.recipient.id,
        bond_type: form.bond_type,
        proposal_text: form.proposal_text,
      });
      toast.success('Proposal sent.');
      setShowPropose(false);
      setForm((f) => ({ ...f, recipient: null, recipient_query: '', proposal_text: '', submitting: false }));
      reload();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to propose');
      setForm((f) => ({ ...f, submitting: false }));
    }
  };

  if (loading) return null;

  const Section = ({ title, children, count, testid }) => (
    <section className="mb-8" data-testid={testid}>
      <h2 className="text-xl font-bold text-purple-300 mb-3 uppercase tracking-widest">
        {title} {count > 0 && <span className="text-gray-500 ml-2">({count})</span>}
      </h2>
      {children}
    </section>
  );

  return (
    <div className="container mx-auto px-4 py-6 max-w-4xl">
      <header className="mb-6 flex items-start justify-between flex-wrap gap-4">
        <div>
          <h2 className="text-2xl sm:text-3xl font-bold text-pink-300 flex items-center gap-3">
            <Heart className="w-7 h-7" />
            Sworn Bonds
          </h2>
          <p className="text-gray-400 mt-2 text-sm">
            Bonds tie characters together across the world — blood-brothers, mentors, rivals, parents and children, sworn friends.
          </p>
        </div>
        {characters.length > 0 && (
          <Button onClick={() => setShowPropose(true)} className="bg-pink-600 hover:bg-pink-500" data-testid="propose-bond-btn">
            <Plus className="w-4 h-4 mr-2" /> Propose a Bond
          </Button>
        )}
      </header>

        {/* Incoming */}
        <Section title="Incoming Proposals" count={bonds.incoming_proposals.length} testid="bonds-incoming">
          {bonds.incoming_proposals.length === 0 ? (
            <p className="text-gray-500 italic">No pending proposals.</p>
          ) : bonds.incoming_proposals.map((b) => (
            <BondCard key={b.id} bond={b} role="incoming"
              onAccept={() => handleAccept(b.id)} onDecline={() => handleDecline(b.id)} />
          ))}
        </Section>

        {/* Outgoing */}
        <Section title="Outgoing Proposals" count={bonds.outgoing_proposals.length} testid="bonds-outgoing">
          {bonds.outgoing_proposals.length === 0 ? (
            <p className="text-gray-500 italic">No proposals awaiting reply.</p>
          ) : bonds.outgoing_proposals.map((b) => (
            <BondCard key={b.id} bond={b} role="outgoing" />
          ))}
        </Section>

        {/* Accepted */}
        <Section title="Active Bonds" count={bonds.accepted.length} testid="bonds-accepted">
          {bonds.accepted.length === 0 ? (
            <p className="text-gray-500 italic">No active bonds — yet.</p>
          ) : bonds.accepted.map((b) => (
            <BondCard key={b.id} bond={b} role="accepted"
              onBreak={() => setBreaking(b)} />
          ))}
        </Section>

        {/* History */}
        {bonds.history.length > 0 && (
          <Section title="History" count={bonds.history.length} testid="bonds-history">
            {bonds.history.map((b) => (
              <BondCard key={b.id} bond={b} role="history" />
            ))}
          </Section>
        )}

        {/* Propose Modal */}
        {showPropose && (
          <div className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center px-4" onClick={() => setShowPropose(false)}>
            <form onSubmit={handlePropose} className="glass-dark p-6 rounded-2xl max-w-2xl w-full border border-pink-500/40 max-h-[85vh] overflow-auto"
              onClick={(e) => e.stopPropagation()} data-testid="propose-bond-modal">
              <div className="flex items-start justify-between gap-3 mb-4">
                <h2 className="text-2xl font-bold text-pink-300">Propose a Bond</h2>
                <button type="button" onClick={() => setShowPropose(false)} className="text-gray-400 hover:text-white"><X className="w-5 h-5" /></button>
              </div>

              <div className="space-y-4">
                <div>
                  <Label className="text-gray-300">Your character</Label>
                  <select
                    value={form.sender_char_id}
                    onChange={(e) => setForm((f) => ({ ...f, sender_char_id: e.target.value }))}
                    className="mt-1 w-full bg-black/30 border border-purple-500/40 text-white rounded-md px-3 py-2"
                    data-testid="propose-sender-select"
                  >
                    {characters.map((c) => (<option key={c.id} value={c.id} className="bg-black">{c.name}</option>))}
                  </select>
                </div>

                <div>
                  <Label className="text-gray-300">Bond type</Label>
                  <select
                    value={form.bond_type}
                    onChange={(e) => setForm((f) => ({ ...f, bond_type: e.target.value }))}
                    className="mt-1 w-full bg-black/30 border border-purple-500/40 text-white rounded-md px-3 py-2"
                    data-testid="propose-type-select"
                  >
                    {Object.entries(bondTypes).map(([k, label]) => (
                      <option key={k} value={k} className="bg-black">{label}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <Label className="text-gray-300">Bond with (character)</Label>
                  {form.recipient ? (
                    <div className="mt-1 flex items-center justify-between p-2 rounded-lg bg-pink-900/20 border border-pink-500/30">
                      <span>{form.recipient.name} <span className="text-gray-400 text-xs">— {form.recipient.owner}</span></span>
                      <button type="button" onClick={() => setForm((f) => ({ ...f, recipient: null, recipient_query: '' }))} className="text-gray-400 hover:text-white">
                        <X className="w-4 h-4" />
                      </button>
                    </div>
                  ) : (
                    <>
                      <Input
                        value={form.recipient_query}
                        onChange={(e) => searchRecipients(e.target.value)}
                        placeholder="Start typing a character's name…"
                        className="mt-1 bg-black/30 border-purple-500/40 text-white"
                        data-testid="propose-recipient-search"
                      />
                      {form.recipient_results.length > 0 && (
                        <ul className="mt-1 bg-black/60 border border-purple-500/30 rounded-lg max-h-48 overflow-auto">
                          {form.recipient_results.map((r) => (
                            <li key={r.id}>
                              <button type="button"
                                onClick={() => setForm((f) => ({ ...f, recipient: r, recipient_results: [] }))}
                                className="block w-full text-left px-3 py-2 hover:bg-pink-600/30 text-gray-200">
                                {r.name} <span className="text-gray-500 text-xs">— {r.owner}</span>
                              </button>
                            </li>
                          ))}
                        </ul>
                      )}
                    </>
                  )}
                </div>

                <div>
                  <Label className="text-gray-300">In-character proposal</Label>
                  <Textarea
                    value={form.proposal_text}
                    onChange={(e) => setForm((f) => ({ ...f, proposal_text: e.target.value }))}
                    rows={6} maxLength={600}
                    placeholder="Speak from your character's heart…"
                    className="mt-1 bg-black/30 border-purple-500/40 text-white"
                    data-testid="propose-text"
                  />
                </div>

                <Button type="submit" disabled={form.submitting} className="bg-pink-600 hover:bg-pink-500 w-full" data-testid="propose-submit">
                  {form.submitting ? 'Sending…' : 'Send Proposal'}
                </Button>
              </div>
            </form>
          </div>
        )}

        {/* Break Bond Modal */}
        {breaking && (
          <BreakBondDialog bond={breaking} onClose={() => setBreaking(null)} onConfirm={handleBreak} />
        )}
    </div>
  );
};

const BondCard = ({ bond, role, onAccept, onDecline, onBreak }) => {
  const Icon = BOND_ICONS[bond.bond_type] || Heart;
  return (
    <div className="glass-dark p-4 rounded-xl border border-purple-500/30 mb-2" data-testid={`bond-${bond.id}`}>
      <div className="flex items-start gap-3">
        <div className="bg-pink-900/30 p-2 rounded-lg"><Icon className="w-5 h-5 text-pink-300" /></div>
        <div className="flex-1 min-w-0">
          <p className="text-sm text-gray-400">
            <span className="font-bold text-pink-200">{bond.bond_label}</span> — {bond.initiator_character_name} ↔ {bond.target_character_name}
          </p>
          {bond.proposal_text && (
            <p className="text-gray-300 italic mt-1">"{bond.proposal_text}"</p>
          )}
          {bond.status === 'broken' && bond.break_reason && (
            <p className="text-xs text-red-300 mt-2">Broken: {bond.break_reason}</p>
          )}
        </div>
        <div className="flex flex-col gap-2 flex-shrink-0">
          {role === 'incoming' && (
            <>
              <Button size="sm" onClick={onAccept} className="bg-emerald-600 hover:bg-emerald-500" data-testid={`bond-accept-${bond.id}`}>Accept</Button>
              <Button size="sm" variant="outline" onClick={onDecline} className="border-red-500/50 text-red-300 hover:bg-red-500/20" data-testid={`bond-decline-${bond.id}`}>Decline</Button>
            </>
          )}
          {role === 'outgoing' && <span className="text-xs text-amber-400 italic">awaiting reply</span>}
          {role === 'accepted' && (
            <Button size="sm" variant="outline" onClick={onBreak} className="border-red-500/50 text-red-300 hover:bg-red-500/20" data-testid={`bond-break-${bond.id}`}>Break</Button>
          )}
        </div>
      </div>
    </div>
  );
};

const BreakBondDialog = ({ bond, onClose, onConfirm }) => {
  const [reason, setReason] = useState('');
  return (
    <div className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center px-4" onClick={onClose}>
      <div className="glass-dark p-6 rounded-2xl max-w-lg w-full border border-red-500/40" onClick={(e) => e.stopPropagation()}>
        <h3 className="text-xl font-bold text-red-300 mb-2">Break this bond?</h3>
        <p className="text-gray-300 text-sm mb-3">This cannot be undone. The world will remember.</p>
        <Textarea value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Optional reason (in-character)…" rows={4} className="bg-black/30 border-red-500/30 text-white" />
        <div className="flex gap-2 mt-3 justify-end">
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button onClick={() => onConfirm(bond.id, reason)} className="bg-red-600 hover:bg-red-500" data-testid="bond-break-confirm">Break Bond</Button>
        </div>
      </div>
    </div>
  );
};

export default BondsPanel;
