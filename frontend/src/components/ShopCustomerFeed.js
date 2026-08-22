import React, { useEffect, useState } from 'react';
import { UserRound, Loader2, ShoppingBag } from 'lucide-react';
import api from '../utils/api';

/**
 * Recent Sales panel for a shop owner — surfaces NPC walk-in customers
 * simulated by the 6h economy tick. Silent when there are no sales yet.
 */
const ShopCustomerFeed = ({ shopId, className = '' }) => {
  const [rows, setRows] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const r = await api.get(`/shops/${shopId}/customers?limit=20`);
        if (!cancelled) setRows(Array.isArray(r.data) ? r.data : []);
      } catch {
        if (!cancelled) setRows([]);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [shopId]);

  if (loading) {
    return (
      <div className={`glass-dark p-4 rounded-xl border border-emerald-500/20 flex items-center gap-2 text-stone-400 ${className}`}>
        <Loader2 className="w-4 h-4 animate-spin" />
        <span>Checking the day-book…</span>
      </div>
    );
  }

  if (!rows || rows.length === 0) {
    return (
      <div
        className={`glass-dark p-4 rounded-xl border border-emerald-500/20 text-sm text-stone-400 ${className}`}
        data-testid="shop-customers-empty"
      >
        <ShoppingBag className="w-4 h-4 inline mr-2 text-emerald-300" />
        No customers yet today — but travellers will find you.
      </div>
    );
  }

  return (
    <div
      className={`glass-dark p-5 rounded-xl border border-emerald-500/30 ${className}`}
      data-testid="shop-customers-panel"
    >
      <div className="flex items-center gap-2 mb-3">
        <UserRound className="w-5 h-5 text-emerald-300" />
        <h3 className="text-lg font-semibold text-emerald-200">Recent Customers</h3>
        <span className="ml-auto text-xs text-stone-400">
          NPC walk-ins visit every 6 hours
        </span>
      </div>
      <div className="space-y-1.5 max-h-72 overflow-y-auto pr-1">
        {rows.map((r) => (
          <div
            key={r.id}
            className="flex items-center justify-between rounded-md border border-emerald-900/40 bg-black/25 px-3 py-2 text-sm"
            data-testid={`shop-customer-${r.id}`}
          >
            <div className="min-w-0">
              <div className="text-stone-100 truncate">{r.customer_name}</div>
              <div className="text-xs text-stone-400 truncate">
                bought {r.units}× {r.item_name}
              </div>
            </div>
            <div className="shrink-0 ml-3 text-emerald-300 text-sm font-semibold">
              +{r.price_total}g
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default ShopCustomerFeed;
