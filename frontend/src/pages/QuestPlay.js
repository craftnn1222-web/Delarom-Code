import React, { useEffect, useState, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import { getQuest, getQuestActions, submitQuestAction, getMyQuests, getQuestParticipants } from '../utils/api';
import { toast } from 'sonner';
import AnimatedBackground from '../components/AnimatedBackground';
import Navbar from '../components/Navbar';
import { Button } from '../components/ui/button';
import { Textarea } from '../components/ui/textarea';
import { ArrowLeft, Sparkles, Coins, Lock, UserCircle, Users } from 'lucide-react';

const QuestPlay = () => {
  const { questId } = useParams();
  const [quest, setQuest] = useState(null);
  const [actions, setActions] = useState([]);
  const [accepted, setAccepted] = useState(false);
  const [acceptanceStatus, setAcceptanceStatus] = useState(null);
  const [character, setCharacter] = useState(null);
  const [participants, setParticipants] = useState([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [actionText, setActionText] = useState('');

  const fetchActions = useCallback(async () => {
    try {
      const res = await getQuestActions(questId);
      setActions(res.data || []);
    } catch (error) {
      console.error('Failed to load quest scene:', error);
    }
  }, [questId]);

  const fetchAll = useCallback(async () => {
    try {
      const [questRes, mineRes, partsRes] = await Promise.all([
        getQuest(questId),
        getMyQuests(),
        getQuestParticipants(questId).catch(() => ({ data: [] })),
      ]);
      setQuest(questRes.data);
      setParticipants(partsRes.data || []);
      const entry = (mineRes.data || []).find((m) => m.quest?.id === questId);
      if (entry) {
        setAccepted(true);
        setCharacter(entry.character || null);
        setAcceptanceStatus(entry.acceptance?.status || 'accepted');
      } else {
        setAccepted(false);
      }
      await fetchActions();
    } catch (error) {
      toast.error('Failed to load this quest.');
    } finally {
      setLoading(false);
    }
  }, [questId, fetchActions]);

  useEffect(() => {
    fetchAll();
    const interval = setInterval(fetchActions, 12000);
    return () => clearInterval(interval);
  }, [fetchAll, fetchActions]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!actionText.trim()) return;
    setSubmitting(true);
    try {
      await submitQuestAction(questId, actionText);
      setActionText('');
      await fetchActions();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to submit action');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen relative">
        <AnimatedBackground />
        <Navbar />
        <div className="relative z-10 container mx-auto px-4 py-20 text-center">
          <div className="text-white text-xl">Unrolling the contract...</div>
        </div>
      </div>
    );
  }

  const visible = actions.filter((a) => a.action_text || a.ai_response);

  return (
    <div className="min-h-screen relative" data-testid="quest-play-scene">
      <AnimatedBackground />
      <Navbar />

      <div className="relative z-10 container mx-auto px-4 py-8 max-w-5xl">
        <Link to="/my-quests">
          <Button variant="ghost" className="mb-6 text-purple-400" data-testid="quest-play-back">
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to My Quests
          </Button>
        </Link>

        {/* Quest header / context */}
        <div className="glass-dark p-8 rounded-2xl mb-6">
          <h1 className="text-4xl font-bold text-white mb-1" data-testid="quest-play-title">
            {quest?.title || 'Quest'}
          </h1>
          {quest?.creator_username && (
            <p className="text-sm text-gray-400 mb-4">by {quest.creator_username}</p>
          )}
          <div className="flex flex-wrap gap-2 mb-4">
            {quest?.nation && (
              <span className="bg-purple-600/20 text-purple-300 px-3 py-1 rounded-full text-xs font-semibold capitalize">
                {quest.nation}
              </span>
            )}
            {quest?.difficulty && (
              <span className="bg-yellow-500/20 text-yellow-400 px-3 py-1 rounded-full text-xs font-semibold capitalize">
                {quest.difficulty}
              </span>
            )}
            {quest?.reward_currency != null && (
              <span className="bg-amber-500/20 text-amber-300 px-3 py-1 rounded-full text-xs font-semibold flex items-center gap-1">
                <Coins className="w-3.5 h-3.5" />
                {quest.reward_currency}g
              </span>
            )}
          </div>
          {quest?.description && (
            <p className="text-gray-300 text-sm mb-4">{quest.description}</p>
          )}
          <div className="p-3 bg-purple-600/20 border border-purple-500/30 rounded-lg">
            <p className="text-sm text-purple-200">
              <Sparkles className="w-4 h-4 inline mr-2" />
              Roleplay your quest here — the AI Quest Master narrates the scene and responds to your actions.
            </p>
          </div>
          {accepted && character && (
            <div className="mt-4 flex items-center gap-2 text-sm text-amber-200" data-testid="quest-play-playing-as">
              <UserCircle className="w-5 h-5 text-amber-400" />
              Playing as <span className="font-bold text-amber-300">{character.name}</span>
            </div>
          )}
        </div>

        {!accepted ? (
          <div
            className="glass-dark p-8 rounded-xl text-center border border-amber-500/40 bg-amber-900/15"
            data-testid="quest-play-not-accepted"
          >
            <Lock className="w-8 h-8 text-amber-300 mx-auto mb-3" />
            <p className="text-amber-100 font-semibold mb-2">You haven&apos;t accepted this quest yet</p>
            <p className="text-sm text-amber-100/70 mb-4">
              Accept it from the Quest Board to step into its scene.
            </p>
            <Link to="/quests">
              <Button className="bg-gradient-to-r from-purple-600 to-pink-600" data-testid="quest-play-go-board">
                Go to Quest Board
              </Button>
            </Link>
          </div>
        ) : (
          <>
            {/* Fellow adventurers on this quest */}
            {participants.length > 0 && (
              <div className="glass-dark p-6 rounded-xl mb-6" data-testid="quest-companions-panel">
                <h2 className="text-lg font-bold text-purple-300 mb-3 flex items-center gap-2">
                  <Users className="w-5 h-5" />
                  Fellow Adventurers ({participants.length})
                </h2>
                <div className="grid sm:grid-cols-2 gap-3">
                  {participants.map((p) => {
                    const isMe = p.character?.id === character?.id;
                    const done = p.acceptance?.status === 'completed';
                    return (
                      <div
                        key={p.character?.id || p.acceptance?.id}
                        className={`flex items-center gap-3 p-3 rounded-lg border ${isMe ? 'border-amber-500/50 bg-amber-900/15' : 'border-purple-500/20 bg-black/20'}`}
                        data-testid={`quest-companion-${p.character?.id}`}
                      >
                        <UserCircle className={`w-8 h-8 flex-shrink-0 ${isMe ? 'text-amber-400' : 'text-purple-300'}`} />
                        <div className="min-w-0 flex-1">
                          <p className={`font-semibold truncate ${isMe ? 'text-amber-200' : 'text-white'}`}>
                            {p.character?.name}
                            {isMe && <span className="ml-1 text-xs text-amber-300/80">(you)</span>}
                          </p>
                          <p className="text-xs text-gray-400 truncate capitalize">
                            {p.character?.race} · {p.character?.class}
                          </p>
                        </div>
                        <span className={`text-xs px-2 py-0.5 rounded-full font-semibold ${done ? 'bg-green-500/20 text-green-400' : 'bg-blue-500/20 text-blue-300'}`}>
                          {done ? 'Done' : 'Questing'}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Scene feed */}
            <div className="glass-dark p-6 rounded-xl mb-6">
              <h2 className="text-2xl font-bold text-purple-300 mb-4">Quest Scene</h2>
              {visible.length === 0 ? (
                <p className="text-gray-400 text-center py-8" data-testid="quest-play-empty">
                  The Quest Master awaits. Write your first action to begin the tale.
                </p>
              ) : (
                <div className="space-y-4 max-h-[600px] overflow-y-auto">
                  {visible.map((action) => {
                    const isOpening = action.action_text === '[Quest Opening]';
                    return (
                      <div key={action.id} className="space-y-2" data-testid={`quest-play-post-${action.id}`}>
                        {action.action_text && !isOpening && (
                          <div className="glass p-4 rounded-lg border-l-4 border-blue-500">
                            <span className="font-bold text-blue-300">{action.character_name}</span>
                            <p className="text-white whitespace-pre-wrap mt-1">{action.action_text}</p>
                          </div>
                        )}
                        {action.ai_response && (
                          <div className={`glass p-4 rounded-lg border-l-4 border-purple-500 bg-purple-900/20 ${isOpening ? '' : 'ml-8'}`}>
                            <div className="flex items-center gap-2 mb-2">
                              <span className="font-bold text-purple-300">🎭 Quest Master</span>
                            </div>
                            <p className="text-gray-200 whitespace-pre-wrap italic">{action.ai_response}</p>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Action input */}
            {acceptanceStatus === 'completed' ? (
              <div
                className="glass-dark p-6 rounded-xl text-center border border-green-500/40 bg-green-900/15"
                data-testid="quest-play-completed"
              >
                <p className="text-green-300 font-semibold">This quest is complete.</p>
                <p className="text-sm text-green-100/70 mt-1">The scene above is preserved as a record of your tale.</p>
              </div>
            ) : (
              <div className="glass-dark p-6 rounded-xl">
                <h3 className="text-xl font-bold text-purple-300 mb-4">Your Action</h3>
                <form onSubmit={handleSubmit} className="space-y-4">
                  <Textarea
                    value={actionText}
                    onChange={(e) => setActionText(e.target.value)}
                    placeholder="Describe what your character does in this quest scene..."
                    className="bg-black/20 border-purple-500/30 text-white min-h-[120px]"
                    required
                    data-testid="quest-play-action-input"
                  />
                  <Button
                    type="submit"
                    disabled={submitting}
                    className="w-full bg-gradient-to-r from-purple-600 to-pink-600"
                    data-testid="quest-play-submit-btn"
                  >
                    {submitting ? 'The Quest Master responds...' : '✒️ Submit Action'}
                  </Button>
                </form>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default QuestPlay;
