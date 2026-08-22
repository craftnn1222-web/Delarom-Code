import React, { useEffect, useState } from 'react';
import { getMyQuests } from '../utils/api';
import { toast } from 'sonner';
import AnimatedBackground from '../components/AnimatedBackground';
import Navbar from '../components/Navbar';
import { Button } from '../components/ui/button';
import { Check, Coins, Clock, Trophy } from 'lucide-react';

const MyQuests = () => {
  const [myQuests, setMyQuests] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchMyQuests();
  }, []);

  const fetchMyQuests = async () => {
    try {
      const response = await getMyQuests();
      setMyQuests(response.data);
    } catch (_error) {
      toast.error('Failed to load your quests');
    } finally {
      setLoading(false);
    }
  };

  const handleCompleteQuest = async () => {
    toast.error('Only the quest creator can complete quests now. Please wait for the quest creator to mark it complete.');
  };

  if (loading) {
    return (
      <div className="min-h-screen relative">
        <AnimatedBackground />
        <Navbar />
        <div className="relative z-10 container mx-auto px-4 py-20 text-center">
          <div className="text-white text-xl">Loading your quests...</div>
        </div>
      </div>
    );
  }

  const activeQuests = myQuests.filter(q => q.acceptance.status === 'accepted');
  const completedQuests = myQuests.filter(q => q.acceptance.status === 'completed');

  return (
    <div className="min-h-screen relative">
      <AnimatedBackground />
      <Navbar />
      
      <div className="relative z-10 container mx-auto px-4 py-8">
        <h1 className="text-4xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-pink-600 mb-8" data-testid="my-quests-title">
          🎯 My Quests
        </h1>

        {/* Active Quests */}
        <div className="mb-12">
          <h2 className="text-2xl font-bold text-purple-300 mb-4 flex items-center gap-2">
            <Clock className="w-6 h-6" />
            Active Quests ({activeQuests.length})
          </h2>
          {activeQuests.length === 0 ? (
            <div className="glass-dark p-8 rounded-xl text-center text-gray-400">
              No active quests. Visit the Quest Board to accept quests!
            </div>
          ) : (
            <div className="grid md:grid-cols-2 gap-6">
              {activeQuests.map(({ quest, acceptance, character }) => (
                <div key={acceptance.id} className="glass-dark p-6 rounded-xl" data-testid={`active-quest-${quest.id}`}>
                  <div className="flex items-start justify-between mb-4">
                    <div>
                      <h3 className="text-xl font-bold text-white mb-1">{quest.title}</h3>
                      <p className="text-sm text-gray-400">by {quest.creator_username}</p>
                    </div>
                    <div className="bg-blue-500/20 text-blue-400 px-3 py-1 rounded-full text-xs font-semibold">
                      IN PROGRESS
                    </div>
                  </div>

                  <p className="text-gray-300 text-sm mb-4">{quest.description}</p>

                  <div className="space-y-2 mb-4">
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-gray-400">Character:</span>
                      <span className="text-purple-300">{character?.name || 'Unknown'}</span>
                    </div>
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-gray-400">Nation:</span>
                      <span className="text-purple-300">{quest.nation}</span>
                    </div>
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-gray-400">Difficulty:</span>
                      <span className="text-yellow-400 capitalize">{quest.difficulty}</span>
                    </div>
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-gray-400">Reward:</span>
                      <span className="text-yellow-400 font-bold flex items-center gap-1">
                        <Coins className="w-4 h-4" />
                        {quest.reward_currency}
                      </span>
                    </div>
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-gray-400">Accepted:</span>
                      <span className="text-gray-300">{new Date(acceptance.accepted_at).toLocaleDateString()}</span>
                    </div>
                  </div>

                  <Button
                    onClick={handleCompleteQuest}
                    className="w-full bg-gradient-to-r from-gray-600 to-gray-700 hover:from-gray-700 hover:to-gray-800"
                    data-testid={`complete-quest-${quest.id}`}
                  >
                    <Check className="w-4 h-4 mr-2" />
                    Await Creator Completion
                  </Button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Completed Quests */}
        <div>
          <h2 className="text-2xl font-bold text-green-400 mb-4 flex items-center gap-2">
            <Trophy className="w-6 h-6" />
            Completed Quests ({completedQuests.length})
          </h2>
          {completedQuests.length === 0 ? (
            <div className="glass-dark p-8 rounded-xl text-center text-gray-400">
              No completed quests yet. Complete your first quest to see it here!
            </div>
          ) : (
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
              {completedQuests.map(({ quest, acceptance, character }) => (
                <div key={acceptance.id} className="glass p-4 rounded-xl opacity-75" data-testid={`completed-quest-${quest.id}`}>
                  <div className="flex items-start justify-between mb-3">
                    <h3 className="font-bold text-white text-lg">{quest.title}</h3>
                    <div className="bg-green-500/20 text-green-400 px-2 py-1 rounded text-xs font-semibold">
                      ✓ DONE
                    </div>
                  </div>

                  <div className="space-y-1 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-400">Character:</span>
                      <span className="text-purple-300">{character?.name || 'Unknown'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-400">Reward Earned:</span>
                      <span className="text-yellow-400 font-bold flex items-center gap-1">
                        <Coins className="w-3 h-3" />
                        {quest.reward_currency}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-400">Completed:</span>
                      <span className="text-gray-300">{new Date(acceptance.completed_at).toLocaleDateString()}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default MyQuests;