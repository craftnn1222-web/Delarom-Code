import React from 'react';
import { Label } from './ui/label';
import { Input } from './ui/input';
import { Switch } from './ui/switch';
import { RefreshCw } from 'lucide-react';

/**
 * Auto-Restock controls for a shop item. Tops the item back up to a target
 * stock level on each ~6h economy cycle so it never sells out.
 */
const RestockSection = ({ formData, setFormData }) => {
  const enabled = Boolean(formData.auto_restock);
  return (
    <div className="border border-amber-500/30 bg-amber-900/10 rounded-lg p-4 space-y-3" data-testid="restock-section">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <RefreshCw className="w-4 h-4 text-amber-300" />
          <Label className="text-amber-200 mb-0">Auto-restock</Label>
        </div>
        <Switch
          checked={enabled}
          onCheckedChange={(v) => setFormData((p) => ({ ...p, auto_restock: v }))}
          data-testid="restock-toggle"
        />
      </div>
      <p className="text-xs text-gray-400">
        Automatically top this item back up to a target stock level every ~6h economy cycle, so your shelves never stay empty.
      </p>
      {enabled && (
        <div>
          <Label htmlFor="restock_target" className="text-xs text-gray-400">Restock up to (stock target)</Label>
          <Input
            id="restock_target"
            type="number"
            min="1"
            value={formData.restock_target ?? ''}
            onChange={(e) => setFormData((p) => ({ ...p, restock_target: parseInt(e.target.value) || 0 }))}
            className="bg-black/20 border-amber-500/30 text-white"
            data-testid="restock-target-input"
          />
          <p className="text-xs text-amber-300/80 mt-2" data-testid="restock-cost-hint">
            Wholesale cost: ~{Math.ceil((Number(formData.price) || 0) * 0.2) * (Number(formData.restock_target) || 0)}g to fully refill
            ({Math.ceil((Number(formData.price) || 0) * 0.2)}g per unit). Charged from your gold each cycle; skipped if you can&apos;t afford it.
          </p>
        </div>
      )}
    </div>
  );
};

export default RestockSection;
