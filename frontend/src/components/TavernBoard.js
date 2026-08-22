import React, { useEffect, useState, useCallback } from 'react';
import { toast } from 'sonner';
import { fetchNotices, postNotice, deleteNotice } from '../utils/api';
import { Button } from './ui/button';
import { Textarea } from './ui/textarea';
import { ClipboardList, Trash2, Plus } from 'lucide-react';

/**
 * TavernBoard — in-location notice board.
 *
 * Public reads (no auth required). Posting requires a character in this
 * location. Notices expire after 7 days; only the author or staff can
 * delete early.
 */

const TavernBoard = ({ nation, location, character, currentUserId, isStaff = false }) => {
  const [notices, setNotices] = useState([]);
  const [composing, setComposing] = useState(false);
  const [body, setBody] = useState('');
  const [posting, setPosting] = useState(false);

  const load = useCallback(async () => {
    try {
      const r = await fetchNotices(nation, location);
      setNotices(r.data || []);
    } catch (e) { console.debug('[TavernBoard] fetchNotices failed (public read):', e); }
  }, [nation, location]);

  useEffect(() => { load(); }, [load]);

  const handlePost = async (e) => {
    e.preventDefault();
    if (!character) { toast.error('Pick a character first.'); return; }
    if (!body.trim()) return;
    setPosting(true);
    try {
      await postNotice(nation, location, { character_id: character.id, body });
      toast.success('Notice pinned to the board.');
      setBody('');
      setComposing(false);
      load();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to post notice.');
    } finally {
      setPosting(false);
    }
  };

  const handleDelete = async (noticeId) => {
    try {
      await deleteNotice(noticeId);
      toast.success('Notice removed.');
      load();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to remove notice.');
    }
  };

  return (
    <div className="glass-dark p-5 rounded-xl border border-amber-700/30 mb-6" data-testid="tavern-board">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-lg font-bold text-amber-200 flex items-center gap-2">
          <ClipboardList className="w-5 h-5" /> Bulletin Board
          <span className="text-xs text-gray-500 font-normal">({notices.length} active)</span>
        </h3>
        {character && !composing && (
          <Button size="sm" onClick={() => setComposing(true)} className="bg-amber-700 hover:bg-amber-600" data-testid="tavern-board-new-btn">
            <Plus className="w-4 h-4 mr-1" /> Post
          </Button>
        )}
      </div>

      {composing && (
        <form onSubmit={handlePost} className="mb-4 p-3 bg-black/30 rounded-lg border border-amber-600/30" data-testid="tavern-board-compose">
          <Textarea
            value={body}
            onChange={(e) => setBody(e.target.value)}
            maxLength={500}
            rows={3}
            placeholder={`Pinned to the board of ${location}. ${500 - body.length} characters remaining.`}
            className="bg-black/30 border-amber-500/30 text-white"
            data-testid="tavern-board-body"
          />
          <div className="flex gap-2 mt-2 justify-end">
            <Button type="button" size="sm" variant="outline" onClick={() => { setComposing(false); setBody(''); }}>Cancel</Button>
            <Button type="submit" size="sm" disabled={posting || !body.trim()} className="bg-amber-700 hover:bg-amber-600" data-testid="tavern-board-submit">
              {posting ? 'Pinning…' : 'Pin to Board'}
            </Button>
          </div>
        </form>
      )}

      {notices.length === 0 ? (
        <p className="text-gray-500 italic text-sm">The board is bare.</p>
      ) : (
        <ul className="space-y-2" data-testid="tavern-board-list">
          {notices.map((n) => {
            const canDelete = n.author_user_id === currentUserId || isStaff;
            return (
              <li key={n.id} className="p-3 bg-amber-950/30 border border-amber-700/30 rounded-lg" data-testid={`notice-${n.id}`}>
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <p className="text-gray-100 whitespace-pre-wrap">{n.body}</p>
                    <p className="text-xs text-gray-500 mt-1 italic">— {n.author_character_name}, {new Date(n.posted_at).toLocaleDateString()}</p>
                  </div>
                  {canDelete && (
                    <button onClick={() => handleDelete(n.id)} className="text-gray-500 hover:text-red-300 flex-shrink-0" data-testid={`notice-delete-${n.id}`}>
                      <Trash2 className="w-4 h-4" />
                    </button>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
};

export default TavernBoard;
