import React, { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { Coins, Loader2, Plus, ScrollText, TrendingUp } from 'lucide-react';
import api from '../utils/api';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { CompanySigil, SigilPicker } from '../components/CompanySigil';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../components/ui/dialog';

const NATIONS = [
  { slug: 'ammeonon',      label: 'Ammeonon' },
  { slug: 'dhor-kuldor',   label: 'Dhor-Kuldor' },
  { slug: 'selindori',     label: 'Selindori' },
  { slug: 'aigraels',      label: 'Aigraels' },
  { slug: 'veiled-realms', label: 'Veiled Realms' },
];

const CHARTER_FEE = 2500;

const TradeCompanies = () => {
  const navigate = useNavigate();
  const [companies, setCompanies] = useState([]);
  const [mine, setMine] = useState({ founded: [], shares_only: [] });
  const [characters, setCharacters] = useState([]);
  const [loading, setLoading] = useState(true);
  const [openCreate, setOpenCreate] = useState(false);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({
    name: '',
    motto: '',
    home_nation: 'ammeonon',
    founder_character_id: '',
    color: '#f59e0b',
    sigil: 'coins',
  });

  const refresh = async () => {
    try {
      const [aRes, mRes, cRes] = await Promise.all([
        api.get('/trade-companies').catch(() => ({ data: [] })),
        api.get('/trade-companies/mine').catch(() => ({ data: { founded: [], shares_only: [] } })),
        api.get('/characters').catch(() => ({ data: [] })),
      ]);
      setCompanies(Array.isArray(aRes.data) ? aRes.data : []);
      setMine(mRes.data || { founded: [], shares_only: [] });
      const chars = Array.isArray(cRes.data) ? cRes.data : (cRes.data?.characters || []);
      setCharacters(chars);
      setForm((f) => (
        !f.founder_character_id && chars[0]?.id ? { ...f, founder_character_id: chars[0].id } : f
      ));
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to load trade companies.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { refresh(); }, []);

  const myIds = useMemo(() => new Set([
    ...(mine.founded || []).map((c) => c.id),
    ...(mine.shares_only || []).map((c) => c.id),
  ]), [mine]);

  const handleCharter = async () => {
    if (form.name.trim().length < 3) { toast.error('Give the company a name.'); return; }
    if (!form.founder_character_id) { toast.error('Choose the character who will be your founder.'); return; }
    if (creating) return;
    setCreating(true);
    try {
      const r = await api.post('/trade-companies', {
        name: form.name.trim(),
        motto: form.motto.trim(),
        home_nation: form.home_nation,
        founder_character_id: form.founder_character_id,
        sigil: form.sigil || 'coins',
        color: form.color,
      });
      setOpenCreate(false);
      toast.success(`${r.data.name} chartered — ${CHARTER_FEE}g moved to the company treasury.`);
      navigate(`/trade-companies/${r.data.id}`);
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Could not charter the company.');
    } finally {
      setCreating(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center text-stone-300 bg-black">
        <Loader2 className="w-6 h-6 mr-2 animate-spin" />
        Opening the merchants&apos; register…
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-zinc-950 via-stone-950 to-black text-stone-100">
      <div className="max-w-5xl mx-auto px-6 py-12">
        <div className="mb-10 flex flex-wrap items-start justify-between gap-4">
          <div>
            <Link to="/dashboard" className="text-sm text-stone-400 hover:text-stone-200 transition" data-testid="trade-back-link">
              ← Dashboard
            </Link>
            <h1 className="mt-4 text-4xl sm:text-5xl font-bold tracking-tight flex items-center gap-3">
              <Coins className="w-10 h-10 text-amber-300" />
              <span>Trade Companies</span>
            </h1>
            <p className="mt-3 text-stone-400 max-w-3xl">
              Charter a merchant house. Draw goods from a city&apos;s workshops,
              carry them across the realm, and pocket the spread. Shareholders
              draw a dividend each week the ledger closes in the black.
            </p>
          </div>
          <Button
            onClick={() => setOpenCreate(true)}
            className="bg-gradient-to-r from-amber-700 to-stone-700 hover:from-amber-800 hover:to-stone-800 text-stone-100"
            data-testid="open-charter-company-btn"
          >
            <Plus className="w-4 h-4 mr-2" />
            Charter a Company ({CHARTER_FEE}g)
          </Button>
        </div>

        {(mine.founded.length > 0 || mine.shares_only.length > 0) && (
          <div className="mb-10">
            <h2 className="text-lg font-semibold mb-3 text-stone-200 flex items-center gap-2">
              <ScrollText className="w-4 h-4 text-amber-300" />
              Your Companies
            </h2>
            <div className="grid sm:grid-cols-2 gap-4" data-testid="my-companies-list">
              {mine.founded.map((c) => <CompanyCard key={c.id} company={c} role="founder" />)}
              {mine.shares_only.map((c) => <CompanyCard key={c.id} company={c} role="shareholder" />)}
            </div>
          </div>
        )}

        <div>
          <h2 className="text-lg font-semibold mb-3 text-stone-200 flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-stone-400" />
            Active on the Register
          </h2>
          {companies.length === 0 ? (
            <div className="rounded-xl border border-stone-700/60 bg-stone-950/40 p-8 text-center text-stone-400">
              No companies are trading yet. Charter the first!
            </div>
          ) : (
            <div className="grid sm:grid-cols-2 gap-4" data-testid="open-companies-list">
              {companies.map((c) => (
                <CompanyCard
                  key={c.id}
                  company={c}
                  role={myIds.has(c.id) ? 'holder' : null}
                />
              ))}
            </div>
          )}
        </div>
      </div>

      <Dialog open={openCreate} onOpenChange={setOpenCreate}>
        <DialogContent className="bg-stone-950 border-stone-700 text-stone-100 max-w-lg" data-testid="charter-company-dialog">
          <DialogHeader>
            <DialogTitle className="text-2xl text-amber-200">Charter a Trade Company</DialogTitle>
            <DialogDescription className="text-stone-400">
              {CHARTER_FEE}g moves from your wallet into the company treasury.
              You&apos;ll receive {CHARTER_FEE / 100} shares in return.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <div>
              <label className="text-sm text-stone-400">Company name</label>
              <Input
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                maxLength={100}
                placeholder="e.g. The Wymroost Salt & Silk Company"
                className="bg-stone-900 border-stone-700 text-stone-100"
                data-testid="company-name-input"
              />
            </div>
            <div>
              <label className="text-sm text-stone-400">Motto</label>
              <Input
                value={form.motto}
                onChange={(e) => setForm({ ...form, motto: e.target.value })}
                maxLength={200}
                placeholder="e.g. Wagons before glory."
                className="bg-stone-900 border-stone-700 text-stone-100"
                data-testid="company-motto-input"
              />
            </div>
            <div>
              <label className="text-sm text-stone-400">Home nation</label>
              <select
                value={form.home_nation}
                onChange={(e) => setForm({ ...form, home_nation: e.target.value })}
                className="w-full bg-stone-900 border border-stone-700 rounded-md px-3 py-2 text-stone-100"
                data-testid="company-nation-select"
              >
                {NATIONS.map((n) => (
                  <option key={n.slug} value={n.slug}>{n.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-sm text-stone-400">Founding character</label>
              {characters.length === 0 ? (
                <div className="text-sm text-stone-500 italic">
                  Create a character first — the founder must be one of yours.
                </div>
              ) : (
                <select
                  value={form.founder_character_id}
                  onChange={(e) => setForm({ ...form, founder_character_id: e.target.value })}
                  className="w-full bg-stone-900 border border-stone-700 rounded-md px-3 py-2 text-stone-100"
                  data-testid="company-founder-select"
                >
                  {characters.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name} — {c.race}{c.character_class ? ` (${c.character_class})` : ''}
                    </option>
                  ))}
                </select>
              )}
            </div>
            <div>
              <label className="text-sm text-stone-400">House sigil</label>
              <SigilPicker
                value={form.sigil}
                color={form.color}
                onChange={(s) => setForm({ ...form, sigil: s })}
              />
            </div>
            <div>
              <label className="text-sm text-stone-400">House colour</label>
              <input
                type="color"
                value={form.color}
                onChange={(e) => setForm({ ...form, color: e.target.value })}
                className="w-16 h-8 rounded border border-stone-700 bg-stone-900"
                data-testid="company-color-input"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setOpenCreate(false)} className="text-stone-300 hover:text-stone-100" data-testid="cancel-charter-btn">
              Cancel
            </Button>
            <Button
              onClick={handleCharter}
              disabled={creating || characters.length === 0}
              className="bg-gradient-to-r from-amber-700 to-stone-700 hover:from-amber-800 hover:to-stone-800 text-stone-100"
              data-testid="submit-charter-btn"
            >
              {creating
                ? (<><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Chartering…</>)
                : (<><Plus className="w-4 h-4 mr-2" /> Pay {CHARTER_FEE}g &amp; Charter</>)}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

const CompanyCard = ({ company, role }) => (
  <Link
    to={`/trade-companies/${company.id}`}
    className="block rounded-xl border border-stone-700/60 bg-stone-950/60 p-4 hover:bg-stone-900/60 hover:border-amber-700/40 transition"
    data-testid={`company-card-${company.id}`}
  >
    <div className="flex items-start justify-between gap-3 mb-2">
      <div className="flex items-start gap-3 min-w-0">
        <div
          className="shrink-0 mt-0.5 rounded-md border border-stone-700 bg-black/40 p-2"
          style={{ borderColor: company.color || '#f59e0b' }}
        >
          <CompanySigil sigil={company.sigil} color={company.color} className="w-6 h-6" />
        </div>
        <div className="min-w-0">
          <h3 className="text-lg font-semibold text-stone-100 line-clamp-1 flex items-center gap-2">
            <span className="truncate">{company.name}</span>
            {company.is_npc && (
              <span
                className="text-[10px] uppercase tracking-widest px-1.5 py-0.5 rounded border border-purple-400/40 bg-purple-950/40 text-purple-200"
                data-testid="npc-badge"
              >
                NPC
              </span>
            )}
          </h3>
          {company.motto && (
            <p className="text-xs italic text-stone-400 mt-0.5 line-clamp-1">&ldquo;{company.motto}&rdquo;</p>
          )}
        </div>
      </div>
    </div>
    <div className="text-xs text-stone-500 flex items-center gap-4 mt-3">
      <span>
        <Coins className="w-3 h-3 inline mr-1" />
        <span className="text-stone-200">{company.treasury?.toLocaleString?.() ?? company.treasury}g</span> treasury
      </span>
      <span className="text-stone-500">Home: {company.home_nation}</span>
      {role && (
        <span className="ml-auto text-amber-300/90 text-[10px] uppercase tracking-widest">
          {role}
        </span>
      )}
    </div>
  </Link>
);

export default TradeCompanies;
