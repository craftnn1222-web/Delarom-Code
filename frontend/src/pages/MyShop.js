import React, { useEffect, useState } from 'react';
import { getMyShop, createShop, addItem, getShopItems, deleteShopItem, updateShopItem } from '../utils/api';
import { toast } from 'sonner';
import AnimatedBackground from '../components/AnimatedBackground';
import Navbar from '../components/Navbar';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from '../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Store, Plus, Package, Coins, Trash2, Edit2, AlertTriangle } from 'lucide-react';
import AutoPricingSection from '../components/AutoPricingSection';
import ShopCustomerFeed from '../components/ShopCustomerFeed';

const MyShop = () => {
  const [shop, setShop] = useState(null);
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isShopDialogOpen, setIsShopDialogOpen] = useState(false);
  const [isItemDialogOpen, setIsItemDialogOpen] = useState(false);
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [selectedItem, setSelectedItem] = useState(null);
  const [actionLoading, setActionLoading] = useState(false);
  
  const [shopFormData, setShopFormData] = useState({
    name: '',
    description: '',
    nation: 'Ammeonon',
  });

  const defaultItemFormData = {
    name: '',
    description: '',
    price: 10,
    stock: 1,
    category: 'Weapon',
    item_type: 'equipment',
    equipment_slot: 'weapon',
    stat_bonuses: {
      strength: 0,
      magic: 0,
      agility: 0,
      endurance: 0,
      charisma: 0,
      luck: 0
    },
    // Economy sourcing (2026-02-14). When opted in, price is recomputed from
    // the goods market via the price chain (faction → city → shop markup).
    source_good_slug: '',
    source_city_slug: '',
    source_nation: '',
    markup_pct: 30,
    is_auto_priced: false,
  };

  const [itemFormData, setItemFormData] = useState(defaultItemFormData);

  useEffect(() => {
    fetchShopData();
  }, []);

  const fetchShopData = async () => {
    try {
      const shopRes = await getMyShop();
      setShop(shopRes.data);
      
      const itemsRes = await getShopItems(shopRes.data.id);
      setItems(itemsRes.data);
    } catch (error) {
      // User doesn't have a shop yet
      if (error.response?.status !== 404) {
        toast.error('Failed to load shop data');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleShopChange = (e) => {
    setShopFormData({ ...shopFormData, [e.target.name]: e.target.value });
  };

  const handleItemChange = (e) => {
    const { name, value } = e.target;
    setItemFormData({ 
      ...itemFormData, 
      [name]: name === 'price' || name === 'stock' ? parseInt(value) : value 
    });
  };

  const handleCreateShop = async (e) => {
    e.preventDefault();
    try {
      await createShop(shopFormData);
      toast.success('Shop created successfully!');
      setIsShopDialogOpen(false);
      fetchShopData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create shop');
    }
  };

  const handleAddItem = async (e) => {
    e.preventDefault();
    try {
      await addItem(shop.id, itemFormData);
      toast.success('Item added to your shop!');
      setIsItemDialogOpen(false);
      setItemFormData(defaultItemFormData);
      fetchShopData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to add item');
    }
  };

  const handleEditClick = (item) => {
    setSelectedItem(item);
    setItemFormData({
      name: item.name,
      description: item.description,
      price: item.price,
      stock: item.stock,
      category: item.category || 'Weapon',
      item_type: item.item_type || 'equipment',
      equipment_slot: item.equipment_slot || 'weapon',
      stat_bonuses: item.stat_bonuses || {
        strength: 0,
        magic: 0,
        agility: 0,
        endurance: 0,
        charisma: 0,
        luck: 0
      },
      source_good_slug: item.source_good_slug || '',
      source_city_slug: item.source_city_slug || '',
      source_nation: item.source_nation || '',
      markup_pct: item.markup_pct ?? 30,
      is_auto_priced: Boolean(item.is_auto_priced),
    });
    setIsEditDialogOpen(true);
  };

  const handleUpdateItem = async (e) => {
    e.preventDefault();
    setActionLoading(true);
    try {
      await updateShopItem(selectedItem.id, itemFormData);
      toast.success('Item updated successfully!');
      setIsEditDialogOpen(false);
      setSelectedItem(null);
      setItemFormData(defaultItemFormData);
      fetchShopData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update item');
    } finally {
      setActionLoading(false);
    }
  };

  const handleDeleteClick = (item) => {
    setSelectedItem(item);
    setIsDeleteDialogOpen(true);
  };

  const handleDeleteItem = async () => {
    setActionLoading(true);
    try {
      await deleteShopItem(selectedItem.id);
      toast.success(`"${selectedItem.name}" removed from your shop`);
      setIsDeleteDialogOpen(false);
      setSelectedItem(null);
      fetchShopData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to delete item');
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen relative">
        <AnimatedBackground />
        <Navbar />
        <div className="relative z-10 container mx-auto px-4 py-20 text-center">
          <div className="text-white text-xl">Loading your shop...</div>
        </div>
      </div>
    );
  }

  if (!shop) {
    return (
      <div className="min-h-screen relative">
        <AnimatedBackground />
        <Navbar />
        
        <div className="relative z-10 container mx-auto px-4 py-8">
          <div className="glass-dark p-12 rounded-2xl text-center max-w-2xl mx-auto">
            <Store className="w-20 h-20 mx-auto mb-4 text-purple-400" />
            <h1 className="text-3xl font-bold mb-4 text-white" data-testid="no-shop-title">You Don&apos;t Have a Shop Yet</h1>
            <p className="text-gray-400 mb-6">
              Open your own shop in the marketplace and start selling items to other adventurers!
            </p>
            
            <Dialog open={isShopDialogOpen} onOpenChange={setIsShopDialogOpen}>
              <DialogTrigger asChild>
                <Button className="bg-gradient-to-r from-purple-600 to-pink-600" data-testid="create-shop-btn">
                  <Plus className="w-4 h-4 mr-2" />
                  Create Your Shop
                </Button>
              </DialogTrigger>
              <DialogContent
                className="bg-gray-900 border-purple-500/30 text-white"
                onPointerDownOutside={(e) => e.preventDefault()}
                onInteractOutside={(e) => e.preventDefault()}
              >
                <DialogHeader>
                  <DialogTitle className="text-2xl text-purple-300">Create Your Shop</DialogTitle>
                </DialogHeader>
                <form onSubmit={handleCreateShop} className="space-y-4" data-testid="shop-form">
                  <div>
                    <Label htmlFor="name">Shop Name *</Label>
                    <Input
                      id="name"
                      name="name"
                      value={shopFormData.name}
                      onChange={handleShopChange}
                      required
                      className="bg-black/20 border-purple-500/30"
                      placeholder="e.g., The Dragon's Hoard"
                      data-testid="shop-name-input"
                    />
                  </div>

                  <div>
                    <Label htmlFor="description">Description *</Label>
                    <Textarea
                      id="description"
                      name="description"
                      value={shopFormData.description}
                      onChange={handleShopChange}
                      required
                      className="bg-black/20 border-purple-500/30"
                      placeholder="Describe your shop..."
                      data-testid="shop-description-input"
                    />
                  </div>

                  <div>
                    <Label htmlFor="nation">Nation *</Label>
                    <Select name="nation" value={shopFormData.nation} onValueChange={(value) => setShopFormData({...shopFormData, nation: value})}>
                      <SelectTrigger className="bg-black/20 border-purple-500/30" data-testid="shop-nation-select">
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

                  <Button type="submit" className="w-full bg-gradient-to-r from-purple-600 to-pink-600" data-testid="shop-submit-btn">
                    Create Shop
                  </Button>
                </form>
              </DialogContent>
            </Dialog>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen relative">
      <AnimatedBackground />
      <Navbar />
      
      <div className="relative z-10 container mx-auto px-4 py-8">
        <div className="glass-dark p-6 rounded-xl mb-8" data-testid="shop-header">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-pink-600 mb-2">
                {shop.name}
              </h1>
              <p className="text-gray-400">{shop.description}</p>
              <p className="text-sm text-purple-400 mt-1">{shop.nation}</p>
            </div>
            <Dialog open={isItemDialogOpen} onOpenChange={setIsItemDialogOpen}>
              <DialogTrigger asChild>
                <Button className="bg-gradient-to-r from-green-600 to-blue-600" data-testid="add-item-btn">
                  <Plus className="w-4 h-4 mr-2" />
                  Add Item
                </Button>
              </DialogTrigger>
              <DialogContent
                className="bg-gray-900 border-purple-500/30 text-white"
                onPointerDownOutside={(e) => e.preventDefault()}
                onInteractOutside={(e) => e.preventDefault()}
              >
                <DialogHeader>
                  <DialogTitle className="text-2xl text-purple-300">Add New Item</DialogTitle>
                </DialogHeader>
                <form onSubmit={handleAddItem} className="space-y-4" data-testid="item-form">
                  <div>
                    <Label htmlFor="item-name">Item Name *</Label>
                    <Input
                      id="item-name"
                      name="name"
                      value={itemFormData.name}
                      onChange={handleItemChange}
                      required
                      className="bg-black/20 border-purple-500/30"
                      placeholder="e.g., Dragon Sword"
                      data-testid="item-name-input"
                    />
                  </div>

                  <div>
                    <Label htmlFor="item-description">Description *</Label>
                    <Textarea
                      id="item-description"
                      name="description"
                      value={itemFormData.description}
                      onChange={handleItemChange}
                      required
                      className="bg-black/20 border-purple-500/30"
                      placeholder="Describe the item..."
                      data-testid="item-description-input"
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label htmlFor="price">Price (Gold) *</Label>
                      <Input
                        id="price"
                        name="price"
                        type="number"
                        value={itemFormData.price}
                        onChange={handleItemChange}
                        required
                        min="1"
                        className="bg-black/20 border-purple-500/30"
                        data-testid="item-price-input"
                      />
                    </div>

                    <div>
                      <Label htmlFor="stock">Stock *</Label>
                      <Input
                        id="stock"
                        name="stock"
                        type="number"
                        value={itemFormData.stock}
                        onChange={handleItemChange}
                        required
                        min="1"
                        className="bg-black/20 border-purple-500/30"
                        data-testid="item-stock-input"
                      />
                    </div>
                  </div>

                  <div>
                    <Label htmlFor="category">Category *</Label>
                    <Input
                      id="category"
                      name="category"
                      value={itemFormData.category}
                      onChange={handleItemChange}
                      required
                      className="bg-black/20 border-purple-500/30"
                      placeholder="e.g., Weapon, Armor, Potion"
                      data-testid="item-category-input"
                    />
                  </div>

                  <div>
                    <Label htmlFor="equipment_slot">Equipment Slot *</Label>
                    <Select 
                      name="equipment_slot" 
                      value={itemFormData.equipment_slot} 
                      onValueChange={(value) => setItemFormData({...itemFormData, equipment_slot: value})}
                    >
                      <SelectTrigger className="bg-black/20 border-purple-500/30">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent className="bg-gray-900 border-purple-500/30">
                        <SelectItem value="weapon">Weapon</SelectItem>
                        <SelectItem value="head">Helmet</SelectItem>
                        <SelectItem value="chest">Chest Armor</SelectItem>
                        <SelectItem value="legs">Leg Armor</SelectItem>
                        <SelectItem value="boots">Boots</SelectItem>
                        <SelectItem value="gloves">Gloves</SelectItem>
                        <SelectItem value="ring">Ring</SelectItem>
                        <SelectItem value="necklace">Necklace</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div>
                    <Label className="mb-2 block">Stat Bonuses (Optional)</Label>
                    <div className="grid grid-cols-2 gap-3">
                      {['strength', 'magic', 'agility', 'endurance', 'charisma', 'luck'].map((stat) => (
                        <div key={stat}>
                          <Label htmlFor={`stat-${stat}`} className="text-xs text-gray-400 capitalize">{stat}</Label>
                          <Input
                            id={`stat-${stat}`}
                            type="number"
                            value={itemFormData.stat_bonuses[stat]}
                            onChange={(e) => setItemFormData({
                              ...itemFormData,
                              stat_bonuses: {
                                ...itemFormData.stat_bonuses,
                                [stat]: parseInt(e.target.value) || 0
                              }
                            })}
                            min="0"
                            className="bg-black/20 border-purple-500/30"
                            placeholder="0"
                          />
                        </div>
                      ))}
                    </div>
                  </div>

                  <AutoPricingSection
                    formData={itemFormData}
                    setFormData={setItemFormData}
                  />

                  <Button type="submit" className="w-full bg-gradient-to-r from-green-600 to-blue-600" data-testid="item-submit-btn">
                    Add Item
                  </Button>
                </form>
              </DialogContent>
            </Dialog>
          </div>
        </div>

        <h2 className="text-2xl font-bold text-purple-300 mb-4">Your Items</h2>
        {items.length === 0 ? (
          <div className="glass-dark p-12 rounded-xl text-center">
            <Package className="w-16 h-16 mx-auto mb-4 text-gray-400" />
            <p className="text-gray-400 mb-6">Your shop is empty. Add items to start selling!</p>
            <Button onClick={() => setIsItemDialogOpen(true)} className="bg-gradient-to-r from-green-600 to-blue-600">
              Add Your First Item
            </Button>
          </div>
        ) : (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {items.map((item) => (
              <div key={item.id} className="glass p-4 rounded-xl" data-testid={`shop-item-${item.id}`}>
                <div className="mb-3">
                  <h3 className="font-bold text-white text-lg">{item.name}</h3>
                  <p className="text-xs text-gray-400 mb-2">{item.category}</p>
                  <p className="text-sm text-gray-300">{item.description}</p>
                </div>

                <div className="flex items-center justify-between pt-3 border-t border-purple-500/30">
                  <div>
                    <p className="text-yellow-400 font-bold text-lg flex items-center gap-1">
                      <Coins className="w-5 h-5" />
                      {item.price}
                    </p>
                    <p className="text-xs text-gray-400">Stock: {item.stock}</p>
                  </div>
                  <div className={`px-3 py-1 rounded-full text-xs font-semibold ${
                    item.stock > 0 ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
                  }`}>
                    {item.stock > 0 ? 'Available' : 'Out of Stock'}
                  </div>
                </div>

                {/* Edit and Delete Buttons */}
                <div className="flex gap-2 mt-3 pt-3 border-t border-purple-500/20">
                  <Button 
                    onClick={() => handleEditClick(item)}
                    size="sm"
                    variant="outline"
                    className="flex-1 border-blue-500/50 text-blue-400 hover:bg-blue-500/20"
                    data-testid={`edit-item-${item.id}`}
                  >
                    <Edit2 className="w-3 h-3 mr-1" />
                    Edit
                  </Button>
                  <Button 
                    onClick={() => handleDeleteClick(item)}
                    size="sm"
                    variant="outline"
                    className="flex-1 border-red-500/50 text-red-400 hover:bg-red-500/20"
                    data-testid={`delete-item-${item.id}`}
                  >
                    <Trash2 className="w-3 h-3 mr-1" />
                    Remove
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* NPC walk-in customer feed — populated on every 6h economy tick */}
        {shop && <ShopCustomerFeed shopId={shop.id} className="mt-8" />}

        {/* Delete Confirmation Dialog */}
        <Dialog open={isDeleteDialogOpen} onOpenChange={setIsDeleteDialogOpen}>
          <DialogContent className="bg-gray-900 border-red-500/30 text-white">
            <DialogHeader>
              <DialogTitle className="text-2xl text-red-400 flex items-center gap-2">
                <AlertTriangle className="w-6 h-6" />
                Remove Item
              </DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              <p className="text-gray-300">
                Are you sure you want to remove <span className="font-bold text-white">&quot;{selectedItem?.name}&quot;</span> from your shop?
              </p>
              <p className="text-sm text-gray-400">
                This action cannot be undone. The item will be permanently deleted.
              </p>
            </div>
            <DialogFooter className="flex gap-2">
              <Button
                onClick={() => setIsDeleteDialogOpen(false)}
                className="bg-gray-600 hover:bg-gray-700"
                disabled={actionLoading}
              >
                Cancel
              </Button>
              <Button
                onClick={handleDeleteItem}
                className="bg-red-600 hover:bg-red-700"
                disabled={actionLoading}
              >
                {actionLoading ? 'Removing...' : 'Remove Item'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Edit Item Dialog */}
        <Dialog open={isEditDialogOpen} onOpenChange={setIsEditDialogOpen}>
          <DialogContent
            className="bg-gray-900 border-purple-500/30 text-white max-h-[90vh] overflow-y-auto"
            onPointerDownOutside={(e) => e.preventDefault()}
            onInteractOutside={(e) => e.preventDefault()}
          >
            <DialogHeader>
              <DialogTitle className="text-2xl text-purple-300">Edit Item</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleUpdateItem} className="space-y-4">
              <div>
                <Label htmlFor="edit-name">Item Name *</Label>
                <Input
                  id="edit-name"
                  name="name"
                  value={itemFormData.name}
                  onChange={handleItemChange}
                  required
                  className="bg-black/20 border-purple-500/30"
                />
              </div>

              <div>
                <Label htmlFor="edit-description">Description *</Label>
                <Textarea
                  id="edit-description"
                  name="description"
                  value={itemFormData.description}
                  onChange={handleItemChange}
                  required
                  className="bg-black/20 border-purple-500/30"
                  rows="3"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="edit-price">Price (Gold) *</Label>
                  <Input
                    id="edit-price"
                    name="price"
                    type="number"
                    value={itemFormData.price}
                    onChange={handleItemChange}
                    required
                    min="1"
                    className="bg-black/20 border-purple-500/30"
                  />
                </div>
                <div>
                  <Label htmlFor="edit-stock">Stock *</Label>
                  <Input
                    id="edit-stock"
                    name="stock"
                    type="number"
                    value={itemFormData.stock}
                    onChange={handleItemChange}
                    required
                    min="0"
                    className="bg-black/20 border-purple-500/30"
                  />
                </div>
              </div>

              <div>
                <Label htmlFor="edit-category">Category</Label>
                <Input
                  id="edit-category"
                  name="category"
                  value={itemFormData.category}
                  onChange={handleItemChange}
                  className="bg-black/20 border-purple-500/30"
                />
              </div>

              <div>
                <Label htmlFor="edit-equipment_slot">Equipment Slot</Label>
                <Select 
                  name="equipment_slot" 
                  value={itemFormData.equipment_slot} 
                  onValueChange={(value) => setItemFormData({...itemFormData, equipment_slot: value})}
                >
                  <SelectTrigger className="bg-black/20 border-purple-500/30">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-gray-900 border-purple-500/30">
                    <SelectItem value="weapon">Weapon</SelectItem>
                    <SelectItem value="head">Helmet</SelectItem>
                    <SelectItem value="chest">Chest Armor</SelectItem>
                    <SelectItem value="legs">Leg Armor</SelectItem>
                    <SelectItem value="boots">Boots</SelectItem>
                    <SelectItem value="gloves">Gloves</SelectItem>
                    <SelectItem value="ring">Ring</SelectItem>
                    <SelectItem value="necklace">Necklace</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <AutoPricingSection
                formData={itemFormData}
                setFormData={setItemFormData}
              />

              <div className="flex gap-2 pt-4">
                <Button 
                  type="button" 
                  onClick={() => setIsEditDialogOpen(false)}
                  className="flex-1 bg-gray-600 hover:bg-gray-700"
                  disabled={actionLoading}
                >
                  Cancel
                </Button>
                <Button 
                  type="submit" 
                  className="flex-1 bg-gradient-to-r from-green-600 to-blue-600"
                  disabled={actionLoading}
                >
                  {actionLoading ? 'Saving...' : 'Save Changes'}
                </Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>
      </div>
    </div>
  );
};

export default MyShop;