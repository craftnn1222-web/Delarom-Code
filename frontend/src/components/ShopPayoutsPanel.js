import React, { useEffect, useState, useCallback } from 'react';
import { getShopLedger } from '../utils/api';
import { Coins, TrendingUp, Users, Package, Wallet, RefreshCw } from 'lucide-react';

const fmt = (n) => (n || 0).toLocaleString();
const netClass = (n) => (n > 0 ? 'text-green-400' : n < 0 ? 'text-red-400' : 'text-gray-300');
const fmtDate = (iso) => {
  try { return new Date(iso).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }); }
  catch { return iso; }
};

const Stat = ({ icon: Icon, label, value, cls, testid }) => (
  <div className="bg-black/20 border border-white/10 rounded-lg p-3" data-testid={testid}>
    <div className="flex items-center gap-1.5 text-xs text-gray-400 mb-1">
      <Icon className="w-3.5 h-3.5" />{label}
    </div>
    <div className={`text-lg font-bold ${cls || 'text-white'}`}>{value}</div>
  </div>
);

const ShopPayoutsPanel = ({ shopId, className = '' }) => {
  const [data, setData] = useState(null);
  const [state, setState] = useState('loading');

  const load = useCallback(async () => {
    setState('loading');
    try {
      const res = await getShopLedger(shopId);
      setData(res.data);
      setState('ready');
    } catch (_e) {
      setState('error');
    }
  }, [shopId]);

  useEffect(() => { load(); }, [load]);

  const totals = data?.totals || {};
  const entries = data?.entries || [];

  return (
    <div className={`glass-dark p-6 rounded-xl ${className}`} data-testid="shop-payouts-panel">
      <div className="flex items-center gap-2 mb-1">
        <Wallet className="w-5 h-5 text-amber-300" />
        <h3 className="text-xl font-bold text-amber-200">Owner Payouts</h3>
      </div>
      <p className="text-sm text-gray-400 mb-4">
        Gold earned from sales each ~6h cycle, minus wages and restocking.
      </p>

      {state === 'loading' && (
        <div className="text-center py-6 text-gray-500" data-testid="payouts-loading">Tallying the ledger…</div>
      )}

      {state === 'error' && (
        <div className="text-center py-6" data-testid="payouts-error">
          <p className="text-red-400 mb-3">Couldn&apos;t load your payouts.</p>
          <button onClick={load} className="text-amber-300 inline-flex items-center gap-1 text-sm" data-testid="payouts-retry">
            <RefreshCw className="w-4 h-4" /> Retry
          </button>
        </div>
      )}

      {state === 'ready' && (
        <>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mb-5" data-testid="payouts-totals">
            <Stat icon={Users} label="NPC sales" value={`${fmt(totals.npc_sales)}g`} cls="text-amber-200" testid="total-npc-sales" />
            <Stat icon={Coins} label="Player sales" value={`${fmt(totals.player_sales)}g`} cls="text-amber-200" testid="total-player-sales" />
            <Stat icon={Wallet} label="Wages paid" value={`${fmt(totals.wages)}g`} cls="text-red-300" testid="total-wages" />
            <Stat icon={Package} label="Restock cost" value={`${fmt(totals.restock)}g`} cls="text-red-300" testid="total-restock" />
            <Stat icon={TrendingUp} label="Net (all-time)" value={`${fmt(totals.net)}g`} cls={netClass(totals.net)} testid="total-net" />
          </div>

          <h4 className="text-sm font-semibold text-gray-300 mb-2">Recent cycles</h4>
          {entries.length === 0 ? (
            <p className="text-sm text-gray-500 text-center py-4" data-testid="payouts-empty">
              No pay cycles yet. Earnings appear here after the next economy cycle.
            </p>
          ) : (
            <div className="space-y-2" data-testid="payouts-entries">
              {entries.map((e) => (
                <div key={e.id} className="bg-black/20 border border-white/10 rounded-lg px-3 py-2" data-testid={`ledger-entry-${e.id}`}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs text-gray-400">{fmtDate(e.at)}</span>
                    <span className={`text-sm font-bold ${netClass(e.net)}`}>
                      {e.net >= 0 ? '+' : ''}{fmt(e.net)}g net
                    </span>
                  </div>
                  <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-gray-400">
                    <span>NPC <span className="text-amber-200">{fmt(e.npc_sales_gold)}g</span></span>
                    <span>Players <span className="text-amber-200">{fmt(e.player_sales_gold)}g</span> ({e.player_sales_count})</span>
                    <span>Wages <span className="text-red-300">-{fmt(e.wages_paid)}g</span></span>
                    <span>Restock <span className="text-red-300">-{fmt(e.restock_cost)}g</span></span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default ShopPayoutsPanel;
