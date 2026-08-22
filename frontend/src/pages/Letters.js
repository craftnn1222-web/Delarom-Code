import React, { useEffect, useState, useCallback } from 'react';
import { toast } from 'sonner';
import {
  fetchInbox, fetchSentLetters, sendLetter, markLetterRead, getMyCharacters,
} from '../utils/api';
import api from '../utils/api';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Textarea } from '../components/ui/textarea';
import { Label } from '../components/ui/label';
import { Mail, Send, Clock, Inbox as InboxIcon, ScrollText, X } from 'lucide-react';

/**
 * Letters panel — embedded inside Quill & Coffer.
 *
 * Three tabs: Inbox / Sent / Compose.
 * Letter travel takes 30 min (same nation) or 4 hrs (cross-continent).
 */

const LettersPanel = () => {
  const [characters, setCharacters] = useState([]);
  const [activeCharId, setActiveCharId] = useState(null);
  const [tab, setTab] = useState('inbox');
  const [inbox, setInbox] = useState([]);
  const [sent, setSent] = useState([]);
  const [open, setOpen] = useState(null); // letter currently being read
  const [loading, setLoading] = useState(true);

  const [loadError, setLoadError] = useState(null);

  // Compose state
  const [compose, setCompose] = useState({
    recipient_query: '',
    recipient_results: [],
    recipient: null,
    subject: '',
    body: '',
    sending: false,
  });

  const loadCharacters = useCallback(async () => {
    try {
      const r = await getMyCharacters();
      setCharacters(r.data || []);
      if (r.data && r.data.length > 0 && !activeCharId) {
        setActiveCharId(r.data[0].id);
      }
    } catch (e) {
      console.error('Failed to load characters:', e);
    } finally {
      setLoading(false);
    }
  }, [activeCharId]);

  const loadMail = useCallback(async () => {
    if (!activeCharId) return;
    try {
      const [inb, snt] = await Promise.all([
        fetchInbox(activeCharId),
        fetchSentLetters(activeCharId),
      ]);
      setInbox(inb.data || []);
      setSent(snt.data || []);
    } catch (e) {
      console.error('Failed to load mail:', e);
    }
  }, [activeCharId]);

  useEffect(() => { loadCharacters(); }, [loadCharacters]);
  useEffect(() => { loadMail(); }, [loadMail]);

  const handleOpen = async (letter) => {
    setOpen(letter);
    if (!letter.read_at && tab === 'inbox') {
      try {
        await markLetterRead(letter.id);
        loadMail();
      } catch (e) { console.debug('[Letters] markLetterRead failed:', e); }
    }
  };

  const searchRecipients = async (q) => {
    setCompose((c) => ({ ...c, recipient_query: q, recipient_results: [] }));
    if (q.trim().length < 2) return;
    try {
      // Use the public members directory as a recipient picker. Endpoint
      // returns a bare list of members, not an object — handle both shapes
      // defensively.
      const r = await api.get('/public/members-directory');
      const all = Array.isArray(r.data) ? r.data : (r.data?.members || []);
      const results = [];
      for (const m of all) {
        for (const ch of (m.characters || [])) {
          if (ch.name && ch.name.toLowerCase().includes(q.toLowerCase()) && ch.id !== activeCharId) {
            results.push({ id: ch.id, name: ch.name, owner: m.username });
          }
        }
      }
      setCompose((c) => ({ ...c, recipient_results: results.slice(0, 8) }));
    } catch (e) { console.debug('[Letters] searchRecipients failed:', e); }
  };

  const handleSend = async (e) => {
    e.preventDefault();
    if (!compose.recipient) {
      toast.error('Pick a recipient first.');
      return;
    }
    if (!compose.subject.trim() || !compose.body.trim()) {
      toast.error('Both subject and body are required.');
      return;
    }
    setCompose((c) => ({ ...c, sending: true }));
    try {
      await sendLetter({
        sender_character_id: activeCharId,
        recipient_character_id: compose.recipient.id,
        subject: compose.subject,
        body: compose.body,
      });
      toast.success('Your letter is on its way.');
      setCompose({ recipient_query: '', recipient_results: [], recipient: null, subject: '', body: '', sending: false });
      setTab('sent');
      loadMail();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to send letter.');
      setCompose((c) => ({ ...c, sending: false }));
    }
  };

  const activeChar = characters.find((c) => c.id === activeCharId);

  if (loading) return null;

  if (loadError) {
    return (
      <div className="container mx-auto px-4 py-6 max-w-3xl text-center text-gray-300" data-testid="letters-load-error">
        <Mail className="w-12 h-12 mx-auto text-red-400 mb-3" />
        <p className="text-red-300 mb-3">{loadError}</p>
        <Button onClick={loadCharacters} className="bg-purple-600 hover:bg-purple-500">Try again</Button>
      </div>
    );
  }

  if (characters.length === 0) {
    return (
      <div className="container mx-auto px-4 py-6 max-w-3xl text-center text-gray-300">
        <Mail className="w-12 h-12 mx-auto text-purple-400 mb-3" />
        <p>You need to create a character before you can write or receive letters.</p>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-6 max-w-5xl">
      <header className="mb-6">
        <h2 className="text-2xl sm:text-3xl font-bold text-amber-300 flex items-center gap-3">
          <Mail className="w-7 h-7" />
          Letters
        </h2>
        <p className="text-gray-400 mt-2 text-sm">
          Send sealed letters to other characters. Within the same nation they arrive in
          half an hour. Across continents, expect a four-hour delay.
        </p>
      </header>

        {/* Character switcher */}
        {characters.length > 1 && (
          <div className="mb-4 flex flex-wrap items-center gap-2" data-testid="letters-char-switcher">
            <span className="text-xs uppercase tracking-widest text-gray-400">Reading as:</span>
            {characters.map((c) => (
              <button
                key={c.id}
                onClick={() => setActiveCharId(c.id)}
                className={`text-xs px-3 py-1 rounded-full border ${activeCharId === c.id ? 'bg-amber-600/40 border-amber-400 text-white' : 'bg-black/30 border-gray-600/40 text-gray-300 hover:text-white'}`}
              >
                {c.name}
              </button>
            ))}
          </div>
        )}

        {/* Tabs */}
        <div className="flex gap-2 border-b border-purple-500/30 mb-6">
          {[
            { k: 'inbox', label: 'Inbox', icon: InboxIcon, count: inbox.filter((l) => !l.read_at).length },
            { k: 'sent', label: 'Sent', icon: ScrollText, count: null },
            { k: 'compose', label: 'Compose', icon: Send, count: null },
          ].map(({ k, label, icon: Icon, count }) => (
            <button
              key={k}
              onClick={() => setTab(k)}
              className={`px-4 py-2 text-sm flex items-center gap-2 border-b-2 transition ${tab === k ? 'border-amber-400 text-amber-200' : 'border-transparent text-gray-400 hover:text-white'}`}
              data-testid={`letters-tab-${k}`}
            >
              <Icon className="w-4 h-4" />
              {label}
              {count > 0 && <span className="text-[10px] bg-red-500 text-white rounded-full px-1.5">{count}</span>}
            </button>
          ))}
        </div>

        {/* Inbox */}
        {tab === 'inbox' && (
          <div data-testid="letters-inbox-list" className="space-y-2">
            {inbox.length === 0 && (
              <p className="text-gray-500 italic text-center py-8">No letters have arrived yet.</p>
            )}
            {inbox.map((l) => (
              <button
                key={l.id}
                onClick={() => handleOpen(l)}
                className={`w-full text-left glass-dark p-4 rounded-xl border ${l.read_at ? 'border-gray-700/40' : 'border-amber-500/40 bg-amber-900/10'}`}
              >
                <div className="flex items-baseline justify-between gap-3">
                  <p className={`font-bold ${l.read_at ? 'text-gray-300' : 'text-amber-200'}`}>{l.subject}</p>
                  <p className="text-xs text-gray-400 flex-shrink-0">From {l.sender_character_name}</p>
                </div>
                <p className="text-sm text-gray-400 truncate mt-1">{l.body}</p>
              </button>
            ))}
          </div>
        )}

        {/* Sent */}
        {tab === 'sent' && (
          <div data-testid="letters-sent-list" className="space-y-2">
            {sent.length === 0 && (
              <p className="text-gray-500 italic text-center py-8">You have sent no letters.</p>
            )}
            {sent.map((l) => (
              <button
                key={l.id}
                onClick={() => handleOpen(l)}
                className="w-full text-left glass-dark p-4 rounded-xl border border-gray-700/40"
              >
                <div className="flex items-baseline justify-between gap-3">
                  <p className="font-bold text-gray-200">{l.subject}</p>
                  <p className="text-xs text-gray-400 flex-shrink-0">
                    To {l.recipient_character_name}
                    {l.status === 'in_transit' && (
                      <span className="ml-2 text-amber-400 inline-flex items-center gap-1">
                        <Clock className="w-3 h-3" /> in transit
                      </span>
                    )}
                    {l.status === 'read' && <span className="ml-2 text-emerald-400">read</span>}
                  </p>
                </div>
                <p className="text-sm text-gray-400 truncate mt-1">{l.body}</p>
              </button>
            ))}
          </div>
        )}

        {/* Compose */}
        {tab === 'compose' && (
          <form onSubmit={handleSend} className="space-y-4 glass-dark p-6 rounded-xl border border-amber-500/30" data-testid="letters-compose-form">
            <p className="text-sm text-gray-400">
              Writing as <span className="text-amber-200 font-bold">{activeChar?.name}</span>
            </p>
            <div>
              <Label className="text-gray-300">Recipient (search by character name)</Label>
              {compose.recipient ? (
                <div className="mt-1 flex items-center justify-between p-2 rounded-lg bg-amber-900/20 border border-amber-500/30">
                  <span>{compose.recipient.name} <span className="text-gray-400 text-xs">— played by {compose.recipient.owner}</span></span>
                  <button type="button" onClick={() => setCompose((c) => ({ ...c, recipient: null, recipient_query: '' }))} className="text-gray-400 hover:text-white">
                    <X className="w-4 h-4" />
                  </button>
                </div>
              ) : (
                <>
                  <Input
                    value={compose.recipient_query}
                    onChange={(e) => searchRecipients(e.target.value)}
                    placeholder="Start typing a character's name…"
                    className="mt-1 bg-black/30 border-purple-500/40 text-white"
                    data-testid="letters-recipient-search"
                  />
                  {compose.recipient_results.length > 0 && (
                    <ul className="mt-1 bg-black/60 border border-purple-500/30 rounded-lg max-h-48 overflow-auto">
                      {compose.recipient_results.map((r) => (
                        <li key={r.id}>
                          <button
                            type="button"
                            onClick={() => setCompose((c) => ({ ...c, recipient: r, recipient_results: [] }))}
                            className="block w-full text-left px-3 py-2 hover:bg-purple-600/30 text-gray-200"
                          >
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
              <Label className="text-gray-300">Subject</Label>
              <Input
                value={compose.subject}
                onChange={(e) => setCompose((c) => ({ ...c, subject: e.target.value }))}
                maxLength={120}
                className="mt-1 bg-black/30 border-purple-500/40 text-white"
                data-testid="letters-subject"
              />
            </div>
            <div>
              <Label className="text-gray-300">Body</Label>
              <Textarea
                value={compose.body}
                onChange={(e) => setCompose((c) => ({ ...c, body: e.target.value }))}
                rows={10}
                maxLength={4000}
                placeholder="My dearest friend…"
                className="mt-1 bg-black/30 border-purple-500/40 text-white"
                data-testid="letters-body"
              />
            </div>
            <Button type="submit" disabled={compose.sending} className="bg-amber-600 hover:bg-amber-500" data-testid="letters-send-btn">
              <Send className="w-4 h-4 mr-2" />
              {compose.sending ? 'Sealing…' : 'Send Letter'}
            </Button>
          </form>
        )}

        {/* Open letter modal */}
        {open && (
          <div className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center px-4" onClick={() => setOpen(null)}>
            <div className="glass-dark p-6 rounded-2xl max-w-2xl w-full border border-amber-500/40 max-h-[80vh] overflow-auto" onClick={(e) => e.stopPropagation()}>
              <div className="flex items-start justify-between gap-3 mb-3">
                <div>
                  <p className="text-xs uppercase tracking-widest text-gray-400">
                    {tab === 'inbox' ? `From ${open.sender_character_name}` : `To ${open.recipient_character_name}`}
                  </p>
                  <h2 className="text-2xl font-bold text-amber-200">{open.subject}</h2>
                </div>
                <button onClick={() => setOpen(null)} className="text-gray-400 hover:text-white"><X className="w-5 h-5" /></button>
              </div>
              <p className="text-gray-200 whitespace-pre-wrap leading-relaxed" data-testid="letter-body">{open.body}</p>
              <p className="text-xs text-gray-500 mt-4 italic">Sent {new Date(open.sent_at).toLocaleString()}</p>
            </div>
          </div>
        )}
    </div>
  );
};

export default LettersPanel;
