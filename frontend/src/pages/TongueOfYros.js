import React, { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { toast } from 'sonner';
import { Hammer, Loader2, Mountain, ScrollText, Swords } from 'lucide-react';
import api from '../utils/api';
import { Button } from '../components/ui/button';
import { Textarea } from '../components/ui/textarea';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '../components/ui/dialog';

const VERDICT_STYLES = {
  silence: { color: 'text-stone-300',  label: 'Silence',      sub: 'The stone did not stir.' },
  tremor:  { color: 'text-amber-300',  label: 'A Tremor',     sub: 'The blade hummed — but did not lift.' },
  drawn:   { color: 'text-orange-300', label: 'DRAWN',        sub: "You wield the Tongue of Y'ros." },
};

const TongueOfYros = () => {
  const [characters, setCharacters] = useState([]);
  const [selectedCharId, setSelectedCharId] = useState('');
  const [attemptText, setAttemptText] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [resultOpen, setResultOpen] = useState(false);
  const [result, setResult] = useState(null);
  const [history, setHistory] = useState([]);
  const [swordState, setSwordState] = useState(null);
  const [loading, setLoading] = useState(true);

  const refresh = async () => {
    try {
      const [stateRes, charRes] = await Promise.all([
        api.get('/tongue-of-yros/state'),
        api.get('/characters'),
      ]);
      setSwordState(stateRes.data);
      const allChars = Array.isArray(charRes.data) ? charRes.data : (charRes.data?.characters || []);
      setCharacters(allChars);
      // Prefer a Dwarf character
      const dwarf = allChars.find((c) => (c.race || '').toLowerCase().includes('dwarf'));
      if (!selectedCharId) setSelectedCharId(dwarf?.id || allChars[0]?.id || '');
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to reach the tomb.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  useEffect(() => {
    if (!selectedCharId) {
      setHistory([]);
      return;
    }
    api.get(`/tongue-of-yros/character/${selectedCharId}`)
      .then((r) => setHistory(Array.isArray(r.data) ? r.data : []))
      .catch(() => setHistory([]));
  }, [selectedCharId, resultOpen]);

  const selectedChar = useMemo(
    () => characters.find((c) => c.id === selectedCharId),
    [characters, selectedCharId],
  );

  const isDwarf = (selectedChar?.race || '').toLowerCase().includes('dwarf');
  const isCurrentBearer = swordState?.bearer_character_id === selectedCharId;

  const handleSubmit = async () => {
    if (!selectedCharId) {
      toast.error('Choose a character first.');
      return;
    }
    if ((attemptText || '').trim().length < 15) {
      toast.error('Your declaration must be at least 15 characters.');
      return;
    }
    if (submitting) return;
    setSubmitting(true);
    try {
      const r = await api.post('/tongue-of-yros/attempt', {
        character_id: selectedCharId,
        attempt_text: attemptText.trim(),
      });
      setResult(r.data);
      setResultOpen(true);
      setAttemptText('');
      refresh();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'The tomb rejects your approach.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleRelinquish = async () => {
    if (!isCurrentBearer) return;
    if (!window.confirm("Set the Tongue of Y'ros back into the stone? Another dwarf may then attempt to claim it.")) return;
    try {
      await api.post('/tongue-of-yros/relinquish', { character_id: selectedCharId });
      toast.success("You set the blade down. Y'ros keeps its stone until another proves worthy.");
      refresh();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'The blade will not release your hand.');
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center text-stone-300">
        <Loader2 className="w-6 h-6 mr-2 animate-spin" />
        Descending into Thal&apos;Karrak…
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-zinc-950 via-stone-950 to-black text-stone-100">
      <div className="max-w-4xl mx-auto px-6 py-12">
        <div className="mb-10">
          <Link
            to="/dashboard"
            className="text-sm text-stone-400 hover:text-stone-200 transition"
            data-testid="back-to-dashboard-link"
          >
            ← Dashboard
          </Link>
          <h1 className="mt-4 text-4xl sm:text-5xl font-bold tracking-tight flex items-center gap-3 text-orange-200">
            <Swords className="w-10 h-10 text-orange-400" />
            The Tongue of Y&apos;ros
          </h1>
          <p className="mt-3 text-stone-400 max-w-3xl">
            In the deepest chamber of Thal&apos;Karrak — Thalgrer&apos;s Tomb, ancient
            seat of Stonehearth Hold — a stone blade waits half-buried in the
            altar. Consecrated to Yros at the dawn of the Astral Era. Only a
            dwarf may draw it, and only when their approach honours the god.
          </p>
        </div>

        {/* Sword state banner */}
        <div
          className={`rounded-xl border p-4 mb-8 ${
            swordState?.bearer_active
              ? 'bg-orange-950/40 border-orange-700/50'
              : 'bg-stone-950/60 border-stone-700/60'
          }`}
          data-testid="tongue-state-banner"
        >
          {swordState?.bearer_active ? (
            <div className="flex items-center gap-3 text-orange-200">
              <Hammer className="w-6 h-6" />
              <div>
                The blade is currently borne by{' '}
                <strong className="text-orange-100">{swordState.bearer_character_name}</strong>.
                Until they set it down, no other may claim it.
              </div>
            </div>
          ) : (
            <div className="flex items-center gap-3 text-stone-300">
              <Mountain className="w-6 h-6 text-stone-500" />
              <div>
                The blade rests in the stone. It waits for a hand it knows.
              </div>
            </div>
          )}
        </div>

        {/* Character picker */}
        <div className="rounded-xl border border-stone-700/60 bg-stone-950/60 p-6 mb-8">
          <label className="block text-sm font-medium text-stone-300 mb-2">
            Approaching the altar as
          </label>
          {characters.length === 0 ? (
            <div className="text-stone-400">
              Create a character first — preferably a dwarf.
            </div>
          ) : (
            <select
              value={selectedCharId}
              onChange={(e) => setSelectedCharId(e.target.value)}
              className="w-full bg-stone-900 border border-stone-700 rounded-md px-3 py-2 text-stone-100"
              data-testid="tongue-character-select"
            >
              {characters.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name} — {c.race}{c.character_class ? ` (${c.character_class})` : ''}
                </option>
              ))}
            </select>
          )}
          {selectedChar && !isDwarf && (
            <p className="mt-2 text-xs text-amber-300/80">
              Only dwarves may draw the Tongue of Y&apos;ros. This character may still
              attempt — but the stone knows.
            </p>
          )}
        </div>

        {/* Attempt / Relinquish */}
        {isCurrentBearer ? (
          <div className="rounded-xl border border-orange-700/60 bg-orange-950/30 p-6 mb-10">
            <h2 className="text-lg font-semibold text-orange-200 mb-2 flex items-center gap-2">
              <Swords className="w-5 h-5" />
              You are the Bearer
            </h2>
            <p className="text-sm text-orange-100/80 mb-4">
              The Tongue of Y&apos;ros answers to your hand. You may set it back
              into the stone at any time — another dwarf may then attempt to
              draw it.
            </p>
            <Button
              onClick={handleRelinquish}
              className="bg-gradient-to-r from-stone-700 to-stone-800 text-stone-100"
              data-testid="tongue-relinquish-btn"
            >
              Set the blade back into the stone
            </Button>
          </div>
        ) : (
          <div className="rounded-xl border border-stone-700/60 bg-stone-950/60 p-6 mb-10">
            <h2 className="text-lg font-semibold mb-1 flex items-center gap-2 text-orange-200">
              <Hammer className="w-5 h-5" />
              Your declaration as you lay hand on the hilt
            </h2>
            <p className="text-sm text-stone-400 mb-4">
              Speak plainly and truly. The blade weighs your words against your
              life. One attempt every six hours.
            </p>
            <Textarea
              value={attemptText}
              onChange={(e) => setAttemptText(e.target.value)}
              placeholder="What do you say, as you touch the hilt? Speak of what oath you hold, what you have built, what you would carry this blade for…"
              maxLength={2000}
              rows={6}
              className="bg-stone-900 border-stone-700 text-stone-100 mb-2"
              data-testid="tongue-attempt-input"
            />
            <div className="text-xs text-stone-500 mb-4">
              {attemptText.length} / 2000 characters
            </div>
            <Button
              onClick={handleSubmit}
              disabled={submitting || !selectedCharId || attemptText.trim().length < 15}
              className="bg-gradient-to-r from-orange-700 to-amber-800 hover:from-orange-800 hover:to-amber-900 text-orange-100"
              data-testid="tongue-attempt-btn"
            >
              {submitting ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  The stone considers…
                </>
              ) : (
                <>
                  <Swords className="w-4 h-4 mr-2" />
                  Attempt the draw
                </>
              )}
            </Button>
          </div>
        )}

        {/* History */}
        {history.length > 0 && (
          <div className="rounded-xl border border-stone-700/60 bg-stone-950/40 p-6">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <ScrollText className="w-5 h-5 text-stone-400" />
              This Character&apos;s Attempts
            </h2>
            <div className="space-y-3" data-testid="tongue-history-list">
              {history.slice(0, 12).map((a) => {
                const v = VERDICT_STYLES[a.verdict] || VERDICT_STYLES.silence;
                return (
                  <div
                    key={a.id}
                    className="rounded-md border border-stone-700/50 bg-stone-900/40 p-3"
                    data-testid={`tongue-record-${a.id}`}
                  >
                    <div className="flex items-center justify-between text-sm mb-1">
                      <strong className={v.color}>{v.label}</strong>
                      <span className="text-stone-500 text-xs">
                        {new Date(a.attempted_at).toLocaleString()}
                      </span>
                    </div>
                    <p className="text-stone-200 text-sm italic">{a.narration}</p>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {/* Result modal */}
      <Dialog open={resultOpen} onOpenChange={setResultOpen}>
        <DialogContent
          className="bg-stone-950 border-stone-700 text-stone-100 max-w-lg"
          data-testid="tongue-result-modal"
        >
          {result && (() => {
            const v = VERDICT_STYLES[result.verdict] || VERDICT_STYLES.silence;
            return (
              <>
                <DialogHeader>
                  <DialogTitle
                    className={`flex items-center gap-2 text-2xl ${v.color}`}
                    data-testid="tongue-result-verdict-label"
                  >
                    <Swords className="w-7 h-7 text-orange-400" />
                    {v.label}
                  </DialogTitle>
                  <DialogDescription className="text-stone-400">
                    {v.sub}
                  </DialogDescription>
                </DialogHeader>
                <p
                  className="text-stone-100 italic text-lg leading-relaxed mt-4"
                  data-testid="tongue-result-narration"
                >
                  {result.narration}
                </p>
                {result.verdict === 'drawn' && (
                  <div className="mt-4 rounded-md border bg-orange-900/40 border-orange-500/50 p-3 text-orange-100 text-sm">
                    <strong>The blade is yours.</strong> Its weight settles into your hand as
                    though it has been waiting your whole life. Every dwarf in the realm will
                    know, before you leave this tomb, that Y&apos;ros has chosen.
                  </div>
                )}
                <div className="mt-4 flex justify-end">
                  <Button
                    onClick={() => setResultOpen(false)}
                    className="bg-stone-800 hover:bg-stone-700 text-stone-100"
                    data-testid="tongue-result-close-btn"
                  >
                    Withdraw from the altar
                  </Button>
                </div>
              </>
            );
          })()}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default TongueOfYros;
