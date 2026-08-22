import React, { useEffect, useState, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import { getForumPost, getPostReplies, createReply, getMyCharacters } from '../utils/api';
import { toast } from 'sonner';
import AnimatedBackground from '../components/AnimatedBackground';
import Navbar from '../components/Navbar';
import { Button } from '../components/ui/button';
import { Textarea } from '../components/ui/textarea';
import { Label } from '../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { ArrowLeft, User, MessageCircle } from 'lucide-react';
import FactionBadge from '../components/factions/FactionBadge';
import useFactionBadges from '../hooks/useFactionBadges';

const ForumPost = () => {
  const { postId } = useParams();
  const [post, setPost] = useState(null);
  const [replies, setReplies] = useState([]);
  const [characters, setCharacters] = useState([]);
  const [loading, setLoading] = useState(true);
  const [replyContent, setReplyContent] = useState('');
  const [selectedCharacterId, setSelectedCharacterId] = useState('');

  // Batch-fetch faction badges for the OP and every reply author.
  const allCharIds = [
    ...(post?.character_id ? [post.character_id] : []),
    ...replies.map((r) => r.character_id).filter(Boolean),
  ];
  const factionsByChar = useFactionBadges(allCharIds);

  const fetchData = useCallback(async () => {
    const [postRes, repliesRes, charsRes] = await Promise.allSettled([
      getForumPost(postId),
      getPostReplies(postId),
      getMyCharacters()
    ]);
    if (postRes.status === 'fulfilled') setPost(postRes.value.data);
    else toast.error('Failed to load post');
    if (repliesRes.status === 'fulfilled') setReplies(repliesRes.value.data);
    if (charsRes.status === 'fulfilled') {
      const chars = charsRes.value.data || [];
      setCharacters(chars);
      if (chars.length > 0) setSelectedCharacterId(chars[0].id);
    }
    setLoading(false);
  }, [postId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleReply = async (e) => {
    e.preventDefault();
    if (characters.length === 0) {
      toast.error('You need to create a character first!');
      return;
    }

    try {
      await createReply(postId, {
        content: replyContent,
        character_id: selectedCharacterId
      });
      toast.success('Reply posted!');
      setReplyContent('');
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to post reply');
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen relative">
        <AnimatedBackground />
        <Navbar />
        <div className="relative z-10 container mx-auto px-4 py-20 text-center">
          <div className="text-white text-xl">Loading post...</div>
        </div>
      </div>
    );
  }

  if (!post) {
    return (
      <div className="min-h-screen relative">
        <AnimatedBackground />
        <Navbar />
        <div className="relative z-10 container mx-auto px-4 py-20 text-center">
          <div className="text-white text-xl">Post not found</div>
          <Link to="/forums">
            <Button className="mt-4">Back to Forums</Button>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen relative">
      <AnimatedBackground />
      <Navbar />
      
      <div className="relative z-10 container mx-auto px-4 py-8 max-w-4xl">
        <Link to="/forums">
          <Button variant="ghost" className="mb-4 text-purple-400 hover:text-purple-300" data-testid="back-to-forums">
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Forums
          </Button>
        </Link>

        {/* Main Post */}
        <div className="glass-dark p-8 rounded-xl mb-6" data-testid="forum-post">
          <div className="flex items-start justify-between mb-4">
            <div>
              <h1 className="text-3xl font-bold text-white mb-3">{post.title}</h1>
              <div className="flex items-center gap-3 text-sm text-gray-400 flex-wrap">
                <div className="flex items-center gap-1">
                  <User className="w-4 h-4" />
                  <span className="text-purple-300">{post.character_name}</span>
                </div>
                {post.character_id && factionsByChar[post.character_id] && (
                  <FactionBadge faction={factionsByChar[post.character_id]} size="sm" />
                )}
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

          <p className="text-gray-300 leading-relaxed whitespace-pre-wrap">{post.content}</p>

          <div className="mt-4 pt-4 border-t border-purple-500/30 flex items-center gap-2 text-sm text-gray-400">
            <MessageCircle className="w-4 h-4" />
            <span>{post.replies_count} replies</span>
          </div>
        </div>

        {/* Reply Form */}
        <div className="glass-dark p-6 rounded-xl mb-6">
          <h2 className="text-xl font-bold text-purple-300 mb-4">Post a Reply</h2>
          <form onSubmit={handleReply} className="space-y-4" data-testid="reply-form">
            {characters.length > 0 && (
              <div>
                <Label className="text-gray-300">Reply as Character</Label>
                <Select value={selectedCharacterId} onValueChange={setSelectedCharacterId}>
                  <SelectTrigger className="bg-black/20 border-purple-500/30" data-testid="reply-character-select">
                    <SelectValue />
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
            )}

            <div>
              <Textarea
                value={replyContent}
                onChange={(e) => setReplyContent(e.target.value)}
                required
                className="bg-black/20 border-purple-500/30 min-h-[100px] text-white"
                placeholder="Write your reply..."
                data-testid="reply-content-input"
              />
            </div>

            <Button 
              type="submit" 
              className="bg-gradient-to-r from-purple-600 to-pink-600"
              disabled={characters.length === 0}
              data-testid="reply-submit-btn"
            >
              {characters.length === 0 ? 'Create a character first' : 'Post Reply'}
            </Button>
          </form>
        </div>

        {/* Replies */}
        <div className="space-y-4">
          <h2 className="text-xl font-bold text-purple-300">Replies ({replies.length})</h2>
          {replies.length === 0 ? (
            <div className="glass p-8 rounded-xl text-center text-gray-400">
              No replies yet. Be the first to respond!
            </div>
          ) : (
            replies.map((reply) => (
              <div key={reply.id} className="glass p-6 rounded-xl" data-testid={`reply-${reply.id}`}>
                <div className="flex items-center gap-3 text-sm text-gray-400 mb-3 flex-wrap">
                  <div className="flex items-center gap-1">
                    <User className="w-4 h-4" />
                    <span className="text-purple-300">{reply.character_name}</span>
                  </div>
                  {reply.character_id && factionsByChar[reply.character_id] && (
                    <FactionBadge faction={factionsByChar[reply.character_id]} size="sm" />
                  )}
                  <span>•</span>
                  <span>{reply.username}</span>
                  <span>•</span>
                  <span>{new Date(reply.created_at).toLocaleDateString()}</span>
                </div>
                <p className="text-gray-300 whitespace-pre-wrap">{reply.content}</p>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};

export default ForumPost;