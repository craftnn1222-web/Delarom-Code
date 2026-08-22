import React, { useEffect, useState } from 'react';
import AnimatedBackground from '../components/AnimatedBackground';
import Navbar from '../components/Navbar';
import { getMemberDirectory } from '../utils/api';
import { Badge } from '../components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { ScrollText, Users, Sparkles, Eye, MapPin } from 'lucide-react';

const roleColors = {
  admin: 'bg-gradient-to-r from-yellow-500 to-orange-500 text-black',
  moderator: 'bg-gradient-to-r from-blue-500 to-cyan-500 text-black',
  member: 'bg-purple-600/30 text-purple-200 border border-purple-500/40',
};

const MemberDirectory = () => {
  const [members, setMembers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selectedMember, setSelectedMember] = useState(null);
  const [selectedCharacter, setSelectedCharacter] = useState(null);

  useEffect(() => {
    const fetchMembers = async () => {
      try {
        const response = await getMemberDirectory();
        setMembers(response.data);
      } catch (err) {
        console.error('Failed to load member directory', err);
        setError('Failed to load member directory. Please try again later.');
      } finally {
        setLoading(false);
      }
    };

    fetchMembers();
  }, []);

  return (
    <div className="min-h-screen relative">
      <AnimatedBackground />
      <Navbar />

      <div className="relative z-10 container mx-auto px-4 py-8 max-w-6xl">
        <header className="mb-10 text-center">
          <h1 className="text-4xl sm:text-5xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-pink-600 mb-3">
            Member Directory
          </h1>
          <p className="text-gray-300 max-w-2xl mx-auto text-sm sm:text-base">
            Browse the approved citizens, adventurers, and rulers of Tyrandria. Each entry shows the
            characters they bring to life in the world of Delarom.
          </p>
        </header>

        {loading ? (
          <div className="glass-dark p-8 rounded-2xl text-center">
            <Users className="w-10 h-10 mx-auto mb-3 text-purple-400" />
            <p className="text-gray-300">Loading members...</p>
          </div>
        ) : error ? (
          <div className="glass-dark p-8 rounded-2xl text-center border border-red-500/40">
            <p className="text-red-300 text-sm sm:text-base">{error}</p>
          </div>
        ) : members.length === 0 ? (
          <div className="glass-dark p-8 rounded-2xl text-center">
            <Users className="w-10 h-10 mx-auto mb-3 text-purple-400" />
            <p className="text-gray-300">No approved members found yet.</p>
          </div>
        ) : (
          <div className="grid md:grid-cols-2 gap-6">
            {members.map((member) => (
              <Card 
                key={member.id} 
                className="glass-dark border border-purple-500/30 cursor-pointer hover:border-purple-400/50 transition-all hover:scale-[1.02]"
                onClick={() => setSelectedMember(member)}
                data-testid={`member-card-${member.id}`}
              >
                <CardHeader className="flex flex-row items-center justify-between gap-3 pb-3">
                  <div>
                    <CardTitle className="text-xl text-white mb-1 flex items-center gap-2">
                      <ScrollText className="w-5 h-5 text-purple-400" />
                      <span>{member.username}</span>
                    </CardTitle>
                    <p className="text-xs text-gray-400">Roleplay member of Tyrandria</p>
                  </div>
                  <Badge
                    className={
                      roleColors[member.role] || 'bg-purple-600/30 text-purple-200 border border-purple-500/40'
                    }
                  >
                    {member.role === 'admin'
                      ? 'Admin'
                      : member.role === 'moderator'
                      ? 'Moderator'
                      : 'Member'}
                  </Badge>
                </CardHeader>
                <CardContent className="space-y-4 pt-0">
                  {member.characters && member.characters.length > 0 ? (
                    <div className="space-y-3">
                      {member.characters.slice(0, 2).map((char) => (
                        <div
                          key={char.id}
                          className="glass p-3 rounded-lg flex gap-3 items-start border border-purple-500/20"
                        >
                          {char.portrait_url && (
                            <div className="w-16 h-16 rounded-md overflow-hidden flex-shrink-0 border border-purple-500/40">
                              <img
                                src={char.portrait_url}
                                alt={`${char.name} portrait`}
                                className="w-full h-full object-cover"
                              />
                            </div>
                          )}
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center justify-between gap-2 mb-1">
                              <h3 className="text-sm font-semibold text-purple-200 truncate">
                                {char.name}
                              </h3>
                              <span className="text-[10px] px-2 py-0.5 rounded-full bg-purple-700/40 text-purple-100">
                                {char.nation}
                              </span>
                            </div>
                            <p className="text-[11px] text-gray-300 mb-1">
                              <span className="font-semibold">{char.race}</span> · {char.character_class}
                            </p>
                            <p className="text-[11px] text-gray-400 line-clamp-2">
                              {char.backstory || char.appearance || 'No description provided yet.'}
                            </p>
                          </div>
                        </div>
                      ))}
                      {member.characters.length > 2 && (
                        <p className="text-xs text-purple-400 text-center">
                          +{member.characters.length - 2} more character{member.characters.length - 2 > 1 ? 's' : ''}
                        </p>
                      )}
                    </div>
                  ) : (
                    <p className="text-xs text-gray-400">This member has not created any characters yet.</p>
                  )}
                  <p className="text-xs text-purple-400 text-center pt-2">Click to view full profile</p>
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {/* Member Profile Modal */}
        <Dialog open={!!selectedMember} onOpenChange={(open) => !open && setSelectedMember(null)}>
          <DialogContent className="bg-gray-900 border-purple-500/30 text-white max-w-3xl max-h-[90vh] overflow-y-auto">
            {selectedMember && (
              <>
                <DialogHeader>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <ScrollText className="w-8 h-8 text-purple-400" />
                      <div>
                        <DialogTitle className="text-2xl text-purple-300">
                          {selectedMember.username}
                        </DialogTitle>
                        <p className="text-sm text-gray-400">Member of Tyrandria</p>
                      </div>
                    </div>
                    <Badge
                      className={
                        roleColors[selectedMember.role] || 'bg-purple-600/30 text-purple-200 border border-purple-500/40'
                      }
                    >
                      {selectedMember.role === 'admin'
                        ? 'Admin'
                        : selectedMember.role === 'moderator'
                        ? 'Moderator'
                        : 'Member'}
                    </Badge>
                  </div>
                </DialogHeader>

                <div className="mt-6">
                  <h3 className="text-lg font-semibold text-purple-300 mb-4 flex items-center gap-2">
                    <Users className="w-5 h-5" />
                    Characters ({selectedMember.characters?.length || 0})
                  </h3>
                  
                  {selectedMember.characters && selectedMember.characters.length > 0 ? (
                    <div className="space-y-4">
                      {selectedMember.characters.map((char) => (
                        <div
                          key={char.id}
                          className={`glass p-4 rounded-xl border transition-all cursor-pointer ${
                            selectedCharacter?.id === char.id 
                              ? 'border-purple-400 bg-purple-500/10' 
                              : 'border-purple-500/20 hover:border-purple-500/40'
                          }`}
                          onClick={() => setSelectedCharacter(selectedCharacter?.id === char.id ? null : char)}
                          data-testid={`modal-character-${char.id}`}
                        >
                          <div className="flex gap-4">
                            {char.portrait_url && (
                              <div className="w-24 h-24 rounded-lg overflow-hidden flex-shrink-0 border-2 border-purple-500/40">
                                <img
                                  src={char.portrait_url}
                                  alt={`${char.name} portrait`}
                                  className="w-full h-full object-cover"
                                />
                              </div>
                            )}
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center justify-between gap-2 mb-2">
                                <h4 className="text-lg font-bold text-white">{char.name}</h4>
                                <span className="text-xs px-3 py-1 rounded-full bg-purple-700/40 text-purple-100 flex items-center gap-1">
                                  <MapPin className="w-3 h-3" />
                                  {char.nation}
                                </span>
                              </div>
                              <p className="text-sm text-gray-300 mb-2">
                                <span className="font-semibold text-purple-200">{char.race}</span> · {char.character_class}
                              </p>
                              <p className="text-xs text-purple-400">
                                {selectedCharacter?.id === char.id ? 'Click to collapse' : 'Click to view full bio'}
                              </p>
                            </div>
                          </div>

                          {/* Expanded Character Details */}
                          {selectedCharacter?.id === char.id && (
                            <div className="mt-4 pt-4 border-t border-purple-500/30 space-y-4">
                              {char.backstory && (
                                <div>
                                  <p className="text-xs text-purple-400 font-semibold mb-2 flex items-center gap-1">
                                    <ScrollText className="w-3 h-3" /> BACKSTORY
                                  </p>
                                  <p className="text-sm text-gray-300 whitespace-pre-wrap">{char.backstory}</p>
                                </div>
                              )}
                              
                              {char.powers && (
                                <div>
                                  <p className="text-xs text-purple-400 font-semibold mb-2 flex items-center gap-1">
                                    <Sparkles className="w-3 h-3" /> POWERS & ABILITIES
                                  </p>
                                  <p className="text-sm text-gray-300 whitespace-pre-wrap">{char.powers}</p>
                                </div>
                              )}
                              
                              {char.appearance && (
                                <div>
                                  <p className="text-xs text-purple-400 font-semibold mb-2 flex items-center gap-1">
                                    <Eye className="w-3 h-3" /> APPEARANCE
                                  </p>
                                  <p className="text-sm text-gray-300 whitespace-pre-wrap">{char.appearance}</p>
                                </div>
                              )}

                              <div className="flex items-center gap-4 pt-2">
                                <span className="text-sm font-bold text-yellow-400">Level {char.level || 1}</span>
                                <span className="text-xs text-gray-400">{char.xp || 0} XP</span>
                              </div>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-gray-400 text-center py-8">
                      This member has not created any characters yet.
                    </p>
                  )}
                </div>
              </>
            )}
          </DialogContent>
        </Dialog>
      </div>
    </div>
  );
};

export default MemberDirectory;
