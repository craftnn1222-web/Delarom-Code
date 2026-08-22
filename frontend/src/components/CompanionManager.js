import React, { useEffect, useState } from 'react';
import api from '../utils/api';
import { toast } from 'sonner';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Textarea } from './ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from './ui/dialog';
import { Heart, Plus, Trash2, Edit2, Loader2, X, Sparkles, ImageIcon } from 'lucide-react';

/**
 * CompanionManager — modal for managing a character's preset NPC companions.
 *
 * Player-managed NPCs are stored as regular NPCs with `created_by_character_id`
 * set to this character. By default they are auto-bonded as companions so they
 * appear in every scene the character visits.
 */
const EMPTY_FORM = {
  name: '',
  race: 'Human',
  role: 'Companion',
  appearance: '',
  personality: '',
  motivation: '',
  background: '',
  quirks: '',
  importance: 'commoner',
};

const CompanionManager = ({ open, onOpenChange, character }) => {
  const [companions, setCompanions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [portraitGeneratingId, setPortraitGeneratingId] = useState(null);
  const [editingId, setEditingId] = useState(null); // null = create mode
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState(EMPTY_FORM);

  useEffect(() => {
    if (open && character?.id) {
      fetchCompanions();
      setShowForm(false);
      setEditingId(null);
      setFormData(EMPTY_FORM);
    }
    // fetchCompanions is stable inside this component; no need to put it in deps
  }, [open, character?.id]); // eslint-disable-line

  const fetchCompanions = async () => {
    if (!character?.id) return;
    setLoading(true);
    try {
      const res = await api.get(`/characters/${character.id}/owned-npcs`);
      setCompanions(res.data || []);
    } catch (err) {
      console.error('Failed to load companions:', err);
      toast.error('Failed to load companions');
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const openCreateForm = () => {
    setEditingId(null);
    setFormData(EMPTY_FORM);
    setShowForm(true);
  };

  const openEditForm = (companion) => {
    setEditingId(companion.id);
    setFormData({
      name: companion.name || '',
      race: companion.race || 'Human',
      role: companion.role || 'Companion',
      appearance: companion.appearance || '',
      personality: companion.personality || '',
      motivation: companion.motivation || '',
      background: companion.background || '',
      quirks: companion.quirks || '',
      importance: companion.importance || 'commoner',
    });
    setShowForm(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.name.trim()) {
      toast.error('Name is required');
      return;
    }
    setSaving(true);
    try {
      if (editingId) {
        await api.patch(`/owned-npcs/${editingId}`, formData);
        toast.success(`${formData.name} updated`);
      } else {
        await api.post(`/characters/${character.id}/owned-npcs`, {
          ...formData,
          auto_bond: true,
        });
        toast.success(`${formData.name} now travels with ${character.name}`);
      }
      setShowForm(false);
      setEditingId(null);
      setFormData(EMPTY_FORM);
      await fetchCompanions();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to save companion');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (companion) => {
    if (!window.confirm(`Delete ${companion.name}? This cannot be undone.`)) {
      return;
    }
    try {
      await api.delete(`/owned-npcs/${companion.id}`);
      toast.success(`${companion.name} released`);
      await fetchCompanions();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to delete companion');
    }
  };

  const handleGeneratePortrait = async (companion) => {
    if (!companion.appearance || !companion.appearance.trim()) {
      toast.error('Add an Appearance description first — that\u2019s what the portrait is based on.');
      return;
    }
    setPortraitGeneratingId(companion.id);
    try {
      const res = await api.post(`/owned-npcs/${companion.id}/portrait`);
      toast.success(`Portrait painted for ${companion.name}`);
      // Optimistic update so the new portrait shows immediately
      setCompanions((prev) =>
        prev.map((c) => (c.id === companion.id ? { ...c, image_url: res.data.image_url } : c))
      );
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to generate portrait');
    } finally {
      setPortraitGeneratingId(null);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className="bg-gray-900 border-pink-500/30 text-white max-w-3xl max-h-[90vh] overflow-y-auto"
        data-testid="companion-manager-modal"
      >
        <DialogHeader>
          <DialogTitle className="text-2xl text-pink-300 flex items-center gap-2">
            <Heart className="w-6 h-6" fill="currentColor" />
            Companions of {character?.name || ''}
          </DialogTitle>
          <DialogDescription className="text-sm text-gray-400">
            Preset NPCs who always travel with this character. They appear in
            every scene and react to your roleplay in their own voice.
          </DialogDescription>
        </DialogHeader>

        {/* Existing companions list */}
        {loading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-6 h-6 animate-spin text-pink-300" />
          </div>
        ) : companions.length === 0 ? (
          <div className="text-center py-8 text-gray-400 border border-pink-500/20 rounded-lg bg-black/30">
            No companions yet. Add one below to bring them on every adventure.
          </div>
        ) : (
          <div className="space-y-3" data-testid="companion-list">
            {companions.map((c) => (
              <div
                key={c.id}
                className="p-4 rounded-lg border border-pink-500/30 bg-pink-900/10"
                data-testid={`owned-companion-${c.id}`}
              >
                <div className="flex items-start gap-3">
                  {/* Portrait or placeholder */}
                  <div className="flex-shrink-0">
                    {c.image_url ? (
                      <img
                        src={c.image_url}
                        alt={c.name}
                        className="w-20 h-20 rounded-lg object-cover border-2 border-pink-500/40"
                        data-testid={`companion-portrait-${c.id}`}
                      />
                    ) : (
                      <div className="w-20 h-20 rounded-lg border-2 border-dashed border-pink-500/40 bg-black/30 flex items-center justify-center">
                        <ImageIcon className="w-7 h-7 text-pink-300/40" />
                      </div>
                    )}
                  </div>

                  <div className="flex-1 min-w-0">
                    <p className="font-semibold text-pink-100">
                      {c.name}
                      <span className="ml-2 text-xs text-pink-200/70 font-normal">
                        {c.race} • {c.role}
                      </span>
                    </p>
                    {c.personality && (
                      <p className="text-xs text-gray-300 mt-1 italic line-clamp-2">
                        {c.personality}
                      </p>
                    )}
                    {c.motivation && (
                      <p className="text-xs text-gray-400 mt-1 line-clamp-2">
                        <span className="text-pink-300/70">Driven by:</span> {c.motivation}
                      </p>
                    )}
                    <div className="flex flex-wrap gap-2 mt-3">
                      <button
                        type="button"
                        onClick={() => handleGeneratePortrait(c)}
                        disabled={portraitGeneratingId === c.id}
                        className="text-xs text-purple-200 hover:text-white bg-purple-900/40 hover:bg-purple-800/60 disabled:opacity-50 border border-purple-500/40 rounded-full px-2 py-1 inline-flex items-center gap-1"
                        data-testid={`generate-portrait-${c.id}`}
                      >
                        {portraitGeneratingId === c.id ? (
                          <>
                            <Loader2 className="w-3 h-3 animate-spin" /> Painting…
                          </>
                        ) : (
                          <>
                            <Sparkles className="w-3 h-3" />
                            {c.image_url ? 'Regenerate Portrait' : 'Generate Portrait'}
                          </>
                        )}
                      </button>
                      <button
                        type="button"
                        onClick={() => openEditForm(c)}
                        className="text-xs text-pink-200 hover:text-white bg-pink-900/40 hover:bg-pink-800/60 border border-pink-500/40 rounded-full px-2 py-1 inline-flex items-center gap-1"
                        data-testid={`edit-companion-${c.id}`}
                      >
                        <Edit2 className="w-3 h-3" /> Edit
                      </button>
                      <button
                        type="button"
                        onClick={() => handleDelete(c)}
                        className="text-xs text-red-200 hover:text-white bg-red-900/40 hover:bg-red-800/60 border border-red-500/40 rounded-full px-2 py-1 inline-flex items-center gap-1"
                        data-testid={`delete-companion-${c.id}`}
                      >
                        <Trash2 className="w-3 h-3" /> Delete
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Add / Edit form */}
        {!showForm ? (
          <Button
            type="button"
            onClick={openCreateForm}
            className="w-full bg-gradient-to-r from-pink-600 to-purple-600 hover:from-pink-700 hover:to-purple-700 mt-2"
            data-testid="add-companion-btn"
          >
            <Plus className="w-4 h-4 mr-2" />
            Add Companion
          </Button>
        ) : (
          <form
            onSubmit={handleSubmit}
            className="space-y-3 border border-pink-500/30 rounded-lg p-4 bg-black/30"
            data-testid="companion-form"
          >
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold text-pink-300">
                {editingId ? 'Edit Companion' : 'New Companion'}
              </h3>
              <button
                type="button"
                onClick={() => {
                  setShowForm(false);
                  setEditingId(null);
                  setFormData(EMPTY_FORM);
                }}
                className="text-gray-400 hover:text-white"
                data-testid="cancel-companion-form-btn"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label htmlFor="name">Name *</Label>
                <Input
                  id="name"
                  name="name"
                  value={formData.name}
                  onChange={handleChange}
                  required
                  className="bg-black/30 border-pink-500/30"
                  placeholder="Orion"
                  data-testid="companion-name-input"
                />
              </div>
              <div>
                <Label htmlFor="race">Race</Label>
                <Input
                  id="race"
                  name="race"
                  value={formData.race}
                  onChange={handleChange}
                  className="bg-black/30 border-pink-500/30"
                  placeholder="Human"
                />
              </div>
              <div>
                <Label htmlFor="role">Role</Label>
                <Input
                  id="role"
                  name="role"
                  value={formData.role}
                  onChange={handleChange}
                  className="bg-black/30 border-pink-500/30"
                  placeholder="Steward"
                />
              </div>
              <div>
                <Label htmlFor="importance">Importance</Label>
                <select
                  id="importance"
                  name="importance"
                  value={formData.importance}
                  onChange={handleChange}
                  className="w-full bg-black/30 border border-pink-500/30 rounded-md px-3 py-2 text-sm"
                  data-testid="companion-importance-select"
                >
                  <option value="commoner">Commoner</option>
                  <option value="notable">Notable</option>
                  <option value="noble">Noble</option>
                  <option value="ruler">Ruler</option>
                </select>
              </div>
            </div>

            <div>
              <Label htmlFor="appearance">Appearance</Label>
              <Textarea
                id="appearance"
                name="appearance"
                value={formData.appearance}
                onChange={handleChange}
                rows={2}
                className="bg-black/30 border-pink-500/30"
                placeholder="A grey-bearded man in deep blue robes, always with a ledger"
              />
            </div>

            <div>
              <Label htmlFor="personality">Personality</Label>
              <Textarea
                id="personality"
                name="personality"
                value={formData.personality}
                onChange={handleChange}
                rows={2}
                className="bg-black/30 border-pink-500/30"
                placeholder="Dry-witted, fiercely loyal, never raises his voice"
              />
            </div>

            <div>
              <Label htmlFor="motivation">Motivation</Label>
              <Textarea
                id="motivation"
                name="motivation"
                value={formData.motivation}
                onChange={handleChange}
                rows={2}
                className="bg-black/30 border-pink-500/30"
                placeholder="To serve the throne faithfully"
              />
            </div>

            <div>
              <Label htmlFor="background">Background (optional)</Label>
              <Textarea
                id="background"
                name="background"
                value={formData.background}
                onChange={handleChange}
                rows={2}
                className="bg-black/30 border-pink-500/30"
                placeholder="Has served the household for forty years"
              />
            </div>

            <Button
              type="submit"
              disabled={saving}
              className="w-full bg-gradient-to-r from-pink-600 to-purple-600 hover:from-pink-700 hover:to-purple-700"
              data-testid="save-companion-btn"
            >
              {saving ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Saving…
                </>
              ) : editingId ? (
                'Update Companion'
              ) : (
                'Bond Companion'
              )}
            </Button>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
};

export default CompanionManager;
