import React, { useEffect, useState, useCallback } from 'react';
import { fetchMemorial, fetchMemorialCharacter } from '../utils/api';
import { Skull, ArrowLeft } from 'lucide-react';

/**
 * Memorial Hall panel — embedded inside Quill & Coffer.
 * Public list of all fallen characters (Phase 3). Detail view is
 * driven by local state rather than URL routing.
 */

const MemorialPanel = () => {
  const [chars, setChars] = useState([]);
  const [focusId, setFocusId] = useState(null);
  const [focus, setFocus] = useState(null);
  const [loading, setLoading] = useState(true);

  const loadList = useCallback(async () => {
    try {
      const r = await fetchMemorial();
      setChars(r.data || []);
    } catch (e) { console.debug('[Memorial] loadList failed:', e); }
    finally { setLoading(false); }
  }, []);

  const loadOne = useCallback(async () => {
    if (!focusId) { setFocus(null); return; }
    try {
      const r = await fetchMemorialCharacter(focusId);
      setFocus(r.data);
    } catch (_e) {
      setFocus(null);
    }
  }, [focusId]);

  useEffect(() => { loadList(); }, [loadList]);
  useEffect(() => { loadOne(); }, [loadOne]);

  if (loading) return null;

  return (
    <div className="container mx-auto px-4 py-6 max-w-5xl">
      {focus ? (
        <article data-testid="memorial-detail">
          <button onClick={() => setFocusId(null)} className="text-gray-400 hover:text-white flex items-center gap-2 mb-4" data-testid="memorial-back-btn">
            <ArrowLeft className="w-4 h-4" /> Back to the Hall
          </button>
          <div className="glass-dark p-8 rounded-2xl border border-gray-600/40">
            <header className="border-b border-gray-700/40 pb-4 mb-6">
              <h2 className="text-3xl font-bold text-gray-100 flex items-center gap-3">
                <Skull className="w-7 h-7 text-gray-500" />
                {focus.name}
              </h2>
              <p className="text-gray-400 mt-2">
                {focus.race} {focus.character_class} of {focus.nation}
              </p>
              {focus.died_at && (
                <p className="text-xs uppercase tracking-widest text-gray-500 mt-3">
                  Passed on {new Date(focus.died_at).toLocaleDateString()} — {focus.status}
                </p>
              )}
            </header>
            {focus.cause_of_death && (
              <p className="text-gray-300 italic mb-4">{focus.cause_of_death}</p>
            )}
            {focus.eulogy ? (
              <blockquote className="text-gray-100 text-lg leading-relaxed border-l-4 border-amber-500/40 pl-4 py-2 my-4" data-testid="memorial-eulogy">
                {focus.eulogy}
              </blockquote>
            ) : (
              <p className="text-gray-500 italic">No words have yet been carved.</p>
            )}
            {focus.backstory && (
              <div className="mt-6">
                <p className="text-xs uppercase tracking-widest text-gray-500">A life remembered</p>
                <p className="text-gray-300 mt-2 whitespace-pre-wrap">{focus.backstory}</p>
              </div>
            )}
          </div>
        </article>
      ) : (
        <>
          <header className="mb-6">
            <h2 className="text-2xl sm:text-3xl font-bold text-gray-200 flex items-center gap-3">
              <Skull className="w-7 h-7 text-gray-500" />
              The Memorial Hall
            </h2>
            <p className="text-gray-400 mt-2 italic text-sm">The dead linger. The world remembers them.</p>
          </header>
          {chars.length === 0 ? (
            <p className="text-gray-500 italic text-center py-12">The Hall is quiet — none have yet passed.</p>
          ) : (
            <ul className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3" data-testid="memorial-list">
              {chars.map((c) => (
                <li key={c.id}>
                  <button onClick={() => setFocusId(c.id)} className="w-full text-left glass-dark p-4 rounded-xl border border-gray-700/40 hover:border-gray-500/60 transition" data-testid={`memorial-card-${c.id}`}>
                    <h3 className="text-lg font-bold text-gray-100">{c.name}</h3>
                    <p className="text-xs text-gray-400 mt-1">
                      {c.race} {c.character_class} • {c.nation}
                    </p>
                    <p className="text-xs uppercase tracking-widest text-gray-500 mt-2">
                      {c.status} {c.died_at ? `• ${new Date(c.died_at).toLocaleDateString()}` : ''}
                    </p>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </div>
  );
};

export default MemorialPanel;
