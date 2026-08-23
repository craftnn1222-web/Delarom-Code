import React, { useEffect, useState, useCallback } from 'react';
import {
  getShopBuyOffers, acceptShopBuyOffer, declineShopBuyOffer,
  depositShopTreasury, withdrawShopTreasury,
} from '../utils/api';
import { toast } from 'sonner';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Wallet, Check, X, ArrowDownToLine, ArrowUpFromLine, Tag } from 'lucide-react';

const ShopBuyOffersPanel = ({ shopId, className = '' }) => {
  const [treasury, setTreasury] = useState(0);
  const [offers, setOffers] = useState([]);
  const [state, setState] = useState('loading');
  const [busy, setBusy] = useState('');
  const [amount, setAmount] = useState('');

  const load = useCallback(async () => {
    setState('loading');
    try {
      const res = await getShopBuyOffers(shopId);
      setTreasury(res.data.treasury || 0);
      setOffers(res.data.offers || []);
      setState('ready');
    } catch (_e) {
      setState('error');
    }
  }, [shopId]);

  useEffect(() => { load(); }, [load]);

  const move = async (dir) => {
    const amt = parseInt(amount, 10);
    if (!amt || amt <= 0) { toast.error('Enter a positive amount'); return; }
    setBusy(dir);
    try {
      const fn = dir === 'deposit' ? depositShopTreasury : withdrawShopTreasury;
      const res = await fn(shopId, amt);
      setTreasury(res.data.treasury);
      setAmount('');
      toast.success(dir === 'deposit' ? `Deposited ${amt}g` : `Withdrew ${amt}g`);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Could not move gold');
    } finally {
      setBusy('');
    }
  };

  const resolve = async (offer, action) => {
    setBusy(offer.id);
    try {
      if (action === 'accept') {
        const res = await acceptShopBuyOffer(shopId, offer.id);
        toast.success(`Bought ${offer.item.name} (paid from ${res.data.paid_from}). Re-listed at ${res.data.resale_price}g.`);
      } else {
        await declineShopBuyOffer(shopId, offer.id);
        toast.info(`Declined ${offer.item.name}`);
      }
      await load();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Action failed');
    } finally {
      setBusy('');
    }
  };

  return (
    <div className={`glass-dark p-6 rounded-xl ${className}`} data-testid="shop-buy-offers-panel">
      <div className="flex items-center gap-2 mb-1">
        <Tag className="w-5 h-5 text-amber-300" />
        <h3 className="text-xl font-bold text-amber-200">Buy Offers</h3>
      </div>
      <p className="text-sm text-gray-400 mb-4">
        Players and NPCs bring wares to sell. Accept to pay from your treasury (then your purse) and re-list the item.
      </p>

      {/* Treasury widget */}
      <div className="bg-black/20 border border-amber-500/20 rounded-lg p-3 mb-4" data-testid="shop-treasury-widget">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm text-gray-300 flex items-center gap-1.5"><Wallet className="w-4 h-4 text-amber-300" /> Treasury</span>
          <span className="text-lg font-bold text-amber-200" data-testid="treasury-balance">{treasury.toLocaleString()}g</span>
        </div>
        <div className="flex gap-2">
          <Input
            type="number"
            min="1"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            placeholder="Amount"
            className="bg-black/30 border-amber-500/30 h-9"
            data-testid="treasury-amount-input"
          />
          <Button size="sm" onClick={() => move('deposit')} disabled={busy === 'deposit'} className="bg-emerald-700 hover:bg-emerald-800" data-testid="treasury-deposit-btn">
            <ArrowDownToLine className="w-3.5 h-3.5 mr-1" /> Deposit
          </Button>
          <Button size="sm" onClick={() => move('withdraw')} disabled={busy === 'withdraw'} variant="outline" className="border-amber-500/40 text-amber-200" data-testid="treasury-withdraw-btn">
            <ArrowUpFromLine className="w-3.5 h-3.5 mr-1" /> Withdraw
          </Button>
        </div>
      </div>

      {state === 'loading' && <p className="text-center text-gray-500 py-4" data-testid="buy-offers-loading">Checking the counter…</p>}
      {state === 'error' && (
        <div className="text-center py-4" data-testid="buy-offers-error">
          <p className="text-red-400 mb-2">Couldn&apos;t load offers.</p>
          <button onClick={load} className="text-amber-300 text-sm">Retry</button>
        </div>
      )}
      {state === 'ready' && (offers.length === 0 ? (
        <p className="text-sm text-gray-500 text-center py-4" data-testid="buy-offers-empty">
          No one is selling right now. Offers from players and NPCs will appear here.
        </p>
      ) : (
        <div className="space-y-2" data-testid="buy-offers-list">
          {offers.map((o) => (
            <div key={o.id} className="bg-black/20 border border-white/10 rounded-lg px-3 py-2" data-testid={`buy-offer-${o.id}`}>
              <div className="flex items-center gap-2 mb-1">
                <span className="text-white font-semibold flex-1 min-w-0 truncate">{o.item.name}</span>
                <span
                  className={`text-[10px] uppercase tracking-wide px-1.5 py-0.5 rounded ${o.seller_type === 'player' ? 'bg-purple-900/50 text-purple-200' : 'bg-gray-700/60 text-gray-300'}`}
                  data-testid={`offer-kind-${o.id}`}
                >
                  {o.seller_type === 'player' ? 'Player' : 'NPC'}
                </span>
                <span className="text-amber-300 font-bold">{o.proposed_price}g</span>
              </div>
              <p className="text-xs text-gray-400 mb-2">from {o.seller_name}{o.item.description ? ` · ${o.item.description}` : ''}</p>
              <div className="flex gap-2">
                <Button size="sm" onClick={() => resolve(o, 'accept')} disabled={busy === o.id} className="bg-emerald-700 hover:bg-emerald-800" data-testid={`accept-offer-${o.id}`}>
                  <Check className="w-3.5 h-3.5 mr-1" /> Accept
                </Button>
                <Button size="sm" variant="outline" onClick={() => resolve(o, 'decline')} disabled={busy === o.id} className="text-red-300 border-red-500/40 hover:bg-red-900/30" data-testid={`decline-offer-${o.id}`}>
                  <X className="w-3.5 h-3.5 mr-1" /> Decline
                </Button>
              </div>
            </div>
          ))}
        </div>
      ))}
    </div>
  );
};

export default ShopBuyOffersPanel;
