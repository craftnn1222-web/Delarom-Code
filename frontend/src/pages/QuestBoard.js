import React, { useEffect, useState, useCallback } from 'react';
import { getQuests, createQuest, acceptQuest, getMyCharacters, getMyQuests, getMyCreatedQuests, deleteQuest } from '../utils/api';
import { toast } from 'sonner';
import AnimatedBackground from '../components/AnimatedBackground';
import Navbar from '../components/Navbar';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Plus, Sword, Trophy, Zap, Crown, Coins } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';


const QuestBoard = () => {
  const { currentUser } = useAuth();
  const [quests, setQuests] = useState([]);
  const [characters, setCharacters] = useState([]);
  const [loading, setLoading] = useState(true);
  const [myCreatedQuests, setMyCreatedQuests] = useState([]);
  const [activeTab, setActiveTab] = useState('available');

  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [selectedNation, setSelectedNation] = useState('all');
  const [selectedDifficulty, setSelectedDifficulty] = useState('all');
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    difficulty: 'easy',
    reward_currency: 100,
    nation: 'Ammeonon',
    category: 'Combat',
    max_acceptors: 10,
  });

  const fetchData = useCallback(async () => {
    const params = {};
    if (selectedNation !== 'all') params.nation = selectedNation;
    if (selectedDifficulty !== 'all') params.difficulty = selectedDifficulty;

    const [questsRes, charsRes, , myCreatedRes] = await Promise.allSettled([
      getQuests(params),
      getMyCharacters(),
      getMyQuests(),
      getMyCreatedQuests()
    ]);
    if (questsRes.status === 'fulfilled') setQuests(questsRes.value.data);
    else toast.error('Failed to load quests');
    if (myCreatedRes && myCreatedRes.status === 'fulfilled') setMyCreatedQuests(myCreatedRes.value.data || []);
    if (charsRes.status === 'fulfilled') setCharacters(charsRes.value.data);
    setLoading(false);
  }, [selectedNation, selectedDifficulty]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData({ ...formData, [name]: name === 'reward_currency' || name === 'max_acceptors' ? parseInt(value) : value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await createQuest(formData);
      toast.success('Quest created successfully!');
      setIsDialogOpen(false);
      setFormData({
        title: '',
        description: '',
        difficulty: 'easy',
        reward_currency: 100,
        nation: 'Ammeonon',
        category: 'Combat',
        max_acceptors: 10,
      });
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create quest');
    }
  };

  const handleAcceptQuest = async (questId) => {
    if (characters.length === 0) {
      toast.error('You need to create a character first!');
      return;
    }

    const characterId = characters[0].id; // Use first character for simplicity
    try {
      await acceptQuest(questId, characterId);
      toast.success('Quest accepted! Check "My Quests" to complete it.');
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to accept quest');
    }
  };

  const handleDeleteQuest = async (questId, questTitle) => {
    if (!window.confirm(`Are you sure you want to delete "${questTitle}"?`)) {
      return;
    }
    
    try {
      await deleteQuest(questId);
      toast.success('Quest deleted successfully!');
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to delete quest');
    }
  };

  const getDifficultyColor = (difficulty) => {
    switch (difficulty) {
      case 'easy': return 'text-green-400 border-green-400';
      case 'medium': return 'text-yellow-400 border-yellow-400';
      case 'hard': return 'text-orange-400 border-orange-400';
      case 'legendary': return 'text-red-400 border-red-400';
      default: return 'text-gray-400 border-gray-400';
    }
  };

  const getDifficultyIcon = (difficulty) => {
    switch (difficulty) {
      case 'easy': return <Sword className="w-4 h-4" />;
      case 'medium': return <Trophy className="w-4 h-4" />;
      case 'hard': return <Zap className="w-4 h-4" />;
      case 'legendary': return <Crown className="w-4 h-4" />;
      default: return <Sword className="w-4 h-4" />;
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen relative">
        <AnimatedBackground />
        <Navbar />
        <div className="relative z-10 container mx-auto px-4 py-20 text-center">
          <div className="text-white text-xl">Loading quests...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen relative">
      <AnimatedBackground />
      <Navbar />
      
      <div className="relative z-10 container mx-auto px-4 py-8">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-4xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-pink-600 mb-2" data-testid="quest-board-title">
              ⚔️ Quest Board
            </h1>
            <p className="text-gray-400">Accept quests and earn rewards!</p>
          </div>
          <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
            <DialogTrigger asChild>
              <Button className="bg-gradient-to-r from-purple-600 to-pink-600" data-testid="create-quest-btn">
                <Plus className="w-4 h-4 mr-2" />
                Create Quest
              </Button>
            </DialogTrigger>
            <DialogContent
              className="bg-gray-900 border-purple-500/30 text-white max-w-2xl"
              onPointerDownOutside={(e) => e.preventDefault()}
              onInteractOutside={(e) => e.preventDefault()}
            >
              <DialogHeader>
                <DialogTitle className="text-2xl text-purple-300">Create New Quest</DialogTitle>
              </DialogHeader>
              <form onSubmit={handleSubmit} className="space-y-4" data-testid="quest-form">
                <div>
                  <Label htmlFor="title">Quest Title *</Label>
                  <Input
                    id="title"
                    name="title"
                    value={formData.title}
                    onChange={handleChange}
                    required
                    className="bg-black/20 border-purple-500/30"
                    placeholder="e.g., Slay the Dragon of Emberdeep"
                    data-testid="quest-title-input"
                  />
                </div>

                <div>
                  <Label htmlFor="description">Description *</Label>
                  <Textarea
                    id="description"
                    name="description"
                    value={formData.description}
                    onChange={handleChange}
                    required
                    className="bg-black/20 border-purple-500/30 min-h-[100px]"
                    placeholder="Describe the quest objectives..."
                    data-testid="quest-description-input"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label htmlFor="difficulty">Difficulty *</Label>
                    <Select name="difficulty" value={formData.difficulty} onValueChange={(value) => setFormData({...formData, difficulty: value})}>
                      <SelectTrigger className="bg-black/20 border-purple-500/30" data-testid="quest-difficulty-select">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent className="bg-gray-900 border-purple-500/30">
                        <SelectItem value="easy">Easy</SelectItem>
                        <SelectItem value="medium">Medium</SelectItem>
                        <SelectItem value="hard">Hard</SelectItem>
                        <SelectItem value="legendary">Legendary</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div>
                    <Label htmlFor="reward_currency">Reward (Gold) *</Label>
                    <Input
                      id="reward_currency"
                      name="reward_currency"
                      type="number"
                      value={formData.reward_currency}
                      onChange={handleChange}
                      required
                      min="1"
                      className="bg-black/20 border-purple-500/30"
                      data-testid="quest-reward-input"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label htmlFor="nation">Nation *</Label>
                    <Select name="nation" value={formData.nation} onValueChange={(value) => setFormData({...formData, nation: value})}>
                      <SelectTrigger className="bg-black/20 border-purple-500/30" data-testid="quest-nation-select">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent className="bg-gray-900 border-purple-500/30">
                        <SelectItem value="Ammeonon">Ammeonon</SelectItem>
                        <SelectItem value="Selindori">Selindori</SelectItem>
                        <SelectItem value="Dhor-Kuldor">Dhor-Kuldor</SelectItem>
                        <SelectItem value="Aigraels">Aigraels</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div>
                    <Label htmlFor="category">Category *</Label>
                    <Input
                      id="category"
                      name="category"
                      value={formData.category}
                      onChange={handleChange}
                      required
                      className="bg-black/20 border-purple-500/30"
                      placeholder="e.g., Combat, Exploration"
                      data-testid="quest-category-input"
                    />
                  </div>
                </div>

                <div>
                  <Label htmlFor="max_acceptors">Max Acceptors *</Label>
                  <Input
                    id="max_acceptors"
                    name="max_acceptors"
                    type="number"
                    value={formData.max_acceptors}
                    onChange={handleChange}
                    required
                    min="1"
                    className="bg-black/20 border-purple-500/30"
                    data-testid="quest-max-acceptors-input"
                  />
                </div>

                <Button type="submit" className="w-full bg-gradient-to-r from-purple-600 to-pink-600" data-testid="quest-submit-btn">
                  Create Quest
                </Button>
              </form>
            </DialogContent>
          </Dialog>
        </div>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="mb-4">
          <TabsList className="bg-gray-900/60 border border-purple-500/40 rounded-xl">
            <TabsTrigger value="available" className="data-[state=active]:bg-purple-600 data-[state=active]:text-white">
              Available Quests
            </TabsTrigger>
            <TabsTrigger value="created" className="data-[state=active]:bg-purple-600 data-[state=active]:text-white">
              My Created Quests
            </TabsTrigger>
          </TabsList>

          <TabsContent value="available" className="mt-4">
            {/* Filters */}
            <div className="glass-dark p-4 rounded-xl mb-6 flex gap-4">
          <div className="flex-1">
            <Label className="text-gray-400 text-sm mb-2 block">Filter by Nation</Label>
            <Select value={selectedNation} onValueChange={setSelectedNation}>
              <SelectTrigger className="bg-black/20 border-purple-500/30" data-testid="filter-nation-select">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-gray-900 border-purple-500/30">
                <SelectItem value="all">All Nations</SelectItem>
                <SelectItem value="Ammeonon">Ammeonon</SelectItem>
                <SelectItem value="Selindori">Selindori</SelectItem>
                <SelectItem value="Dhor-Kuldor">Dhor-Kuldor</SelectItem>
                <SelectItem value="Aigraels">Aigraels</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="flex-1">
            <Label className="text-gray-400 text-sm mb-2 block">Filter by Difficulty</Label>
            <Select value={selectedDifficulty} onValueChange={setSelectedDifficulty}>
              <SelectTrigger className="bg-black/20 border-purple-500/30" data-testid="filter-difficulty-select">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-gray-900 border-purple-500/30">
                <SelectItem value="all">All Difficulties</SelectItem>
                <SelectItem value="easy">Easy</SelectItem>
                <SelectItem value="medium">Medium</SelectItem>
                <SelectItem value="hard">Hard</SelectItem>
                <SelectItem value="legendary">Legendary</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        {/* Quests Grid */}
        {quests.length === 0 ? (
          <div className="glass-dark p-12 rounded-2xl text-center">
            <Sword className="w-16 h-16 mx-auto mb-4 text-purple-400" />
            <h2 className="text-2xl font-bold mb-2 text-white">No Quests Available</h2>
            <p className="text-gray-400 mb-6">Be the first to create a quest!</p>
            <Button onClick={() => setIsDialogOpen(true)} className="bg-gradient-to-r from-purple-600 to-pink-600">
              Create First Quest
            </Button>
          </div>
        ) : (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {quests.map((quest) => (
              <div key={quest.id} className="glass-dark p-6 rounded-xl relative" data-testid={`quest-card-${quest.id}`}>
                <div className="flex items-start justify-between mb-3">
                  <div className="flex-1">
                    <h3 className="text-xl font-bold text-white mb-1">{quest.title}</h3>
                    <p className="text-sm text-gray-400">by {quest.creator_username}</p>
                  </div>
                  <div className={`flex items-center gap-1 px-2 py-1 rounded border ${getDifficultyColor(quest.difficulty)}`}>
                    {getDifficultyIcon(quest.difficulty)}
                    <span className="text-xs font-semibold uppercase">{quest.difficulty}</span>
                  </div>
                </div>

                <p className="text-gray-300 text-sm mb-4 line-clamp-3">{quest.description}</p>

                <div className="space-y-2 mb-4">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-400">Nation:</span>
                    <span className="text-purple-300">{quest.nation}</span>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-400">Category:</span>
                    <span className="text-purple-300">{quest.category}</span>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-400">Reward:</span>
                    <span className="text-yellow-400 font-bold flex items-center gap-1">
                      <Coins className="w-4 h-4" />
                      {quest.reward_currency}
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-400">Acceptors:</span>
                    <span className="text-white">{quest.current_acceptors} / {quest.max_acceptors}</span>
                  </div>
                </div>

                {(currentUser?.role === 'admin' || currentUser?.role === 'moderator' || quest.creator_id === currentUser?.id) && (
                  <button
                    type="button"
                    onClick={() => handleDeleteQuest(quest.id, quest.title)}
                    className="absolute top-3 right-3 text-xs text-red-300 hover:text-red-100 bg-red-900/50 hover:bg-red-800/60 rounded-full px-2 py-1 border border-red-500/60"
                  >
                    Remove
                  </button>
                )}

                <Button
                  onClick={() => handleAcceptQuest(quest.id)}
                  className="w-full bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700"
                  disabled={quest.current_acceptors >= quest.max_acceptors}
                  data-testid={`accept-quest-${quest.id}`}
                >
                  {quest.current_acceptors >= quest.max_acceptors ? 'Quest Full' : 'Accept Quest'}
                </Button>
              </div>
            ))}
          </div>
        )}
          </TabsContent>

          <TabsContent value="created" className="mt-4">
            {/* My Created Quests */}
            {myCreatedQuests.length === 0 ? (
              <div className="glass-dark p-12 rounded-2xl text-center">
                <Sword className="w-16 h-16 mx-auto mb-4 text-purple-400" />
                <h2 className="text-2xl font-bold mb-2 text-white">No Created Quests</h2>
                <p className="text-gray-400 mb-6">You haven't created any quests yet!</p>
                <Button onClick={() => setIsDialogOpen(true)} className="bg-gradient-to-r from-purple-600 to-pink-600">
                  Create Your First Quest
                </Button>
              </div>
            ) : (
              <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
                {myCreatedQuests.map((quest) => (
                  <div key={quest.id} className="glass-dark p-6 rounded-xl relative" data-testid={`created-quest-card-${quest.id}`}>
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex-1">
                        <h3 className="text-xl font-bold text-white mb-1">{quest.title}</h3>
                        <p className="text-sm text-gray-400">Created by you</p>
                      </div>
                      <div className={`flex items-center gap-1 px-2 py-1 rounded border ${getDifficultyColor(quest.difficulty)}`}>
                        {getDifficultyIcon(quest.difficulty)}
                        <span className="text-xs font-semibold uppercase">{quest.difficulty}</span>
                      </div>
                    </div>

                    <p className="text-gray-300 text-sm mb-4 line-clamp-3">{quest.description}</p>

                    <div className="space-y-2 mb-4">
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-gray-400">Nation:</span>
                        <span className="text-purple-300">{quest.nation}</span>
                      </div>
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-gray-400">Category:</span>
                        <span className="text-purple-300">{quest.category}</span>
                      </div>
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-gray-400">Reward:</span>
                        <span className="text-yellow-400 font-bold flex items-center gap-1">
                          <Coins className="w-4 h-4" />
                          {quest.reward_currency}
                        </span>
                      </div>
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-gray-400">Acceptors:</span>
                        <span className="text-white">{quest.current_acceptors} / {quest.max_acceptors}</span>
                      </div>
                    </div>

                    {(currentUser?.role === 'admin' || currentUser?.role === 'moderator' || quest.creator_id === currentUser?.id) && (
                      <button
                        type="button"
                        onClick={() => handleDeleteQuest(quest.id, quest.title)}
                        className="absolute top-3 right-3 text-xs text-red-300 hover:text-red-100 bg-red-900/50 hover:bg-red-800/60 rounded-full px-2 py-1 border border-red-500/60"
                      >
                        Remove
                      </button>
                    )}

                    <div className="text-sm text-gray-400 mb-4">
                      Status: <span className="text-green-400">Active</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
};

export default QuestBoard;