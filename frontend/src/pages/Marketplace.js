import React, { useEffect, useState, useCallback } from 'react';
import { getShops, getShopItems, purchaseItem, getMyCharacters } from '../utils/api';
import { toast } from 'sonner';
import { Link } from 'react-router-dom';
import AnimatedBackground from '../components/AnimatedBackground';
import Navbar from '../components/Navbar';
import { Button } from '../components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { Store, Coins, Package, User } from 'lucide-react';

const Marketplace = () => {
  const [shops, setShops] = useState([]);
  const [selectedShop, setSelectedShop] = useState(null);
  const [items, setItems] = useState([]);
  const [characters, setCharacters] = useState([]);
  const [selectedNation, setSelectedNation] = useState('all');
  const [loading, setLoading] = useState(true);
  const [purchasingItems, setPurchasingItems] = useState({}); // Track per-item purchasing state
  const [characterSelectDialog, setCharacterSelectDialog] = useState({ open: false, item: null });

  const fetchCharacters = useCallback(async () => {
    try {
      const response = await getMyCharacters();
      setCharacters(response.data);
    } catch (_error) {
      console.error('Failed to load characters');
    }
  }, []);

  const fetchShops = useCallback(async () => {
    try {
      const params = {};
      if (selectedNation !== 'all') params.nation = selectedNation;
      
      const response = await getShops(params);
      setShops(response.data);
      setSelectedShop(prev => prev || response.data[0]?.id || null);
    } catch (_error) {
      toast.error('Failed to load shops');
    } finally {
      setLoading(false);
    }
  }, [selectedNation]);

  useEffect(() => {
    fetchShops();
    fetchCharacters();
  }, [fetchShops, fetchCharacters]);

  useEffect(() => {
    if (selectedShop) {
      fetchItems(selectedShop);
    }
  }, [selectedShop]);

  const fetchItems = async (shopId) => {
    try {
      const response = await getShopItems(shopId);
      setItems(response.data);
    } catch (_error) {
      toast.error('Failed to load items');
    }
  };

  const handlePurchaseClick = (item) => {
    console.log('[Marketplace] Purchase click for item:', item);
    
    if (characters.length === 0) {
      toast.error('You need to create a character first!');
      return;
    }
    
    // Open character selection dialog
    setCharacterSelectDialog({ open: true, item });
  };

  const handlePurchase = async (itemId, itemName, price, characterId) => {
    console.log('[Marketplace] Purchase initiated:', { itemId, itemName, price, characterId });
    
    // Close dialog
    setCharacterSelectDialog({ open: false, item: null });
    
    // Check if this item is already being purchased
    if (purchasingItems[itemId]) {
      console.log('[Marketplace] Purchase already in progress for item:', itemId);
      return;
    }
    
    // Mark this specific item as being purchased
    setPurchasingItems(prev => ({ ...prev, [itemId]: true }));
    console.log('[Marketplace] Set purchasing state for item:', itemId);
    
    toast.info(`Purchasing ${itemName}...`, { duration: 2000 });
    
    try {
      console.log('[Marketplace] Calling purchaseItem API for:', itemId, 'character:', characterId);
      const response = await purchaseItem(itemId, characterId);
      console.log('[Marketplace] Purchase successful:', response.data);
      
      const characterName = characters.find(c => c.id === characterId)?.name || 'Character';
      toast.success(`✓ ${characterName} received ${itemName}! New balance: ${response.data.new_balance} gold`, { duration: 4000 });
      
      // Reset purchasing state before reload
      setPurchasingItems(prev => {
        const newState = { ...prev };
        delete newState[itemId];
        return newState;
      });
      
      // Small delay then reload
      setTimeout(() => {
        console.log('[Marketplace] Reloading page...');
        window.location.reload();
      }, 1500);
    } catch (error) {
      console.error('[Marketplace] Purchase error:', error);
      console.error('[Marketplace] Error response:', error.response?.data);
      
      const errorMsg = error.response?.data?.detail || 'Purchase failed';
      toast.error(`✗ ${errorMsg}`, { duration: 4000 });
      
      // Reset purchasing state on error
      setPurchasingItems(prev => {
        const newState = { ...prev };
        delete newState[itemId];
        return newState;
      });
    }
  };

  const currentShop = shops.find(s => s.id === selectedShop);

  if (loading) {
    return (
      <div className="min-h-screen relative">
        <AnimatedBackground />
        <Navbar />
        <div className="relative z-10 container mx-auto px-4 py-20 text-center">
          <div className="text-white text-xl">Loading marketplace...</div>
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
            <h1 className="text-4xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-pink-600 mb-2" data-testid="marketplace-title">
              🛍️ Marketplace
            </h1>
            <p className="text-gray-400">Browse shops and purchase items</p>
          </div>
          <Link to="/my-shop">
            <Button className="bg-gradient-to-r from-green-600 to-blue-600" data-testid="my-shop-link">
              <Store className="w-4 h-4 mr-2" />
              My Shop
            </Button>
          </Link>
        </div>

        {shops.length === 0 ? (
          <div className="glass-dark p-12 rounded-2xl text-center">
            <Store className="w-16 h-16 mx-auto mb-4 text-purple-400" />
            <h2 className="text-2xl font-bold mb-2 text-white">No Shops Yet</h2>
            <p className="text-gray-400 mb-6">Be the first to open a shop in the marketplace!</p>
            <Link to="/my-shop">
              <Button className="bg-gradient-to-r from-purple-600 to-pink-600">
                Open Your Shop
              </Button>
            </Link>
          </div>
        ) : (
          <div className="grid lg:grid-cols-3 gap-6">
            {/* Shops List */}
            <div className="lg:col-span-1">
              <div className="glass-dark p-4 rounded-xl">
                <div className="mb-4">
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

                <h3 className="font-bold text-purple-300 mb-3">Shops</h3>
                <div className="space-y-2">
                  {shops.map((shop) => (
                    <button
                      key={shop.id}
                      onClick={() => setSelectedShop(shop.id)}
                      className={`w-full text-left p-3 rounded-lg transition ${
                        selectedShop === shop.id
                          ? 'bg-purple-600/30 border-2 border-purple-500'
                          : 'glass hover:bg-white/10'
                      }`}
                      data-testid={`shop-${shop.id}`}
                    >
                      <h4 className="font-bold text-white">{shop.name}</h4>
                      <p className="text-xs text-gray-400">by {shop.owner_username}</p>
                      <p className="text-xs text-purple-400 mt-1">{shop.nation}</p>
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Shop Items */}
            <div className="lg:col-span-2">
              {currentShop && (
                <div className="glass-dark p-6 rounded-xl mb-6">
                  <h2 className="text-2xl font-bold text-purple-300 mb-2">{currentShop.name}</h2>
                  <p className="text-gray-400 mb-1">{currentShop.description}</p>
                  <p className="text-sm text-purple-400">Owner: {currentShop.owner_username} • {currentShop.nation}</p>
                </div>
              )}

              {items.length === 0 ? (
                <div className="glass-dark p-12 rounded-xl text-center">
                  <Package className="w-12 h-12 mx-auto mb-3 text-gray-400" />
                  <p className="text-gray-400">This shop has no items yet.</p>
                </div>
              ) : (
                <div className="grid md:grid-cols-2 gap-4">
                  {items.map((item) => (
                    <div key={item.id} className="glass p-4 rounded-xl" data-testid={`item-${item.id}`}>
                      <div className="mb-3">
                        <h3 className="font-bold text-white text-lg">{item.name}</h3>
                        <p className="text-xs text-gray-400 mb-2">{item.category}</p>
                        <p className="text-sm text-gray-300">{item.description}</p>
                      </div>

                      <div className="flex items-center justify-between">
                        <div>
                          <p className="text-yellow-400 font-bold text-lg flex items-center gap-1">
                            <Coins className="w-5 h-5" />
                            {item.price}
                          </p>
                          <p className="text-xs text-gray-400">Stock: {item.stock}</p>
                        </div>
                        <Button
                          onClick={() => handlePurchaseClick(item)}
                          disabled={item.stock === 0 || purchasingItems[item.id]}
                          className="bg-gradient-to-r from-green-600 to-blue-600 hover:from-green-700 hover:to-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                          data-testid={`buy-item-${item.id}`}
                        >
                          {purchasingItems[item.id] ? 'Purchasing...' : item.stock === 0 ? 'Out of Stock' : '💰 Purchase'}
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
      
      {/* Character Selection Dialog */}
      <Dialog open={characterSelectDialog.open} onOpenChange={(open) => setCharacterSelectDialog({ open, item: null })}>
        <DialogContent className="bg-gray-900 border-purple-500/30 text-white">
          <DialogHeader>
            <DialogTitle className="text-2xl text-purple-300">Select Character</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <p className="text-gray-400">
              Which character should receive <span className="text-white font-bold">{characterSelectDialog.item?.name}</span>?
            </p>
            {characterSelectDialog.item && (
              <div className="glass p-3 rounded-lg">
                <p className="text-sm text-gray-400 mb-1">Item Details:</p>
                <p className="text-white font-bold">{characterSelectDialog.item.name}</p>
                <p className="text-xs text-gray-400">{characterSelectDialog.item.description}</p>
                <div className="flex items-center gap-4 mt-2">
                  <p className="text-yellow-400 flex items-center gap-1">
                    <Coins className="w-4 h-4" />
                    {characterSelectDialog.item.price}
                  </p>
                  {characterSelectDialog.item.equipment_slot && (
                    <span className="text-xs px-2 py-1 rounded bg-purple-600/20 text-purple-300">
                      {characterSelectDialog.item.equipment_slot}
                    </span>
                  )}
                </div>
              </div>
            )}
            
            {characters.length === 0 ? (
              <div className="text-center py-6">
                <p className="text-gray-400 mb-4">You don't have any characters yet!</p>
                <Link to="/characters">
                  <Button className="bg-gradient-to-r from-purple-600 to-pink-600">
                    Create Character
                  </Button>
                </Link>
              </div>
            ) : (
              <div className="space-y-2 max-h-[400px] overflow-y-auto">
                {characters.map((char) => (
                  <button
                    key={char.id}
                    onClick={() => handlePurchase(
                      characterSelectDialog.item.id,
                      characterSelectDialog.item.name,
                      characterSelectDialog.item.price,
                      char.id
                    )}
                    className="w-full text-left p-4 rounded-lg glass hover:bg-white/10 transition"
                  >
                    <div className="flex items-center gap-3">
                      <User className="w-10 h-10 text-purple-400" />
                      <div className="flex-1">
                        <p className="font-bold text-white">{char.name}</p>
                        <p className="text-xs text-gray-400">{char.race} {char.character_class}</p>
                        <p className="text-xs text-purple-400">Level {char.level}</p>
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default Marketplace;