import React, { useEffect, useState, useCallback } from 'react';
import { toast } from 'sonner';
import api from '../../utils/api';
import { Button } from '../ui/button';
import { Textarea } from '../ui/textarea';
import { MessageSquare, Plus, ArrowLeft } from 'lucide-react';

const RANK_TONE = {
  initiate: 'bg-gray-800/40 text-gray-300 border-gray-600/40',
  member:   'bg-blue-900/40 text-blue-200 border-blue-700/40',
  officer:  'bg-purple-900/40 text-purple-200 border-purple-700/40',
  leader:   'bg-amber-900/40 text-amber-200 border-amber-600/60',
};

/**
 * Faction-only forum tab. Only active members can read full thread bodies or
 * post replies. Non-members (or anonymous) see the title list only.
 */
const FactionThreadsTab = ({ slug, myCharsInFaction }) => {
  const [threads, setThreads] = useState([]);
  const [openThreadId, setOpenThreadId] = useState(null);
  const [openThread, setOpenThread] = useState(null);
  const [openReplies, setOpenReplies] = useState([]);
  const [forbidden, setForbidden] = useState(false);
  const [loading, setLoading] = useState(false);
  const [showCreate, setShowCreate] = useState(false);
  const [createForm, setCreateForm] = useState({ character_id: '', title: '', content: '' });
  const [replyText, setReplyText] = useState('');
  const [replyAs, setReplyAs] = useState('');

  const amMember = myCharsInFaction.length > 0;
  const defaultActorId = myCharsInFaction[0]?.character_id || '';

  const loadList = useCallback(async () => {
    setLoading(true);
    try {
      const r = await api.get(`/factions/${slug}/threads`);
      setThreads(r.data || []);
    } finally { setLoading(false); }
  }, [slug]);

  const loadThread = useCallback(async (id) => {
    setForbidden(false);
    setLoading(true);
    try {
      const r = await api.get(`/factions/${slug}/threads/${id}`);
      setOpenThread(r.data.thread);
      setOpenReplies(r.data.replies || []);
    } catch (err) {
      if (err.response?.status === 403) setForbidden(true);
      else toast.error(err.response?.data?.detail || 'Failed to load thread');
    } finally { setLoading(false); }
  }, [slug]);

  useEffect(() => { loadList(); }, [loadList]);
  useEffect(() => {
    if (openThreadId) loadThread(openThreadId);
    else { setOpenThread(null); setOpenReplies([]); setForbidden(false); }
  }, [openThreadId, loadThread]);

  useEffect(() => {
    setCreateForm((f) => ({ ...f, character_id: f.character_id || defaultActorId }));
    setReplyAs((r) => r || defaultActorId);
  }, [defaultActorId]);

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!createForm.character_id) { toast.error('Pick a character to author this thread.'); return; }
    try {
      await api.post(`/factions/${slug}/threads`, createForm);
      toast.success('Thread posted.');
      setShowCreate(false);
      setCreateForm({ character_id: defaultActorId, title: '', content: '' });
      await loadList();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to post thread.');
    }
  };

  const handleReply = async (e) => {
    e.preventDefault();
    if (!replyText.trim()) return;
    if (!replyAs) { toast.error('Pick a character to reply as.'); return; }
    try {
      await api.post(`/factions/${slug}/threads/${openThreadId}/replies`, {
        character_id: replyAs,
        content: replyText.trim(),
      });
      setReplyText('');
      await loadThread(openThreadId);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to reply.');
    }
  };

  // ----- single thread view -----
  if (openThreadId) {
    return (
      <div data-testid="faction-thread-detail">
        <button
          onClick={() => setOpenThreadId(null)}
          className="text-gray-400 hover:text-white flex items-center gap-2 text-sm mb-4"
          data-testid="thread-back-btn"
        >
          <ArrowLeft className="w-4 h-4" /> Back to all threads
        </button>
        {forbidden ? (
          <div className="glass-dark border border-red-500/30 rounded-xl p-6 text-center" data-testid="thread-forbidden">
            <p className="text-red-300 font-semibold">This thread is for faction members only.</p>
            <p className="text-xs text-gray-400 mt-2">Pledge a character to this faction to read the full discussion.</p>
          </div>
        ) : openThread ? (
          <article className="glass-dark border border-purple-500/30 rounded-xl p-5">
            <header className="border-b border-gray-700/40 pb-3 mb-3">
              <h3 className="text-xl font-bold text-gray-100" style={{ fontFamily: 'Georgia, serif' }}>{openThread.title}</h3>
              <div className="flex items-center gap-2 text-xs text-gray-400 mt-1">
                <span className={`px-2 py-0.5 rounded-full border ${RANK_TONE[openThread.author_rank] || ''}`}>{openThread.author_rank}</span>
                <span>{openThread.character_name}</span>
                <span>·</span>
                <span>{new Date(openThread.created_at).toLocaleString()}</span>
              </div>
            </header>
            <p className="text-gray-200 whitespace-pre-wrap leading-relaxed">{openThread.content}</p>

            {openReplies.length > 0 && (
              <ul className="mt-6 space-y-3 border-t border-gray-700/40 pt-4">
                {openReplies.map((r) => (
                  <li key={r.id} className="bg-black/30 rounded-lg p-3 border border-gray-700/30" data-testid={`thread-reply-${r.id}`}>
                    <div className="flex items-center gap-2 text-xs mb-1 flex-wrap">
                      {r.is_npc ? (
                        <span className="px-2 py-0.5 rounded-full border border-amber-700/40 bg-amber-900/20 text-amber-300 uppercase tracking-wider" title="An in-world NPC member">
                          NPC · {r.npc_title || 'sworn'}
                        </span>
                      ) : (
                        <span className={`px-2 py-0.5 rounded-full border ${RANK_TONE[r.author_rank] || ''}`}>{r.author_rank}</span>
                      )}
                      <span className="text-gray-300 font-semibold">{r.character_name}</span>
                      <span className="text-gray-500">{new Date(r.created_at).toLocaleString()}</span>
                    </div>
                    <p className="text-gray-200 text-sm whitespace-pre-wrap">{r.content}</p>
                  </li>
                ))}
              </ul>
            )}

            {amMember && (
              <form onSubmit={handleReply} className="mt-6 space-y-2" data-testid="reply-form">
                <div className="flex gap-2 items-center">
                  <label className="text-xs uppercase tracking-wider text-gray-400">Reply as</label>
                  <select
                    value={replyAs}
                    onChange={(e) => setReplyAs(e.target.value)}
                    className="bg-black/40 border border-gray-600 rounded px-2 py-1 text-sm text-gray-200"
                    data-testid="reply-as-select"
                  >
                    {myCharsInFaction.map((m) => (
                      <option key={m.character_id} value={m.character_id}>
                        {m.character_name} ({m.rank})
                      </option>
                    ))}
                  </select>
                </div>
                <Textarea
                  value={replyText}
                  onChange={(e) => setReplyText(e.target.value)}
                  placeholder="Speak your piece…"
                  rows={3}
                  maxLength={4000}
                  className="bg-black/40 border-gray-600 text-gray-100"
                  data-testid="reply-input"
                />
                <Button type="submit" size="sm" disabled={!replyText.trim()} className="bg-purple-600 hover:bg-purple-500" data-testid="reply-submit-btn">
                  Post Reply
                </Button>
              </form>
            )}
          </article>
        ) : (
          <p className="text-gray-500 italic text-center py-6">Loading thread…</p>
        )}
      </div>
    );
  }

  // ----- thread list -----
  return (
    <div data-testid="faction-threads-list">
      <div className="flex items-center justify-between mb-4">
        <p className="text-xs text-gray-400 italic">
          Thread bodies are visible to faction members only. Titles are public.
        </p>
        {amMember && (
          <Button
            size="sm"
            onClick={() => setShowCreate(true)}
            className="bg-gradient-to-r from-purple-600 to-pink-600"
            data-testid="new-thread-btn"
          >
            <Plus className="w-4 h-4 mr-1" /> New Thread
          </Button>
        )}
      </div>

      {loading ? (
        <p className="text-gray-500 italic">Loading…</p>
      ) : threads.length === 0 ? (
        <p className="text-gray-500 italic text-center py-8">No threads yet. {amMember && 'Be the first to call a council.'}</p>
      ) : (
        <ul className="divide-y divide-gray-800/60 glass-dark rounded-xl border border-gray-700/40">
          {threads.map((t) => (
            <li key={t.id}>
              <button
                onClick={() => setOpenThreadId(t.id)}
                className="w-full text-left px-4 py-3 hover:bg-stone-900/40 transition"
                data-testid={`thread-row-${t.id}`}
              >
                <div className="flex items-center justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <h4 className="font-semibold text-gray-100 truncate">{t.title}</h4>
                    <div className="flex items-center gap-2 text-xs text-gray-400 mt-0.5">
                      <span className={`px-1.5 py-0.5 rounded-full border ${RANK_TONE[t.author_rank] || ''}`}>{t.author_rank}</span>
                      <span>{t.character_name}</span>
                      <span>·</span>
                      <span>{new Date(t.created_at).toLocaleDateString()}</span>
                    </div>
                  </div>
                  <span className="flex items-center gap-1 text-xs text-gray-400 whitespace-nowrap">
                    <MessageSquare className="w-3 h-3" />
                    {t.replies_count || 0}
                  </span>
                </div>
              </button>
            </li>
          ))}
        </ul>
      )}

      {/* Create thread modal */}
      {showCreate && (
        <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4" onClick={() => setShowCreate(false)}>
          <form
            onSubmit={handleCreate}
            onClick={(e) => e.stopPropagation()}
            className="glass-dark border border-purple-500/40 rounded-xl p-6 w-full max-w-md space-y-3"
            data-testid="new-thread-form"
          >
            <h3 className="text-xl font-bold text-purple-200">Call a Faction Thread</h3>
            <div>
              <label className="text-xs uppercase tracking-wider text-gray-400 block mb-1">Posting as</label>
              <select
                value={createForm.character_id}
                onChange={(e) => setCreateForm({ ...createForm, character_id: e.target.value })}
                className="w-full bg-black/40 border border-gray-600 rounded px-3 py-2 text-gray-100"
                required
                data-testid="new-thread-author-select"
              >
                {myCharsInFaction.map((m) => (
                  <option key={m.character_id} value={m.character_id}>
                    {m.character_name} ({m.rank})
                  </option>
                ))}
              </select>
            </div>
            <input
              type="text"
              required
              placeholder="Thread title"
              value={createForm.title}
              onChange={(e) => setCreateForm({ ...createForm, title: e.target.value })}
              maxLength={160}
              className="w-full bg-black/40 border border-gray-600 rounded px-3 py-2 text-gray-100"
              data-testid="new-thread-title-input"
            />
            <Textarea
              required
              placeholder="What is the matter at hand?"
              value={createForm.content}
              onChange={(e) => setCreateForm({ ...createForm, content: e.target.value })}
              rows={6}
              maxLength={8000}
              className="bg-black/40 border-gray-600 text-gray-100"
              data-testid="new-thread-content-input"
            />
            <div className="flex gap-2 justify-end">
              <Button type="button" variant="outline" onClick={() => setShowCreate(false)}>Cancel</Button>
              <Button type="submit" className="bg-gradient-to-r from-purple-600 to-pink-600" data-testid="new-thread-submit-btn">
                Post
              </Button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
};

export default FactionThreadsTab;
