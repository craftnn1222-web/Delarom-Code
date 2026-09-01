import React, { useEffect, useState, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { getMyCharacters, createCharacter, updateCharacter, deleteCharacter, generateCharacterPortrait, uploadCharacterImage, startStarterQuest } from '../utils/api';
import { toast } from 'sonner';
import AnimatedBackground from '../components/AnimatedBackground';
import Navbar from '../components/Navbar';
import ExpandableText from '../components/ExpandableText';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Plus, Trash2, Scroll, Sparkles, Shield, Upload, Edit, Heart, Scale, Hammer } from 'lucide-react';
import CompanionManager from '../components/CompanionManager';
import FactionBadge from '../components/factions/FactionBadge';
import useFactionBadges from '../hooks/useFactionBadges';
import RapSheet from '../components/RapSheet';
import FamilyTreePanel from '../components/FamilyTreePanel';
import MysteryIdentityPanel from '../components/MysteryIdentityPanel';
import CharacterReputationPanel from '../components/CharacterReputationPanel';
import ApprenticeshipsPanel from '../components/ApprenticeshipsPanel';

const Characters = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const fileInputRefs = useRef({});
  const [characters, setCharacters] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [isEditMode, setIsEditMode] = useState(false);
  const [editingCharacterId, setEditingCharacterId] = useState(null);
  const [generatingPortrait, setGeneratingPortrait] = useState({});
  const [uploadingImage, setUploadingImage] = useState({});
  const [lightboxUrl, setLightboxUrl] = useState(null);

  // Faction badges keyed by character id, batched.
  const factionsByChar = useFactionBadges(characters.map((c) => c.id));
  const [companionModalChar, setCompanionModalChar] = useState(null);
  const [rapSheetChar, setRapSheetChar] = useState(null);
  const [familyChar, setFamilyChar] = useState(null);
  const [renownChar, setRenownChar] = useState(null);
  const [mysteryChar, setMysteryChar] = useState(null);
  const [apprenticeChar, setApprenticeChar] = useState(null);
  const [formData, setFormData] = useState({
    name: '',
    race: '',
    character_class: '',
    backstory: '',
    powers: '',
    appearance: '',
    nation: 'Ammeonon',
  });

  useEffect(() => {
    fetchCharacters();
  }, []);

  // First-quest handoff: arriving via ?starter=1 opens the create form
  // straight away so a brand-new player can forge their hero without a click.
  useEffect(() => {
    if (searchParams.get('starter')) {
      setIsEditMode(false);
      setIsDialogOpen(true);
    }
  }, []);

  const fetchCharacters = async () => {
    try {
      const response = await getMyCharacters();
      setCharacters(response.data);
    } catch (_error) {
      toast.error('Failed to load characters');
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (isEditMode && editingCharacterId) {
        await updateCharacter(editingCharacterId, formData);
        toast.success(`${formData.name} has been updated!`);
      } else {
        await createCharacter(formData);
        toast.success(`${formData.name} has been created!`);
        // First-quest handoff: a brand-new player who arrived via the welcome
        // onboarding (?starter=1) is dropped straight into their starter scene.
        if (characters.length === 0 && searchParams.get('starter')) {
          const tid = toast.loading('The Quest Master is preparing your first scene...');
          try {
            const res = await startStarterQuest();
            toast.dismiss(tid);
            if (res.data?.quest_id) {
              navigate(`/quests/${res.data.quest_id}/play`);
              return;
            }
          } catch (_e) {
            toast.dismiss(tid);
            toast.error('Could not start your first quest — you can begin from the Quest Board.');
          }
        }
      }
      setIsDialogOpen(false);
      setIsEditMode(false);
      setEditingCharacterId(null);
      setFormData({
        name: '',
        race: '',
        character_class: '',
        backstory: '',
        powers: '',
        appearance: '',
        nation: 'Ammeonon',
      });
      fetchCharacters();
    } catch (error) {
      toast.error(error.response?.data?.detail || `Failed to ${isEditMode ? 'update' : 'create'} character`);
    }
  };

  const handleEdit = (character) => {
    setFormData({
      name: character.name,
      race: character.race,
      character_class: character.character_class,
      backstory: character.backstory,
      powers: character.powers,
      appearance: character.appearance,
      nation: character.nation,
    });
    setEditingCharacterId(character.id);
    setIsEditMode(true);
    setIsDialogOpen(true);
  };

  const handleCloseDialog = (open) => {
    if (!open) {
      setIsDialogOpen(false);
      setIsEditMode(false);
      setEditingCharacterId(null);
      setFormData({
        name: '',
        race: '',
        character_class: '',
        backstory: '',
        powers: '',
        appearance: '',
        nation: 'Ammeonon',
      });
    } else {
      setIsDialogOpen(true);
    }
  };

  const handleDelete = async (id, name) => {
    if (window.confirm(`Are you sure you want to delete ${name}?`)) {
      try {
        await deleteCharacter(id);
        toast.success(`${name} has been removed`);
        fetchCharacters();
      } catch (_error) {
        toast.error('Failed to delete character');
      }
    }
  };

  const handleGeneratePortrait = async (characterId, characterName) => {
    console.log('[Characters] Generate portrait for:', characterId, characterName);
    
    if (generatingPortrait[characterId]) {
      console.log('[Characters] Already generating portrait for:', characterId);
      return;
    }
    
    setGeneratingPortrait(prev => ({ ...prev, [characterId]: true }));
    toast.info(`✨ Generating AI portrait for ${characterName}...`, { duration: 3000 });
    
    try {
      console.log('[Characters] Calling generateCharacterPortrait API');
      const response = await generateCharacterPortrait(characterId);
      console.log('[Characters] Portrait generated successfully:', response.data);
      
      toast.success(`✓ Portrait generated for ${characterName}!`, { duration: 4000 });
      
      // Refresh character list to show the new portrait
      await fetchCharacters();
    } catch (error) {
      console.error('[Characters] Portrait generation error:', error);
      const errorMsg = error.response?.data?.detail || 'Failed to generate portrait';
      toast.error(`✗ ${errorMsg}`, { duration: 4000 });
    } finally {
      setGeneratingPortrait(prev => {
        const newState = { ...prev };
        delete newState[characterId];
        return newState;
      });
    }
  };

  const handleImageUpload = async (characterId, characterName, file) => {
    if (!file) return;
    
    console.log('[Characters] Upload image for:', characterId, characterName);
    
    // Check file type
    if (!file.type.startsWith('image/')) {
      toast.error('Please upload an image file');
      return;
    }
    
    // Check file size (5MB max)
    if (file.size > 5 * 1024 * 1024) {
      toast.error('Image too large! Maximum size is 5MB');
      return;
    }
    
    setUploadingImage(prev => ({ ...prev, [characterId]: true }));
    toast.info(`Uploading image for ${characterName}...`, { duration: 2000 });
    
    try {
      const formData = new FormData();
      formData.append('file', file);
      
      console.log('[Characters] Calling uploadCharacterImage API');
      const response = await uploadCharacterImage(characterId, formData);
      console.log('[Characters] Image uploaded successfully:', response.data);
      
      toast.success(`✓ Image uploaded for ${characterName}!`, { duration: 4000 });
      
      // Refresh character list to show the new image
      await fetchCharacters();
    } catch (error) {
      console.error('[Characters] Image upload error:', error);
      const errorMsg = error.response?.data?.detail || 'Failed to upload image';
      toast.error(`✗ ${errorMsg}`, { duration: 4000 });
    } finally {
      setUploadingImage(prev => {
        const newState = { ...prev };
        delete newState[characterId];
        return newState;
      });
    }
  };

  const triggerFileInput = (characterId) => {
    fileInputRefs.current[characterId]?.click();
  };


  if (loading) {
    return (
      <div className="min-h-screen relative">
        <AnimatedBackground />
        <Navbar />
        <div className="relative z-10 container mx-auto px-4 py-20 text-center">
          <div className="text-white text-xl">Loading characters...</div>
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
          <h1 className="text-4xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-pink-600" data-testid="characters-title">
            Your Characters
          </h1>
          <Dialog open={isDialogOpen} onOpenChange={handleCloseDialog}>
            <DialogTrigger asChild>
              <Button className="bg-gradient-to-r from-purple-600 to-pink-600" data-testid="create-character-btn">
                <Plus className="w-4 h-4 mr-2" />
                Create Character
              </Button>
            </DialogTrigger>
            <DialogContent
              className="bg-gray-900 border-purple-500/30 text-white max-w-2xl max-h-[90vh] overflow-y-auto"
              onPointerDownOutside={(e) => e.preventDefault()}
              onInteractOutside={(e) => e.preventDefault()}
            >
              <DialogHeader>
                <DialogTitle className="text-2xl text-purple-300">
                  {isEditMode ? 'Edit Character' : 'Create New Character'}
                </DialogTitle>
              </DialogHeader>
              <form onSubmit={handleSubmit} className="space-y-4" data-testid="character-form">
                <div>
                  <Label htmlFor="name">Character Name *</Label>
                  <Input
                    id="name"
                    name="name"
                    value={formData.name}
                    onChange={handleChange}
                    required
                    className="bg-black/20 border-purple-500/30"
                    placeholder="e.g., Astral King, Shadow Walker"
                    data-testid="character-name-input"
                  />
                </div>

                <div>
                  <Label htmlFor="race">Race/Species * (Freeform - Be creative!)</Label>
                  <Input
                    id="race"
                    name="race"
                    value={formData.race}
                    onChange={handleChange}
                    required
                    className="bg-black/20 border-purple-500/30"
                    placeholder="e.g., Astral Being, Dragon-born, Celestial Elf"
                    data-testid="character-race-input"
                  />
                </div>

                <div>
                  <Label htmlFor="character_class">Class/Role *</Label>
                  <Input
                    id="character_class"
                    name="character_class"
                    value={formData.character_class}
                    onChange={handleChange}
                    required
                    className="bg-black/20 border-purple-500/30"
                    placeholder="e.g., Warrior, Mage, King, Assassin"
                    data-testid="character-class-input"
                  />
                </div>

                <div>
                  <Label htmlFor="nation">Nation *</Label>
                  <Select name="nation" value={formData.nation} onValueChange={(value) => setFormData({...formData, nation: value})}>
                    <SelectTrigger className="bg-black/20 border-purple-500/30" data-testid="character-nation-select">
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
                  <Label htmlFor="backstory">Backstory *</Label>
                  <Textarea
                    id="backstory"
                    name="backstory"
                    value={formData.backstory}
                    onChange={handleChange}
                    required
                    className="bg-black/20 border-purple-500/30 min-h-[100px]"
                    placeholder="Tell your character's story..."
                    data-testid="character-backstory-input"
                  />
                </div>

                <div>
                  <Label htmlFor="powers">Powers & Abilities *</Label>
                  <Textarea
                    id="powers"
                    name="powers"
                    value={formData.powers}
                    onChange={handleChange}
                    required
                    className="bg-black/20 border-purple-500/30"
                    placeholder="Describe their powers and abilities..."
                    data-testid="character-powers-input"
                  />
                </div>

                <div>
                  <Label htmlFor="appearance">Appearance *</Label>
                  <Textarea
                    id="appearance"
                    name="appearance"
                    value={formData.appearance}
                    onChange={handleChange}
                    required
                    className="bg-black/20 border-purple-500/30"
                    placeholder="Describe their appearance..."
                    data-testid="character-appearance-input"
                  />
                </div>

                <Button type="submit" className="w-full bg-gradient-to-r from-purple-600 to-pink-600" data-testid="character-submit-btn">
                  {isEditMode ? 'Update Character' : 'Create Character'}
                </Button>
              </form>
            </DialogContent>
          </Dialog>
        </div>

        {characters.length === 0 ? (
          <div className="glass-dark p-12 rounded-2xl text-center">
            <Scroll className="w-16 h-16 mx-auto mb-4 text-purple-400" />
            <h2 className="text-2xl font-bold mb-2 text-white">No Characters Yet</h2>
            <p className="text-gray-400 mb-6">Create your first character to begin your adventure in Delarom!</p>
            <Button onClick={() => setIsDialogOpen(true)} className="bg-gradient-to-r from-purple-600 to-pink-600">
              Create Your First Character
            </Button>
          </div>
        ) : (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {characters.map((char) => (
              <div key={char.id} className="glass-dark p-6 rounded-xl relative" data-testid={`character-card-${char.id}`}>
                {/* AI Portrait Display */}
                {char.portrait_url && (
                  <button
                    type="button"
                    onClick={() => setLightboxUrl(char.portrait_url)}
                    className="mb-4 w-full rounded-lg overflow-hidden border-2 border-purple-500/30 bg-black/40 aspect-square flex items-center justify-center hover:border-purple-400/60 transition group"
                    title="Click to view full portrait"
                    data-testid={`portrait-thumb-${char.id}`}
                  >
                    <img
                      src={char.portrait_url}
                      alt={`${char.name} portrait`}
                      className="w-full h-full object-contain group-hover:scale-[1.02] transition-transform"
                    />
                  </button>
                )}
                
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <h2 className="text-2xl font-bold text-purple-300 mb-1">{char.name}</h2>
                    <p className="text-gray-400 text-sm">{char.race}</p>
                    <p className="text-gray-500 text-sm">{char.character_class}</p>
                    {factionsByChar[char.id] && (
                      <div className="mt-2">
                        <FactionBadge faction={factionsByChar[char.id]} size="sm" showRank />
                      </div>
                    )}
                  </div>
                  <div className="flex gap-2">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleEdit(char)}
                      className="text-blue-400 hover:text-blue-300 hover:bg-blue-500/20"
                      data-testid={`edit-character-${char.id}`}
                    >
                      <Edit className="w-4 h-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleDelete(char.id, char.name)}
                      className="text-red-400 hover:text-red-300 hover:bg-red-500/20"
                      data-testid={`delete-character-${char.id}`}
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                </div>

                <div className="space-y-3">
                  <div>
                    <p className="text-xs text-purple-400 font-semibold mb-1">NATION</p>
                    <p className="text-white text-sm">{char.nation}</p>
                  </div>

                  <ExpandableText 
                    text={char.backstory} 
                    label="BACKSTORY" 
                    maxLines={3}
                  />

                  <ExpandableText 
                    text={char.powers} 
                    label="POWERS" 
                    maxLines={2}
                  />

                  <ExpandableText 
                    text={char.appearance} 
                    label="APPEARANCE" 
                    maxLines={2}
                  />

                  <div className="pt-3 border-t border-purple-500/30 space-y-2">
                    <div className="flex items-center justify-between">
                      <p className="text-sm font-bold text-yellow-400">Level {char.level}</p>
                      <p className="text-xs text-gray-400">{char.xp || 0} / {char.xp_to_next_level || 100} XP</p>
                    </div>
                    <div className="w-full bg-gray-700 rounded-full h-2">
                      <div 
                        className="bg-gradient-to-r from-yellow-500 to-orange-500 h-2 rounded-full transition-all duration-500"
                        style={{ width: `${((char.xp || 0) / (char.xp_to_next_level || 100)) * 100}%` }}
                      />
                    </div>
                    
                    <div className="grid grid-cols-3 gap-2 mt-3">
                      <div className="bg-red-600/20 p-2 rounded text-center">
                        <p className="text-xs text-red-300">STR</p>
                        <p className="text-sm font-bold text-white">{char.strength || 10}</p>
                      </div>
                      <div className="bg-blue-600/20 p-2 rounded text-center">
                        <p className="text-xs text-blue-300">MAG</p>
                        <p className="text-sm font-bold text-white">{char.magic || 10}</p>
                      </div>
                      <div className="bg-green-600/20 p-2 rounded text-center">
                        <p className="text-xs text-green-300">AGI</p>
                        <p className="text-sm font-bold text-white">{char.agility || 10}</p>
                      </div>
                      <div className="bg-yellow-600/20 p-2 rounded text-center">
                        <p className="text-xs text-yellow-300">END</p>
                        <p className="text-sm font-bold text-white">{char.endurance || 10}</p>
                      </div>
                      <div className="bg-purple-600/20 p-2 rounded text-center">
                        <p className="text-xs text-purple-300">CHA</p>
                        <p className="text-sm font-bold text-white">{char.charisma || 10}</p>
                      </div>
                      <div className="bg-pink-600/20 p-2 rounded text-center">
                        <p className="text-xs text-pink-300">LCK</p>
                        <p className="text-sm font-bold text-white">{char.luck || 10}</p>
                      </div>
                    </div>
                  </div>
                  
                  {/* Action Buttons */}
                  <div className="mt-4 space-y-2">
                    <Button
                      onClick={() => navigate(`/characters/${char.id}/equipment`)}
                      className="w-full bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-700 hover:to-cyan-700"
                      data-testid={`equipment-${char.id}`}
                    >
                      <Shield className="w-4 h-4 mr-2" />
                      Equipment & Inventory
                    </Button>

                    <Button
                      onClick={() => setCompanionModalChar(char)}
                      className="w-full bg-gradient-to-r from-pink-600 to-purple-600 hover:from-pink-700 hover:to-purple-700"
                      data-testid={`manage-companions-${char.id}`}
                    >
                      <Heart className="w-4 h-4 mr-2" fill="currentColor" />
                      Manage Companions
                    </Button>

                    <Button
                      onClick={() => setRapSheetChar(char)}
                      className="w-full bg-gradient-to-r from-amber-600 to-rose-600 hover:from-amber-700 hover:to-rose-700"
                      data-testid={`rap-sheet-${char.id}`}
                    >
                      <Scale className="w-4 h-4 mr-2" />
                      Rap Sheet
                    </Button>

                    <Button
                      onClick={() => setRenownChar(char)}
                      className="w-full bg-gradient-to-r from-purple-600 to-fuchsia-600 hover:from-purple-700 hover:to-fuchsia-700"
                      data-testid={`renown-btn-${char.id}`}
                    >
                      <Shield className="w-4 h-4 mr-2" />
                      Renown &amp; Reputation
                    </Button>

                    <Button
                      onClick={() => setFamilyChar(char)}
                      className="w-full bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700"
                      data-testid={`family-tree-${char.id}`}
                    >
                      <Heart className="w-4 h-4 mr-2" />
                      Family & Bloodline
                    </Button>

                    <Button
                      onClick={() => setMysteryChar(char)}
                      className="w-full bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-700 hover:to-violet-700"
                      data-testid={`mystery-identity-${char.id}`}
                    >
                      <Sparkles className="w-4 h-4 mr-2" />
                      Dreams · Prophecy · Persona
                    </Button>

                    <Button
                      onClick={() => setApprenticeChar(char)}
                      className="w-full bg-gradient-to-r from-amber-700 to-orange-700 hover:from-amber-800 hover:to-orange-800"
                      data-testid={`apprentice-${char.id}`}
                    >
                      <Hammer className="w-4 h-4 mr-2" />
                      Apprenticeships
                    </Button>
                    
                    <div className="grid grid-cols-2 gap-2">
                      <Button
                        onClick={() => triggerFileInput(char.id)}
                        disabled={uploadingImage[char.id]}
                        className="bg-gradient-to-r from-green-600 to-teal-600 hover:from-green-700 hover:to-teal-700"
                        data-testid={`upload-image-${char.id}`}
                      >
                        <Upload className="w-4 h-4 mr-2" />
                        {uploadingImage[char.id] ? 'Uploading...' : 'Upload Image'}
                      </Button>
                      <Button
                        onClick={() => handleGeneratePortrait(char.id, char.name)}
                        disabled={generatingPortrait[char.id]}
                        className="bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700"
                        data-testid={`generate-portrait-${char.id}`}
                      >
                        <Sparkles className="w-4 h-4 mr-2" />
                        {generatingPortrait[char.id] ? 'Generating...' : 'AI Portrait'}
                      </Button>
                    </div>
                    
                    {/* Hidden file input */}
                    <input
                      ref={el => fileInputRefs.current[char.id] = el}
                      type="file"
                      accept="image/*"
                      style={{ display: 'none' }}
                      onChange={(e) => {
                        const file = e.target.files[0];
                        if (file) {
                          handleImageUpload(char.id, char.name, file);
                        }
                        e.target.value = ''; // Reset input
                      }}
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <CompanionManager
        open={!!companionModalChar}
        onOpenChange={(o) => !o && setCompanionModalChar(null)}
        character={companionModalChar}
      />

      <RapSheet
        open={!!rapSheetChar}
        onOpenChange={(o) => !o && setRapSheetChar(null)}
        character={rapSheetChar}
      />

      {/* Renown & Reputation modal (Iteration A — the Reputation Web) */}
      <Dialog open={!!renownChar} onOpenChange={(o) => !o && setRenownChar(null)}>
        <DialogContent className="bg-gray-900 border-purple-500/30 text-white max-w-3xl max-h-[85vh] overflow-y-auto" data-testid="renown-modal">
          <DialogHeader>
            <DialogTitle className="text-2xl text-purple-200">
              {renownChar?.name}&apos;s Renown
            </DialogTitle>
          </DialogHeader>
          {renownChar && <CharacterReputationPanel characterId={renownChar.id} />}
        </DialogContent>
      </Dialog>

      {/* Family & Bloodline modal (Phase 3) */}
      <Dialog open={!!familyChar} onOpenChange={(o) => !o && setFamilyChar(null)}>
        <DialogContent className="bg-gray-900 border-emerald-500/30 text-white max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-2xl text-emerald-300">
              {familyChar?.name}&apos;s Kin
            </DialogTitle>
          </DialogHeader>
          {familyChar && <FamilyTreePanel characterId={familyChar.id} canEdit />}
        </DialogContent>
      </Dialog>

      {/* Mystery & Identity modal (Phase 4) — Dreams · Prophecy · Persona */}
      <Dialog open={!!mysteryChar} onOpenChange={(o) => !o && setMysteryChar(null)}>
        <DialogContent className="bg-gray-900 border-violet-500/30 text-white max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-2xl text-violet-300">
              {mysteryChar?.name} — Inner World
            </DialogTitle>
          </DialogHeader>
          {mysteryChar && <MysteryIdentityPanel character={mysteryChar} />}
        </DialogContent>
      </Dialog>

      {/* Apprenticeships modal (Phase 5) */}
      <Dialog open={!!apprenticeChar} onOpenChange={(o) => !o && setApprenticeChar(null)}>
        <DialogContent
          className="bg-gray-900 border-amber-500/30 text-white max-w-2xl max-h-[90vh] overflow-y-auto"
          // Keep this dialog from closing when the user opens an inner Radix
          // primitive (the craft Select dropdown, the mentor search list, etc).
          // Those primitives portal their content to <body> so Radix would
          // otherwise treat their pointer events as "outside" and shut the
          // whole apprenticeships panel. Closing via the X button still works.
          onPointerDownOutside={(e) => e.preventDefault()}
          onInteractOutside={(e) => e.preventDefault()}
        >
          <DialogHeader>
            <DialogTitle className="text-2xl text-amber-300">
              {apprenticeChar?.name} — Apprenticeships
            </DialogTitle>
          </DialogHeader>
          {apprenticeChar && <ApprenticeshipsPanel character={apprenticeChar} />}
        </DialogContent>
      </Dialog>

      {/* Portrait lightbox — full-size viewer */}
      {lightboxUrl && (
        <div
          className="fixed inset-0 z-[100] bg-black/90 flex items-center justify-center p-4 cursor-zoom-out"
          onClick={() => setLightboxUrl(null)}
          data-testid="portrait-lightbox"
        >
          <img
            src={lightboxUrl}
            alt="Character portrait — full size"
            className="max-h-[92vh] max-w-[92vw] object-contain rounded-lg shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          />
          <button
            type="button"
            onClick={() => setLightboxUrl(null)}
            className="absolute top-4 right-4 text-white/80 hover:text-white text-2xl bg-black/60 hover:bg-black/80 rounded-full w-10 h-10 flex items-center justify-center"
            aria-label="Close portrait viewer"
          >
            ×
          </button>
        </div>
      )}
    </div>
  );
};

export default Characters;