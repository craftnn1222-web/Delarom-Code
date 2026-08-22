import React, { useEffect, useState, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { getForumPosts, createForumPost, getMyCharacters } from '../utils/api';
import { toast } from 'sonner';
import AnimatedBackground from '../components/AnimatedBackground';
import Navbar from '../components/Navbar';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { MessageSquare, Plus, MessageCircle, User } from 'lucide-react';

const Forums = () => {
  const [posts, setPosts] = useState([]);
  const [characters, setCharacters] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [selectedNation, setSelectedNation] = useState('all');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [formData, setFormData] = useState({
    title: '',
    content: '',
    category: 'General',
    nation: 'Ammeonon',
    character_id: '',
  });

  const fetchData = useCallback(async () => {
    const params = {};
    if (selectedNation !== 'all') params.nation = selectedNation;
    if (selectedCategory !== 'all') params.category = selectedCategory;

    // allSettled so a forum-API blip doesn't also blank out the user's
    // characters (which hides the "post" form).
    const [postsRes, charsRes] = await Promise.allSettled([
      getForumPosts(params),
      getMyCharacters()
    ]);
    if (postsRes.status === 'fulfilled') {
      setPosts(postsRes.value.data);
    } else {
      toast.error('Failed to load forum posts');
    }
    if (charsRes.status === 'fulfilled') {
      const chars = charsRes.value.data || [];
      setCharacters(chars);
      if (chars.length > 0) {
        setFormData(prev => prev.character_id ? prev : { ...prev, character_id: chars[0].id });
      }
    }
    setLoading(false);
  }, [selectedNation, selectedCategory]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (characters.length === 0) {
      toast.error('You need to create a character first!');
      return;
    }

    try {
      await createForumPost(formData);
      toast.success('Post created successfully!');
      setIsDialogOpen(false);
      setFormData({
        title: '',
        content: '',
        category: 'General',
        nation: 'Ammeonon',
        character_id: characters[0]?.id || '',
      });
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create post');
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen relative">
        <AnimatedBackground />
        <Navbar />
        <div className="relative z-10 container mx-auto px-4 py-20 text-center">
          <div className="text-white text-xl">Loading forums...</div>
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
            <h1 className="text-4xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-pink-600 mb-2" data-testid="forums-title">
              💬 Roleplay Forums
            </h1>
            <p className="text-gray-400">Share stories and adventures with the community</p>
          </div>
          <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
            <DialogTrigger asChild>
              <Button className="bg-gradient-to-r from-purple-600 to-pink-600" data-testid="create-post-btn">
                <Plus className="w-4 h-4 mr-2" />
                New Post
              </Button>
            </DialogTrigger>
            <DialogContent
              className="bg-gray-900 border-purple-500/30 text-white max-w-2xl"
              onPointerDownOutside={(e) => e.preventDefault()}
              onInteractOutside={(e) => e.preventDefault()}
            >
              <DialogHeader>
                <DialogTitle className="text-2xl text-purple-300">Create Forum Post</DialogTitle>
              </DialogHeader>
              <form onSubmit={handleSubmit} className="space-y-4" data-testid="post-form">
                <div>
                  <Label htmlFor="character_id">Post as Character *</Label>
                  <Select 
                    name="character_id" 
                    value={formData.character_id} 
                    onValueChange={(value) => setFormData({...formData, character_id: value})}
                  >
                    <SelectTrigger className="bg-black/20 border-purple-500/30" data-testid="post-character-select">
                      <SelectValue placeholder="Select character" />
                    </SelectTrigger>
                    <SelectContent className="bg-gray-900 border-purple-500/30">
                      {characters.map((char) => (
                        <SelectItem key={char.id} value={char.id}>
                          {char.name} ({char.race})
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <Label htmlFor="title">Post Title *</Label>
                  <Input
                    id="title"
                    name="title"
                    value={formData.title}
                    onChange={handleChange}
                    required
                    className="bg-black/20 border-purple-500/30"
                    placeholder="Give your post a title..."
                    data-testid="post-title-input"
                  />
                </div>

                <div>
                  <Label htmlFor="content">Content *</Label>
                  <Textarea
                    id="content"
                    name="content"
                    value={formData.content}
                    onChange={handleChange}
                    required
                    className="bg-black/20 border-purple-500/30 min-h-[150px]"
                    placeholder="Share your story..."
                    data-testid="post-content-input"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label htmlFor="category">Category *</Label>
                    <Input
                      id="category"
                      name="category"
                      value={formData.category}
                      onChange={handleChange}
                      required
                      className="bg-black/20 border-purple-500/30"
                      placeholder="e.g., Adventure, Lore"
                      data-testid="post-category-input"
                    />
                  </div>

                  <div>
                    <Label htmlFor="nation">Nation *</Label>
                    <Select name="nation" value={formData.nation} onValueChange={(value) => setFormData({...formData, nation: value})}>
                      <SelectTrigger className="bg-black/20 border-purple-500/30" data-testid="post-nation-select">
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
                </div>

                <Button type="submit" className="w-full bg-gradient-to-r from-purple-600 to-pink-600" data-testid="post-submit-btn">
                  Create Post
                </Button>
              </form>
            </DialogContent>
          </Dialog>
        </div>

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
            <Label className="text-gray-400 text-sm mb-2 block">Filter by Category</Label>
            <Input
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              placeholder="Type category..."
              className="bg-black/20 border-purple-500/30"
            />
          </div>
        </div>

        {/* Posts List */}
        {posts.length === 0 ? (
          <div className="glass-dark p-12 rounded-2xl text-center">
            <MessageSquare className="w-16 h-16 mx-auto mb-4 text-purple-400" />
            <h2 className="text-2xl font-bold mb-2 text-white">No Posts Yet</h2>
            <p className="text-gray-400 mb-6">Be the first to share a story!</p>
            <Button onClick={() => setIsDialogOpen(true)} className="bg-gradient-to-r from-purple-600 to-pink-600">
              Create First Post
            </Button>
          </div>
        ) : (
          <div className="space-y-4">
            {posts.map((post) => (
              <Link key={post.id} to={`/forums/${post.id}`}>
                <div className="glass-dark p-6 rounded-xl hover:bg-white/10 transition" data-testid={`post-${post.id}`}>
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex-1">
                      <h3 className="text-xl font-bold text-white mb-2">{post.title}</h3>
                      <div className="flex items-center gap-3 text-sm text-gray-400">
                        <div className="flex items-center gap-1">
                          <User className="w-4 h-4" />
                          {post.character_name}
                        </div>
                        <span>•</span>
                        <span>{post.username}</span>
                        <span>•</span>
                        <span>{new Date(post.created_at).toLocaleDateString()}</span>
                      </div>
                    </div>
                    <div className="flex gap-2">
                      <span className="px-3 py-1 bg-purple-600/30 text-purple-300 rounded-full text-xs font-semibold">
                        {post.category}
                      </span>
                      <span className="px-3 py-1 bg-blue-600/30 text-blue-300 rounded-full text-xs font-semibold">
                        {post.nation}
                      </span>
                    </div>
                  </div>

                  <p className="text-gray-300 mb-3 line-clamp-2">{post.content}</p>

                  <div className="flex items-center gap-2 text-sm text-gray-400">
                    <MessageCircle className="w-4 h-4" />
                    <span>{post.replies_count} replies</span>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default Forums;