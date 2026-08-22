import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useParams, useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import {
  ArrowLeft, Coins, Crown, Flame, Loader2, Plus, Send,
  Trash2, TrendingUp, Users, X,
} from 'lucide-react';
import api from '../utils/api';
import { useAuth } from '../contexts/AuthContext';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { CompanySigil } from '../components/CompanySigil';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../components/ui/dialog';

const NATIONS = ['ammeonon', 'dhor-kuldor', 'selindori', 'aigraels', 'veiled-realms'];

const TradeCompanyDetail = () => {
  const { companyId } = useParams();
  const navigate = useNavigate();
  const { currentUser } = useAuth();

  const [company, setCompany] = useState(null);
  const [routes, setRoutes] = useState([]);
  const [shareholders, setShareholders] = useState([]);
  const [activity, setActivity] = useState([]);
  const [ledgers, setLedgers] = useState([]);
  const [goods, setGoods] = useState([]);
  const [characters, setCharacters] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  const [routeOpen, setRouteOpen] = useState(false);
  const [routeForm, setRouteForm] = useState({
    source_nation: 'ammeonon',
    source_city_slug: '',
    dest_nation: 'ammeonon',
    dest_city_slug: '',
    good_slug: '',
    units_per_run: 20,
  });
  const [sourceCities, setSourceCities] = useState([]);
  const [destCities, setDestCities] = useState([]);

  const [investOpen, setInvestOpen] = useState(false);
  const [investForm, setInvestForm] = useState({ character_id: '', gold: 500 });

  const load = useCallback(async () => {
    try {
      const [cRes, rRes, sRes, aRes, lRes, gRes, chRes] = await Promise.all([
        api.get(`/trade-companies/${companyId}`),
        api.get(`/trade-companies/${companyId}/routes`).catch(() => ({ data: [] })),
        api.get(`/trade-companies/${companyId}/shareholders`).catch(() => ({ data: [] })),
        api.get(`/trade-companies/${companyId}/activity`).catch(() => ({ data: [] })),
        api.get(`/trade-companies/${companyId}/ledgers`).catch(() => ({ data: [] })),
        api.get('/economy/goods').catch(() => ({ data: [] })),
        api.get('/characters').catch(() => ({ data: [] })),
      ]);
      setCompany(cRes.data);
      setRoutes(Array.isArray(rRes.data) ? rRes.data : []);
      setShareholders(Array.isArray(sRes.data) ? sRes.data : []);
      setActivity(Array.isArray(aRes.data) ? aRes.data : []);
      setLedgers(Array.isArray(lRes.data) ? lRes.data : []);
      setGoods(Array.isArray(gRes.data) ? gRes.data : []);
      const chars = Array.isArray(chRes.data) ? chRes.data : (chRes.data?.characters || []);
      setCharacters(chars);
      setInvestForm((f) => (!f.character_id && chars[0]?.id ? { ...f, character_id: chars[0].id } : f));
    } catch (e) {
      if (e.response?.status === 404) {
        toast.error('Trade company not found.');
        navigate('/trade-companies');
      } else {
        toast.error(e.response?.data?.detail || 'Failed to load company.');
      }
    } finally {
      setLoading(false);
    }
  }, [companyId, navigate]);

  useEffect(() => { load(); }, [load]);

  // Cities dropdowns are keyed to the picked nation
  useEffect(() => {
    (async () => {
      try {
        const r = await api.get(`/cities/${routeForm.source_nation}`);
        const cities = Array.isArray(r.data) ? r.data : [];
        setSourceCities(cities);
        setRouteForm((f) => (
          !f.source_city_slug && cities[0]?.slug ? { ...f, source_city_slug: cities[0].slug } : f
        ));
      } catch { setSourceCities([]); }
    })();
  }, [routeForm.source_nation]);

  useEffect(() => {
    (async () => {
      try {
        const r = await api.get(`/cities/${routeForm.dest_nation}`);
        const cities = Array.isArray(r.data) ? r.data : [];
        setDestCities(cities);
        setRouteForm((f) => (
          !f.dest_city_slug && cities[0]?.slug ? { ...f, dest_city_slug: cities[0].slug } : f
        ));
      } catch { setDestCities([]); }
    })();
  }, [routeForm.dest_nation]);

  const isFounder = !!company && company.founder_user_id === currentUser?.id;
  const myShares = useMemo(
    () => shareholders.find((s) => s.user_id === currentUser?.id)?.shares || 0,
    [shareholders, currentUser],
  );
  const totalShares = useMemo(
    () => shareholders.reduce((sum, s) => sum + (s.shares || 0), 0),
    [shareholders],
  );

  const doAddRoute = async () => {
    if (!routeForm.source_city_slug || !routeForm.dest_city_slug || !routeForm.good_slug) {
      toast.error('Pick a source, a destination and a good.'); return;
    }
    if (routeForm.source_nation === routeForm.dest_nation && routeForm.source_city_slug === routeForm.dest_city_slug) {
      toast.error('Source and destination must differ.'); return;
    }
    setBusy(true);
    try {
      await api.post(`/trade-companies/${companyId}/routes`, routeForm);
      setRouteOpen(false);
      toast.success('Route opened.');
      load();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Could not add route.');
    } finally {
      setBusy(false);
    }
  };

  const doToggleRoute = async (rid) => {
    try {
      await api.post(`/trade-companies/${companyId}/routes/${rid}/toggle`);
      load();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Could not toggle route.');
    }
  };

  const doDeleteRoute = async (rid) => {
    if (!window.confirm('Remove this route?')) return;
    try {
      await api.delete(`/trade-companies/${companyId}/routes/${rid}`);
      load();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Could not remove route.');
    }
  };

  const doInvest = async () => {
    if (!investForm.character_id) { toast.error('Choose a character.'); return; }
    if (investForm.gold < 100) { toast.error('Minimum investment is 100g.'); return; }
    setBusy(true);
    try {
      await api.post(`/trade-companies/${companyId}/invest`, {
        character_id: investForm.character_id,
        gold: Number(investForm.gold),
      });
      setInvestOpen(false);
      toast.success('Shares purchased.');
      load();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Could not buy shares.');
    } finally {
      setBusy(false);
    }
  };

  const doDissolve = async () => {
    if (!window.confirm('Dissolve the company? All shareholders will be refunded proportionally. This cannot be undone.')) return;
    setBusy(true);
    try {
      await api.post(`/trade-companies/${companyId}/dissolve`);
      toast.success('Company dissolved. Treasury refunded proportionally.');
      load();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Could not dissolve.');
    } finally {
      setBusy(false);
    }
  };

  if (loading || !company) {
    return (
      <div className="min-h-screen flex items-center justify-center text-stone-300 bg-black">
        <Loader2 className="w-6 h-6 mr-2 animate-spin" />
        Reading the ledger…
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-zinc-950 via-stone-950 to-black text-stone-100">
      <div className="max-w-5xl mx-auto px-6 py-10">
        <Link to="/trade-companies" className="text-sm text-stone-400 hover:text-stone-200 transition flex items-center gap-1" data-testid="company-back-link">
          <ArrowLeft className="w-4 h-4" /> All Trade Companies
        </Link>

        {/* Header */}
        <div className="mt-4 mb-8 rounded-xl border border-stone-700/60 bg-stone-950/60 p-6" style={{ borderTop: `4px solid ${company.color || '#f59e0b'}` }}>
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="flex items-start gap-4">
              <div
                className="shrink-0 rounded-md border-2 p-3 bg-black/40"
                style={{ borderColor: company.color || '#f59e0b' }}
              >
                <CompanySigil sigil={company.sigil} color={company.color} className="w-10 h-10" />
              </div>
              <div>
                <h1 className="text-3xl sm:text-4xl font-bold tracking-tight flex items-center gap-3 flex-wrap" data-testid="company-title">
                  {company.name}
                  {company.is_npc && (
                    <span className="text-[11px] uppercase tracking-widest px-2 py-1 rounded border border-purple-400/40 bg-purple-950/40 text-purple-200" data-testid="npc-badge">
                      NPC House
                    </span>
                  )}
                </h1>
                {company.motto && (
                  <p className="mt-2 text-stone-300 italic">&ldquo;{company.motto}&rdquo;</p>
                )}
                <div className="mt-3 text-xs text-stone-400 flex items-center gap-3 flex-wrap">
                  <span>Home: {company.home_nation}</span>
                  <span>·</span>
                  <span>Founded by <strong className="text-stone-200">{company.founder_character_name}</strong></span>
                  <span>·</span>
                  <span data-testid="company-status">{company.status}</span>
                </div>
              </div>
            </div>
            <div className="text-right">
              <div className="text-xs text-stone-400 uppercase tracking-widest">Treasury</div>
              <div className="text-2xl font-bold text-amber-300 flex items-center gap-1 justify-end" data-testid="company-treasury">
                <Coins className="w-5 h-5" />
                {company.treasury?.toLocaleString?.() ?? company.treasury}g
              </div>
              <div className="text-[10px] text-stone-500 mt-1">
                Lifetime: {company.lifetime_revenue?.toLocaleString?.()}g revenue · {company.lifetime_dividends_paid?.toLocaleString?.()}g dividends
              </div>
            </div>
          </div>

          <div className="mt-5 flex flex-wrap items-center gap-2">
            {company.status === 'active' && !isFounder && !company.is_npc && (
              <Button
                onClick={() => setInvestOpen(true)}
                className="bg-emerald-800 hover:bg-emerald-900 text-emerald-50"
                data-testid="invest-btn"
              >
                <Plus className="w-4 h-4 mr-2" />
                {myShares > 0 ? `Buy more shares (you hold ${myShares})` : 'Buy shares'}
              </Button>
            )}
            {company.status === 'active' && company.is_npc && (
              <span className="text-xs text-purple-300/80 italic">
                NPC houses do not accept outside investment.
              </span>
            )}
            {company.status === 'active' && isFounder && (
              <>
                <Button
                  onClick={() => setRouteOpen(true)}
                  className="bg-amber-700 hover:bg-amber-800 text-amber-50"
                  data-testid="add-route-btn"
                >
                  <Plus className="w-4 h-4 mr-2" /> Open Route
                </Button>
                <Button
                  onClick={doDissolve}
                  disabled={busy}
                  variant="outline"
                  className="border-stone-600 text-stone-200 hover:bg-stone-800"
                  data-testid="dissolve-btn"
                >
                  <Flame className="w-4 h-4 mr-2" /> Dissolve
                </Button>
              </>
            )}
          </div>
        </div>

        {/* Routes + Shareholders */}
        <div className="grid md:grid-cols-3 gap-4 mb-8">
          <div className="md:col-span-2 rounded-xl border border-stone-700/60 bg-stone-950/40 p-5" data-testid="routes-panel">
            <h2 className="text-sm uppercase tracking-widest text-stone-400 mb-3 flex items-center gap-2">
              <TrendingUp className="w-4 h-4" /> Routes ({routes.length}/8)
            </h2>
            {routes.length === 0 ? (
              <p className="text-sm text-stone-500 italic">
                {isFounder ? 'Open a route between two cities to start moving stock.' : 'No routes opened yet.'}
              </p>
            ) : (
              <div className="space-y-2">
                {routes.map((r) => (
                  <div
                    key={r.id}
                    className={`rounded-md border p-2.5 text-sm ${
                      r.is_active ? 'border-amber-500/30 bg-amber-950/10' : 'border-stone-800 bg-stone-950/40 opacity-60'
                    }`}
                    data-testid={`route-${r.id}`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <div className="min-w-0">
                        <div className="text-stone-100 truncate">
                          <strong className="text-amber-200">{r.good_slug.replace(/-/g, ' ')}</strong>
                          <span className="mx-2 text-stone-500">·</span>
                          {r.source_nation}:{r.source_city_slug}
                          <span className="mx-1 text-stone-500">→</span>
                          {r.dest_nation}:{r.dest_city_slug}
                        </div>
                        <div className="text-[11px] text-stone-500 mt-1">
                          {r.units_per_run} units/run · {r.runs_total} runs total
                          {r.last_run_result && (
                            <> · last +{r.last_run_result.profit}g</>
                          )}
                        </div>
                      </div>
                      {isFounder && company.status === 'active' && (
                        <div className="flex items-center gap-2 shrink-0">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => doToggleRoute(r.id)}
                            className="border-stone-600 text-stone-200 hover:bg-stone-800 h-7 px-2"
                            data-testid={`toggle-route-${r.id}`}
                          >
                            {r.is_active ? 'Pause' : 'Resume'}
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => doDeleteRoute(r.id)}
                            className="text-stone-400 hover:text-red-400 h-7 px-2"
                            data-testid={`delete-route-${r.id}`}
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </Button>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="rounded-xl border border-stone-700/60 bg-stone-950/40 p-5" data-testid="shareholders-panel">
            <h2 className="text-sm uppercase tracking-widest text-stone-400 mb-3 flex items-center gap-2">
              <Users className="w-4 h-4" /> Shareholders
            </h2>
            <div className="text-xs text-stone-500 mb-2">
              Total shares: <strong className="text-stone-200">{totalShares}</strong>
            </div>
            <div className="space-y-1.5">
              {shareholders.map((s) => {
                const pct = totalShares ? Math.round((s.shares / totalShares) * 100) : 0;
                const isMe = s.user_id === currentUser?.id;
                return (
                  <div
                    key={s.id}
                    className={`rounded-md border p-2 text-xs ${
                      isMe ? 'border-amber-500/40 bg-amber-950/20' : 'border-stone-800 bg-stone-950/40'
                    }`}
                    data-testid={`shareholder-${s.user_id}`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-stone-200 truncate flex items-center gap-1">
                        {s.user_id === company.founder_user_id && <Crown className="w-3 h-3 text-amber-300 shrink-0" />}
                        <span>{isMe ? 'You' : `Trader-${s.user_id.slice(0, 6)}`}</span>
                      </span>
                      <span className="text-amber-200">{s.shares} ({pct}%)</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Ledgers */}
        {ledgers.length > 0 && (
          <div className="rounded-xl border border-stone-700/60 bg-stone-950/40 p-5 mb-8" data-testid="ledgers-panel">
            <h2 className="text-sm uppercase tracking-widest text-stone-400 mb-3">Weekly Ledgers</h2>
            <div className="space-y-2">
              {ledgers.map((l) => (
                <div key={l.id} className="rounded-md border border-stone-800 bg-stone-950/40 p-3 text-sm" data-testid={`ledger-${l.id}`}>
                  <div className="flex items-center justify-between text-stone-300">
                    <span>{new Date(l.period_start).toLocaleDateString()} — {new Date(l.period_end).toLocaleDateString()}</span>
                    <span className={l.net_profit >= 0 ? 'text-emerald-300' : 'text-red-400'}>
                      {l.net_profit >= 0 ? '+' : ''}{l.net_profit}g net
                    </span>
                  </div>
                  <div className="text-xs text-stone-500 mt-1">
                    Revenue {l.revenue}g · Costs {l.costs}g · Dividend {l.per_share_dividend}g/share ({l.dividends_paid}g paid)
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Activity */}
        {activity.length > 0 && (
          <div className="rounded-xl border border-stone-700/60 bg-stone-950/40 p-5 mb-8" data-testid="activity-panel">
            <h2 className="text-sm uppercase tracking-widest text-stone-400 mb-3">Recent Activity</h2>
            <div className="space-y-1.5 max-h-80 overflow-y-auto">
              {activity.map((a) => (
                <div key={a.id} className="rounded-md border border-stone-800 bg-stone-950/40 p-2 text-xs text-stone-300" data-testid={`activity-${a.id}`}>
                  <div className="flex items-center justify-between">
                    <span className="text-amber-200 uppercase tracking-widest">{a.kind}</span>
                    <span className="text-stone-500">{new Date(a.at).toLocaleString()}</span>
                  </div>
                  <div className="mt-1 text-stone-400">
                    {a.kind === 'route_run' && a.meta && (
                      <>
                        {a.meta.units} × {a.meta.good_slug} — {a.meta.profit >= 0 ? <span className="text-emerald-300">+{a.meta.profit}g</span> : <span className="text-red-400">{a.meta.profit}g</span>}
                      </>
                    )}
                    {a.kind === 'invest' && a.meta && (
                      <>+{a.meta.gold}g invested for {a.meta.shares} shares</>
                    )}
                    {a.kind === 'dividend' && a.meta && (
                      <>Dividend paid: {a.meta.paid}g ({a.meta.per_share}g/share to {a.meta.shareholders} holders)</>
                    )}
                    {a.kind === 'charter' && (<>Company chartered.</>)}
                    {a.kind === 'dissolve' && a.meta && (
                      <>Dissolved — refunded {a.meta.total_refunded}g to shareholders.</>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Route dialog */}
      <Dialog open={routeOpen} onOpenChange={setRouteOpen}>
        <DialogContent className="bg-stone-950 border-stone-700 text-stone-100 max-w-lg" data-testid="add-route-dialog">
          <DialogHeader>
            <DialogTitle className="text-xl text-amber-200">Open a Trade Route</DialogTitle>
            <DialogDescription className="text-stone-400">
              Every 6-hour tick, this route tries to buy {routeForm.units_per_run || 20} units
              from the source city&apos;s stockpile and sell in the destination.
            </DialogDescription>
          </DialogHeader>
          <div className="grid grid-cols-2 gap-3">
            <div className="col-span-2">
              <label className="text-xs text-stone-400">Good</label>
              <select
                value={routeForm.good_slug}
                onChange={(e) => setRouteForm({ ...routeForm, good_slug: e.target.value })}
                className="w-full bg-stone-900 border border-stone-700 rounded-md px-3 py-2 text-stone-100"
                data-testid="route-good-select"
              >
                <option value="">— pick a good —</option>
                {goods.map((g) => (
                  <option key={g.slug} value={g.slug}>{g.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs text-stone-400">Source nation</label>
              <select
                value={routeForm.source_nation}
                onChange={(e) => setRouteForm({ ...routeForm, source_nation: e.target.value, source_city_slug: '' })}
                className="w-full bg-stone-900 border border-stone-700 rounded-md px-3 py-2 text-stone-100"
                data-testid="route-source-nation"
              >
                {NATIONS.map((n) => <option key={n} value={n}>{n}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs text-stone-400">Source city</label>
              <select
                value={routeForm.source_city_slug}
                onChange={(e) => setRouteForm({ ...routeForm, source_city_slug: e.target.value })}
                className="w-full bg-stone-900 border border-stone-700 rounded-md px-3 py-2 text-stone-100"
                data-testid="route-source-city"
              >
                <option value="">— pick a city —</option>
                {sourceCities.map((c) => <option key={c.slug} value={c.slug}>{c.name}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs text-stone-400">Destination nation</label>
              <select
                value={routeForm.dest_nation}
                onChange={(e) => setRouteForm({ ...routeForm, dest_nation: e.target.value, dest_city_slug: '' })}
                className="w-full bg-stone-900 border border-stone-700 rounded-md px-3 py-2 text-stone-100"
                data-testid="route-dest-nation"
              >
                {NATIONS.map((n) => <option key={n} value={n}>{n}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs text-stone-400">Destination city</label>
              <select
                value={routeForm.dest_city_slug}
                onChange={(e) => setRouteForm({ ...routeForm, dest_city_slug: e.target.value })}
                className="w-full bg-stone-900 border border-stone-700 rounded-md px-3 py-2 text-stone-100"
                data-testid="route-dest-city"
              >
                <option value="">— pick a city —</option>
                {destCities.map((c) => <option key={c.slug} value={c.slug}>{c.name}</option>)}
              </select>
            </div>
            <div className="col-span-2">
              <label className="text-xs text-stone-400">Units per run (1-200)</label>
              <Input
                type="number"
                min={1}
                max={200}
                value={routeForm.units_per_run}
                onChange={(e) => setRouteForm({ ...routeForm, units_per_run: Number(e.target.value) || 20 })}
                className="bg-stone-900 border-stone-700 text-stone-100"
                data-testid="route-units-input"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setRouteOpen(false)} className="text-stone-300 hover:text-stone-100" data-testid="cancel-route-btn">
              <X className="w-4 h-4 mr-2" /> Cancel
            </Button>
            <Button
              onClick={doAddRoute}
              disabled={busy}
              className="bg-amber-700 hover:bg-amber-800 text-amber-50"
              data-testid="submit-route-btn"
            >
              {busy
                ? (<><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Opening…</>)
                : (<><Send className="w-4 h-4 mr-2" /> Open Route</>)}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Invest dialog */}
      <Dialog open={investOpen} onOpenChange={setInvestOpen}>
        <DialogContent className="bg-stone-950 border-stone-700 text-stone-100" data-testid="invest-dialog">
          <DialogHeader>
            <DialogTitle className="text-xl text-emerald-200">Buy Shares</DialogTitle>
            <DialogDescription className="text-stone-400">
              100g per share. Shares earn a weekly dividend when the ledger closes profitable.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <div>
              <label className="text-xs text-stone-400">Character</label>
              {characters.length === 0 ? (
                <div className="text-sm text-stone-500 italic">Create a character first.</div>
              ) : (
                <select
                  value={investForm.character_id}
                  onChange={(e) => setInvestForm({ ...investForm, character_id: e.target.value })}
                  className="w-full bg-stone-900 border border-stone-700 rounded-md px-3 py-2 text-stone-100"
                  data-testid="invest-character-select"
                >
                  {characters.map((c) => (
                    <option key={c.id} value={c.id}>{c.name} — {c.race}</option>
                  ))}
                </select>
              )}
            </div>
            <div>
              <label className="text-xs text-stone-400">Gold to invest (min 100)</label>
              <Input
                type="number"
                min={100}
                step={100}
                value={investForm.gold}
                onChange={(e) => setInvestForm({ ...investForm, gold: Number(e.target.value) || 100 })}
                className="bg-stone-900 border-stone-700 text-stone-100"
                data-testid="invest-gold-input"
              />
              <div className="text-xs text-stone-500 mt-1">
                = {Math.floor((investForm.gold || 0) / 100)} shares
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setInvestOpen(false)} className="text-stone-300 hover:text-stone-100" data-testid="cancel-invest-btn">
              Cancel
            </Button>
            <Button
              onClick={doInvest}
              disabled={busy || characters.length === 0}
              className="bg-emerald-800 hover:bg-emerald-900 text-emerald-50"
              data-testid="submit-invest-btn"
            >
              {busy
                ? (<><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Buying…</>)
                : (<><Coins className="w-4 h-4 mr-2" /> Buy Shares</>)}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default TradeCompanyDetail;
