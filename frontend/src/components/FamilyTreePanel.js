import React, { useEffect, useState, useCallback } from 'react';
import { toast } from 'sonner';
import {
  fetchFamily, addRelative, updateRelative, deleteRelative, fetchRelationshipTypes,
} from '../utils/api';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Textarea } from './ui/textarea';
import { Label } from './ui/label';
import { TreePine, Plus, Trash2, Pencil } from 'lucide-react';

/**
 * FamilyTreePanel — embeddable card for editing a character's declared
 * relatives. Used inside the character edit/profile flow.
 */

const STATUS_COLORS = {
  living:    'text-emerald-300',
  deceased:  'text-gray-400',
  missing:   'text-amber-300',
  estranged: 'text-rose-300',
  unknown:   'text-gray-500',
};

const FamilyTreePanel = ({ characterId, canEdit = true }) => {
  const [relatives, setRelatives] = useState([]);
  const [loading, setLoading] = useState(true);
  const [types, setTypes] = useState({ relationships: [], statuses: [] });
  const [editing, setEditing] = useState(null); // null | 'new' | relative_id
  const [form, setForm] = useState({ name: '', relationship: 'sibling', status: 'unknown', story: '' });

  const load = useCallback(async () => {
    try {
      const [r, t] = await Promise.all([fetchFamily(characterId), fetchRelationshipTypes()]);
      setRelatives(r.data || []);
      setTypes(t.data || { relationships: [], statuses: [] });
    } catch (e) { console.debug("Silent failure:", e); }
    finally { setLoading(false); }
  }, [characterId]);

  useEffect(() => { load(); }, [load]);

  const startNew = () => {
    setForm({ name: '', relationship: 'sibling', status: 'unknown', story: '' });
    setEditing('new');
  };

  const startEdit = (r) => {
    setForm({ name: r.name, relationship: r.relationship, status: r.status, story: r.story || '' });
    setEditing(r.id);
  };

  const cancel = () => setEditing(null);

  const submit = async (e) => {
    e.preventDefault();
    if (!form.name.trim()) { toast.error('Name is required.'); return; }
    try {
      if (editing === 'new') {
        await addRelative(characterId, form);
        toast.success('Kin remembered.');
      } else {
        await updateRelative(characterId, editing, form);
        toast.success('Updated.');
      }
      setEditing(null);
      load();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Save failed');
    }
  };

  const remove = async (id) => {
    try {
      await deleteRelative(characterId, id);
      toast.success('Kin removed.');
      load();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed.');
    }
  };

  if (loading) return null;

  return (
    <div className="glass-dark p-5 rounded-xl border border-emerald-700/30" data-testid="family-tree-panel">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-lg font-bold text-emerald-200 flex items-center gap-2">
          <TreePine className="w-5 h-5" /> Family & Bloodline
          <span className="text-xs text-gray-500 font-normal">({relatives.length})</span>
        </h3>
        {canEdit && editing === null && (
          <Button size="sm" onClick={startNew} className="bg-emerald-700 hover:bg-emerald-600" data-testid="family-add-btn">
            <Plus className="w-4 h-4 mr-1" /> Add Kin
          </Button>
        )}
      </div>

      {editing !== null && (
        <form onSubmit={submit} className="mb-4 p-3 bg-black/30 rounded-lg border border-emerald-600/30" data-testid="family-edit-form">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mb-2">
            <div>
              <Label className="text-gray-300 text-xs">Name</Label>
              <Input value={form.name} onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))} maxLength={120} className="mt-1 bg-black/30 border-emerald-500/30 text-white" data-testid="family-name-input" />
            </div>
            <div>
              <Label className="text-gray-300 text-xs">Relationship</Label>
              <select value={form.relationship} onChange={(e) => setForm((f) => ({ ...f, relationship: e.target.value }))} className="mt-1 w-full bg-black/30 border border-emerald-500/30 text-white rounded-md px-2 py-1.5 capitalize" data-testid="family-relationship-select">
                {types.relationships.map((r) => (<option key={r} value={r} className="bg-black capitalize">{r.replace(/-/g, ' ')}</option>))}
              </select>
            </div>
            <div className="sm:col-span-2">
              <Label className="text-gray-300 text-xs">Status</Label>
              <div className="flex flex-wrap gap-2 mt-1" data-testid="family-status-toggle">
                {types.statuses.map((s) => (
                  <button key={s} type="button" onClick={() => setForm((f) => ({ ...f, status: s }))} className={`text-xs px-3 py-1 rounded-full border capitalize ${form.status === s ? 'bg-emerald-600/40 border-emerald-400 text-white' : 'bg-black/30 border-gray-600/40 text-gray-300 hover:text-white'}`}>
                    {s}
                  </button>
                ))}
              </div>
            </div>
          </div>
          <Label className="text-gray-300 text-xs">Story (optional)</Label>
          <Textarea value={form.story} onChange={(e) => setForm((f) => ({ ...f, story: e.target.value }))} maxLength={800} rows={3} className="mt-1 bg-black/30 border-emerald-500/30 text-white" data-testid="family-story-input" />
          <div className="flex gap-2 mt-2 justify-end">
            <Button type="button" size="sm" variant="outline" onClick={cancel}>Cancel</Button>
            <Button type="submit" size="sm" className="bg-emerald-700 hover:bg-emerald-600" data-testid="family-save-btn">
              {editing === 'new' ? 'Add' : 'Save'}
            </Button>
          </div>
        </form>
      )}

      {relatives.length === 0 ? (
        <p className="text-gray-500 italic text-sm">No kin declared.</p>
      ) : (
        <ul className="space-y-2" data-testid="family-list">
          {relatives.map((r) => (
            <li key={r.id} className="p-3 bg-emerald-950/20 border border-emerald-700/20 rounded-lg" data-testid={`relative-${r.id}`}>
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                  <p className="font-bold text-gray-100">
                    {r.name}
                    <span className="ml-2 text-xs text-gray-400 capitalize">— {r.relationship.replace(/-/g, ' ')}</span>
                    <span className={`ml-2 text-xs uppercase tracking-widest ${STATUS_COLORS[r.status] || 'text-gray-500'}`}>{r.status}</span>
                  </p>
                  {r.story && <p className="text-sm text-gray-300 mt-1 italic">{r.story}</p>}
                </div>
                {canEdit && (
                  <div className="flex gap-1 flex-shrink-0">
                    <button onClick={() => startEdit(r)} className="text-gray-400 hover:text-emerald-300" data-testid={`relative-edit-${r.id}`}>
                      <Pencil className="w-4 h-4" />
                    </button>
                    <button onClick={() => remove(r.id)} className="text-gray-400 hover:text-red-300" data-testid={`relative-delete-${r.id}`}>
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

export default FamilyTreePanel;
