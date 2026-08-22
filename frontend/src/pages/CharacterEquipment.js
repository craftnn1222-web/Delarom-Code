import React, { useEffect, useState, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getCharacter, equipItem, unequipItem, getCharacterStats } from '../utils/api';
import { toast } from 'sonner';
import AnimatedBackground from '../components/AnimatedBackground';
import Navbar from '../components/Navbar';
import { Button } from '../components/ui/button';
import { ArrowLeft, Sword, Shield, Crown, Shirt, Footprints, Hand, Gem, Sparkles } from 'lucide-react';

const SLOT_ICONS = {
  weapon: Sword,
  head: Crown,
  chest: Shirt,
  legs: Shield,
  boots: Footprints,
  gloves: Hand,
  ring: Gem,
  necklace: Sparkles
};

const SLOT_NAMES = {
  weapon: 'Weapon',
  head: 'Helmet',
  chest: 'Chest Armor',
  legs: 'Leg Armor',
  boots: 'Boots',
  gloves: 'Gloves',
  ring: 'Ring',
  necklace: 'Necklace'
};

const CharacterEquipment = () => {
  const { characterId } = useParams();
  const navigate = useNavigate();
  const [character, setCharacter] = useState(null);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [actionInProgress, setActionInProgress] = useState(false);

  const fetchCharacterData = useCallback(async () => {
    try {
      const [charRes, statsRes] = await Promise.all([
        getCharacter(characterId),
        getCharacterStats(characterId)
      ]);
      setCharacter(charRes.data);
      setStats(statsRes.data);
    } catch (_error) {
      toast.error('Failed to load character');
      navigate('/characters');
    } finally {
      setLoading(false);
    }
  }, [characterId, navigate]);

  useEffect(() => {
    fetchCharacterData();
  }, [fetchCharacterData]);

  const handleEquip = async (inventoryItemId, itemName) => {
    if (actionInProgress) return;
    
    setActionInProgress(true);
    try {
      await equipItem(characterId, inventoryItemId);
      toast.success(`${itemName} equipped!`);
      await fetchCharacterData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to equip item');
    } finally {
      setActionInProgress(false);
    }
  };

  const handleUnequip = async (slot, itemName) => {
    if (actionInProgress) return;
    
    setActionInProgress(true);
    try {
      await unequipItem(characterId, slot);
      toast.success(`${itemName} unequipped!`);
      await fetchCharacterData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to unequip item');
    } finally {
      setActionInProgress(false);
    }
  };

  const getStatColor = (stat) => {
    const colors = {
      strength: 'text-red-400',
      magic: 'text-blue-400',
      agility: 'text-green-400',
      endurance: 'text-yellow-400',
      charisma: 'text-purple-400',
      luck: 'text-pink-400'
    };
    return colors[stat] || 'text-gray-400';
  };

  if (loading) {
    return (
      <div className="min-h-screen relative">
        <AnimatedBackground />
        <Navbar />
        <div className="relative z-10 container mx-auto px-4 py-20 text-center">
          <div className="text-white text-xl">Loading equipment...</div>
        </div>
      </div>
    );
  }

  if (!character || !stats) {
    return (
      <div className="min-h-screen relative">
        <AnimatedBackground />
        <Navbar />
        <div className="relative z-10 container mx-auto px-4 py-20 text-center">
          <div className="text-white text-xl">Character not found</div>
        </div>
      </div>
    );
  }

  const equipped = character.equipped || {};
  const inventory = character.inventory || [];

  return (
    <div className="min-h-screen relative">
      <AnimatedBackground />
      <Navbar />
      
      <div className="relative z-10 container mx-auto px-4 py-8">
        {/* Header */}
        <div className="flex items-center gap-4 mb-8">
          <Button
            onClick={() => navigate('/characters')}
            variant="ghost"
            className="text-purple-400 hover:text-purple-300"
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back
          </Button>
          <div>
            <h1 className="text-4xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-pink-600">
              ⚔️ {character.name}'s Equipment
            </h1>
            <p className="text-gray-400">{character.race} {character.character_class} • Level {character.level}</p>
          </div>
        </div>

        <div className="grid lg:grid-cols-3 gap-6">
          {/* Equipment Slots */}
          <div className="lg:col-span-2">
            <div className="glass-dark p-6 rounded-xl">
              <h2 className="text-2xl font-bold text-purple-300 mb-6">Equipment Slots</h2>
              
              <div className="grid md:grid-cols-2 gap-4">
                {Object.keys(SLOT_NAMES).map((slot) => {
                  const Icon = SLOT_ICONS[slot];
                  const item = equipped[slot];
                  
                  return (
                    <div key={slot} className="glass p-4 rounded-lg">
                      <div className="flex items-center gap-2 mb-3">
                        <Icon className="w-5 h-5 text-purple-400" />
                        <span className="font-bold text-purple-300">{SLOT_NAMES[slot]}</span>
                      </div>
                      
                      {item ? (
                        <div className="space-y-2">
                          <p className="text-white font-semibold">{item.name}</p>
                          <p className="text-xs text-gray-400">{item.description}</p>
                          
                          {item.stat_bonuses && Object.keys(item.stat_bonuses).length > 0 && (
                            <div className="flex flex-wrap gap-2 mt-2">
                              {Object.entries(item.stat_bonuses).map(([stat, bonus]) => (
                                <span key={stat} className={`text-xs px-2 py-1 rounded bg-black/30 ${getStatColor(stat)}`}>
                                  +{bonus} {stat.toUpperCase().substring(0, 3)}
                                </span>
                              ))}
                            </div>
                          )}
                          
                          <Button
                            size="sm"
                            onClick={() => handleUnequip(slot, item.name)}
                            disabled={actionInProgress}
                            className="w-full mt-2 bg-red-600/20 hover:bg-red-600/30 text-red-400"
                          >
                            Unequip
                          </Button>
                        </div>
                      ) : (
                        <p className="text-gray-500 text-sm italic">Empty</p>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Inventory */}
            <div className="glass-dark p-6 rounded-xl mt-6">
              <h2 className="text-2xl font-bold text-purple-300 mb-6">Inventory ({inventory.length})</h2>
              
              {inventory.length === 0 ? (
                <div className="text-center py-12 text-gray-400">
                  <p>No items in inventory</p>
                  <p className="text-sm mt-2">Purchase items from the marketplace or complete quests to get gear!</p>
                </div>
              ) : (
                <div className="grid md:grid-cols-2 gap-4">
                  {inventory.map((item) => (
                    <div key={item.id} className="glass p-4 rounded-lg">
                      <div className="flex items-start justify-between mb-2">
                        <div>
                          <p className="font-bold text-white">{item.name}</p>
                          <p className="text-xs text-gray-400">{item.description}</p>
                        </div>
                        {item.equipment_slot && SLOT_ICONS[item.equipment_slot] && (
                          <div className="text-purple-400">
                            {React.createElement(SLOT_ICONS[item.equipment_slot], { className: "w-4 h-4" })}
                          </div>
                        )}
                      </div>
                      
                      {item.stat_bonuses && Object.keys(item.stat_bonuses).length > 0 && (
                        <div className="flex flex-wrap gap-2 mb-3">
                          {Object.entries(item.stat_bonuses).map(([stat, bonus]) => (
                            <span key={stat} className={`text-xs px-2 py-1 rounded bg-black/30 ${getStatColor(stat)}`}>
                              +{bonus} {stat.toUpperCase().substring(0, 3)}
                            </span>
                          ))}
                        </div>
                      )}
                      
                      <p className="text-xs text-gray-500 mb-2">
                        From: {item.acquired_from === 'shop_purchase' ? 'Shop Purchase' : 'Quest Reward'}
                      </p>
                      
                      {item.equipment_slot && (
                        <Button
                          size="sm"
                          onClick={() => handleEquip(item.id, item.name)}
                          disabled={actionInProgress}
                          className="w-full bg-gradient-to-r from-purple-600 to-pink-600"
                        >
                          Equip to {SLOT_NAMES[item.equipment_slot]}
                        </Button>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Stats Panel */}
          <div className="lg:col-span-1">
            <div className="glass-dark p-6 rounded-xl sticky top-4">
              <h2 className="text-2xl font-bold text-purple-300 mb-6">Character Stats</h2>
              
              <div className="space-y-4">
                {Object.entries(stats.total_stats).map(([stat, value]) => {
                  const baseValue = stats.base_stats[stat];
                  const bonus = stats.gear_bonuses[stat];
                  
                  return (
                    <div key={stat} className="space-y-1">
                      <div className="flex items-center justify-between">
                        <span className={`font-bold uppercase text-sm ${getStatColor(stat)}`}>
                          {stat}
                        </span>
                        <div className="flex items-center gap-2">
                          <span className="text-white font-bold">{value}</span>
                          {bonus > 0 && (
                            <span className="text-green-400 text-sm">+{bonus}</span>
                          )}
                        </div>
                      </div>
                      {bonus > 0 && (
                        <div className="text-xs text-gray-400">
                          Base: {baseValue} + Gear: {bonus}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>

              <div className="mt-6 pt-6 border-t border-purple-500/30">
                <div className="text-center">
                  <p className="text-sm text-gray-400 mb-1">Total Gear Bonus</p>
                  <p className="text-3xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-green-400 to-blue-500">
                    +{Object.values(stats.gear_bonuses).reduce((a, b) => a + b, 0)}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CharacterEquipment;
