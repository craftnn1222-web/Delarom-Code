import React, { useEffect, useState, useCallback } from 'react';
import { Coins, TrendingUp, TrendingDown, Plus, Trash2, Pencil } from 'lucide-react';
import { Button } from '../ui/button';
import { toast } from 'sonner';
import api, { addFactionCustomOffering } from '../../utils/api';

/**
 * Faction Specialties tab — shows the goods this faction produces (base cost
 * per unit, capacity per tick). If the current viewer is the faction's
 * Leader (or an admin), they get an "Add / Edit / Remove" UI for the lineup.
 *
 * Used inside FactionDetail.js as `<FactionSpecialtiesTab />`.
 */
const FactionSpecialtiesTab = ({ factionSlug, canEdit }) => {
  const [specialties, setSpecialties] = useState([]);
  const [catalogue, setCatalogue] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editingGood, setEditingGood] = useState(null);
  const [form, setForm] = useState({ good_slug: '', base_cost: 50, capacity: 50, description: '', mode: 'catalogue', name: '', category: '', unit: 'per unit' });
  const [busy, setBusy] = useState(false);

  const loadAll = useCallback(async () => {
    setLoading(true);
    try {
      const [specRes, goodsRes] = await Promise.allSettled([
        api.get(`/economy/factions/${factionSlug}/specialties`),
        api.get('/economy/goods'),
      ]);
      if (specRes.status === 'fulfilled') {
        setSpecialties(specRes.value.data?.specialties || []);
      }
      if (goodsRes.status === 'fulfilled') setCatalogue(goodsRes.value.data || []);
    } finally {
      setLoading(false);
    }
  }, [factionSlug]);

  useEffect(() => { loadAll(); }, [loadAll]);

  const openAdd = () => {
    setEditingGood(null);
    setForm({ good_slug: catalogue[0]?.slug || '', base_cost: 50, capacity: 50, description: '', mode: 'catalogue', name: '', category: '', unit: 'per unit' });
    setShowForm(true);
  };

  const openEdit = (s) => {
    setEditingGood(s.good_slug);
    setForm({
      good_slug: s.good_slug,
      base_cost: s.base_cost || 0,
      capacity: s.capacity || 0,
      description: s.description || '',
      mode: 'catalogue',
      name: '',
      category: '',
      unit: 'per unit',
    });
    setShowForm(true);
  };

  const submit = async () => {
    if (form.base_cost <= 0) {
      toast.error('Set a positive base cost.');
      return;
    }
    setBusy(true);
    try {
      if (!editingGood && form.mode === 'custom') {
        if (!form.name.trim()) {
          toast.error('Name your custom product.');
          setBusy(false);
          return;
        }
        await addFactionCustomOffering(factionSlug, {
          name: form.name.trim(),
          category: form.category.trim() || 'custom',
          unit: form.unit.trim() || 'per unit',
          base_cost: Number(form.base_cost),
          capacity: Number(form.capacity || 50),
          description: form.description || '',
        });
        toast.success('Custom offering coined.');
      } else {
        if (!form.good_slug) {
          toast.error('Pick a good.');
          setBusy(false);
          return;
        }
        await api.post(`/economy/factions/${factionSlug}/specialties`, {
          faction_slug: factionSlug,
          good_slug: form.good_slug,
          base_cost: Number(form.base_cost),
          capacity: Number(form.capacity || 50),
          description: form.description || '',
          reason: editingGood ? 'Leader adjustment' : 'Leader added offering',
        });
        toast.success(editingGood ? 'Specialty updated.' : 'Specialty added.');
      }
      setShowForm(false);
      await loadAll();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to save offering');
    } finally {
      setBusy(false);
    }
  };

  const remove = async (goodSlug) => {
    if (!window.confirm(`Remove ${goodSlug} from this faction's offerings?`)) return;
    try {
      await api.delete(`/economy/factions/${factionSlug}/specialties/${goodSlug}`);
      toast.success('Specialty removed.');
      await loadAll();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to remove specialty');
    }
  };

  if (loading) {
    return <p className="text-gray-400 italic">Loading ledger…</p>;
  }

  return (
    <section data-testid="faction-specialties-tab">
      <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
        <div>
          <h2 className="text-sm uppercase tracking-[0.3em] text-gray-400">
            Offerings ({specialties.length})
          </h2>
          <p className="text-xs text-gray-500 mt-1 italic">
            What this faction produces, at the base cost they charge per unit.
            Cities buying from them pay this plus tariff; merchants then add their margin.
          </p>
        </div>
        {canEdit && (
          <Button
            type="button"
            onClick={openAdd}
            className="bg-amber-600 hover:bg-amber-700 text-black"
            data-testid="specialties-add-btn"
          >
            <Plus className="w-4 h-4 mr-1" />
            Add Offering
          </Button>
        )}
      </div>

      {specialties.length === 0 ? (
        <div
          className="p-6 rounded-xl glass-dark border border-gray-700/40 text-center"
          data-testid="specialties-empty"
        >
          <Coins className="w-8 h-8 mx-auto mb-2 text-gray-500" />
          <p className="text-gray-400 italic">
            This faction has not declared what it offers to the realms.
          </p>
          {canEdit && (
            <p className="text-xs text-gray-500 mt-2">
              As Leader, you can list what your faction produces — goods, services, or contraband.
            </p>
          )}
        </div>
      ) : (
        <div className="grid sm:grid-cols-2 gap-3" data-testid="specialties-list">
          {specialties.map((s) => {
            const lastDelta = (s.cost_history || []).slice(-1)[0];
            const moved = lastDelta && lastDelta.delta;
            const ToneIcon = moved && moved > 0 ? TrendingUp : moved && moved < 0 ? TrendingDown : null;
            const toneColor = moved && moved > 0 ? 'text-rose-300' : moved && moved < 0 ? 'text-emerald-300' : 'text-gray-400';
            return (
              <div
                key={s.id || s.good_slug}
                className="p-4 rounded-lg glass-dark border border-amber-500/20"
                data-testid={`specialty-${s.good_slug}`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <p className="font-semibold text-amber-100">
                      {s.good_name || s.good_slug}
                    </p>
                    <p className="text-[10px] uppercase tracking-wider text-amber-200/60">
                      {s.good_category} · {s.good_unit}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-lg font-bold text-amber-200">{s.base_cost}g</p>
                    <p className="text-[10px] text-amber-200/50">cap {s.capacity}</p>
                  </div>
                </div>
                {s.description && (
                  <p className="text-xs text-gray-400 italic mt-2">{s.description}</p>
                )}
                {moved && ToneIcon && (
                  <p className={`text-xs mt-2 flex items-center gap-1 ${toneColor}`}>
                    <ToneIcon className="w-3 h-3" />
                    {moved > 0 ? '+' : ''}{moved}g · {lastDelta.reason || 'recent shift'}
                  </p>
                )}
                {canEdit && (
                  <div className="flex gap-2 mt-3">
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      className="text-xs"
                      onClick={() => openEdit(s)}
                      data-testid={`specialty-edit-${s.good_slug}`}
                    >
                      <Pencil className="w-3 h-3 mr-1" />
                      Edit
                    </Button>
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      className="text-xs text-rose-300 border-rose-500/40 hover:bg-rose-900/30"
                      onClick={() => remove(s.good_slug)}
                      data-testid={`specialty-remove-${s.good_slug}`}
                    >
                      <Trash2 className="w-3 h-3 mr-1" />
                      Remove
                    </Button>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Add/Edit modal — kept inline (no Radix Dialog) to avoid pointer-events issues */}
      {showForm && (
        <div className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4">
          <div
            className="glass-dark border border-amber-500/40 rounded-xl p-5 max-w-md w-full"
            data-testid="specialty-form-modal"
          >
            <h3 className="text-lg font-semibold text-amber-200 mb-3">
              {editingGood ? `Edit ${editingGood}` : 'Add New Offering'}
            </h3>
            <div className="space-y-3">
              {!editingGood && (
                <div className="flex gap-2" data-testid="offering-mode-toggle">
                  <button
                    type="button"
                    onClick={() => setForm({ ...form, mode: 'catalogue' })}
                    className={`flex-1 text-xs py-2 rounded border ${form.mode === 'catalogue' ? 'bg-amber-600 text-black border-amber-500' : 'border-amber-500/40 text-amber-200'}`}
                    data-testid="offering-mode-catalogue"
                  >
                    From catalogue
                  </button>
                  <button
                    type="button"
                    onClick={() => setForm({ ...form, mode: 'custom' })}
                    className={`flex-1 text-xs py-2 rounded border ${form.mode === 'custom' ? 'bg-amber-600 text-black border-amber-500' : 'border-amber-500/40 text-amber-200'}`}
                    data-testid="offering-mode-custom"
                  >
                    Type your own
                  </button>
                </div>
              )}
              {(!editingGood && form.mode === 'custom') ? (
                <>
                  <div>
                    <label className="text-xs uppercase tracking-wider text-amber-200/70">Product name</label>
                    <input
                      type="text"
                      value={form.name}
                      onChange={(e) => setForm({ ...form, name: e.target.value })}
                      className="w-full bg-black/50 border border-amber-500/40 rounded p-2 text-sm text-amber-100"
                      placeholder="e.g. Moonsteel Blades"
                      data-testid="offering-custom-name"
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="text-xs uppercase tracking-wider text-amber-200/70">Category</label>
                      <input
                        type="text"
                        value={form.category}
                        onChange={(e) => setForm({ ...form, category: e.target.value })}
                        className="w-full bg-black/50 border border-amber-500/40 rounded p-2 text-sm text-amber-100"
                        placeholder="e.g. weapon"
                        data-testid="offering-custom-category"
                      />
                    </div>
                    <div>
                      <label className="text-xs uppercase tracking-wider text-amber-200/70">Unit</label>
                      <input
                        type="text"
                        value={form.unit}
                        onChange={(e) => setForm({ ...form, unit: e.target.value })}
                        className="w-full bg-black/50 border border-amber-500/40 rounded p-2 text-sm text-amber-100"
                        placeholder="e.g. per blade"
                        data-testid="offering-custom-unit"
                      />
                    </div>
                  </div>
                </>
              ) : (
                <div>
                  <label className="text-xs uppercase tracking-wider text-amber-200/70">Good</label>
                  <select
                    value={form.good_slug}
                    onChange={(e) => setForm({ ...form, good_slug: e.target.value })}
                    disabled={!!editingGood}
                    className="w-full bg-black/50 border border-amber-500/40 rounded p-2 text-sm text-amber-100 disabled:opacity-60"
                    data-testid="specialty-form-good-select"
                  >
                    {catalogue.map((g) => (
                      <option key={g.slug} value={g.slug}>
                        {g.name} ({g.category} · {g.unit})
                      </option>
                    ))}
                  </select>
                </div>
              )}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs uppercase tracking-wider text-amber-200/70">Base cost (g/unit)</label>
                  <input
                    type="number"
                    min="1"
                    value={form.base_cost}
                    onChange={(e) => setForm({ ...form, base_cost: e.target.value })}
                    className="w-full bg-black/50 border border-amber-500/40 rounded p-2 text-sm text-amber-100"
                    data-testid="specialty-form-base-cost"
                  />
                </div>
                <div>
                  <label className="text-xs uppercase tracking-wider text-amber-200/70">Capacity/tick</label>
                  <input
                    type="number"
                    min="1"
                    value={form.capacity}
                    onChange={(e) => setForm({ ...form, capacity: e.target.value })}
                    className="w-full bg-black/50 border border-amber-500/40 rounded p-2 text-sm text-amber-100"
                    data-testid="specialty-form-capacity"
                  />
                </div>
              </div>
              <div>
                <label className="text-xs uppercase tracking-wider text-amber-200/70">Description (optional)</label>
                <textarea
                  rows={2}
                  value={form.description}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                  className="w-full bg-black/50 border border-amber-500/40 rounded p-2 text-sm text-amber-100"
                  placeholder="How / why your faction produces this"
                  data-testid="specialty-form-description"
                />
              </div>
            </div>
            <div className="flex justify-end gap-2 mt-4">
              <Button
                type="button"
                variant="outline"
                onClick={() => setShowForm(false)}
                disabled={busy}
                data-testid="specialty-form-cancel"
              >
                Cancel
              </Button>
              <Button
                type="button"
                onClick={submit}
                disabled={busy}
                className="bg-amber-600 hover:bg-amber-700 text-black"
                data-testid="specialty-form-save"
              >
                {busy ? 'Saving…' : editingGood ? 'Save Changes' : 'Add Offering'}
              </Button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
};

export default FactionSpecialtiesTab;
