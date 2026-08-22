import React, { useState } from 'react';
import { toast } from 'sonner';
import { Database, AlertCircle, Loader2, CheckCircle2, XCircle, Shield, Hammer, Crown, Sparkles, Trash2, Image as ImageIcon, Wrench } from 'lucide-react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Progress } from '../ui/progress';
import { Switch } from '../ui/switch';
import { adminSeedStarterFactions, adminSeedMasterNpcs, adminSeedRoyalsAndNobles, adminPopulateCitiesAi, adminCleanupGeoData, adminImageBatchSurvey, adminImageBatchStatus, adminImageBatchGenerate, adminImageBatchStop, adminSeedTitanSacredSites, adminSeedDhorKuldorCanon, adminSeedAllRealmsCanon, adminRepairWorldLocations } from '../../utils/api';

/**
 * Database Seed Panel (admin-only) — current world data counts +
 * background seed button + live progress.
 */
const DatabaseSeedPanel = ({ dbStatus, seedStatus, seeding, withImages, onToggleWithImages, onSeed }) => {
  const [factionSeeding, setFactionSeeding] = useState(false);
  const [factionResult, setFactionResult] = useState(null);
  const [mastersSeeding, setMastersSeeding] = useState(false);
  const [mastersResult, setMastersResult] = useState(null);
  const [royalsSeeding, setRoyalsSeeding] = useState(false);
  const [royalsResult, setRoyalsResult] = useState(null);
  const [populateCount, setPopulateCount] = useState(5);
  const [populating, setPopulating] = useState(false);
  const [populateResult, setPopulateResult] = useState(null);
  const [cleanupBusy, setCleanupBusy] = useState(false);
  const [cleanupResult, setCleanupResult] = useState(null);
  const [imgSurvey, setImgSurvey] = useState(null);
  const [imgStatus, setImgStatus] = useState(null);
  const [imgAutoContinue, setImgAutoContinue] = useState(false);
  const [titanBusy, setTitanBusy] = useState(false);
  const [titanResult, setTitanResult] = useState(null);
  const [kuldorBusy, setKuldorBusy] = useState(false);
  const [kuldorResult, setKuldorResult] = useState(null);
  const [realmsBusy, setRealmsBusy] = useState(false);
  const [realmsResult, setRealmsResult] = useState(null);
  const [repairBusy, setRepairBusy] = useState(false);
  const [repairResult, setRepairResult] = useState(null);

  const handleRepairWorld = async () => {
    if (repairBusy) return;
    setRepairBusy(true);
    setRepairResult(null);
    try {
      const r = await adminRepairWorldLocations();
      setRepairResult(r.data);
      const filled = r.data?.baseline_locations?.cities_filled || 0;
      const made = r.data?.baseline_locations?.locations_created || 0;
      const slug = r.data?.nation_slug?.fixed ? ' · nation slug fixed' : '';
      toast.success(`World repaired — ${filled} empty cities filled, ${made} locations added${slug}.`);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'World repair failed.');
    } finally {
      setRepairBusy(false);
    }
  };

  const handleSeedFactions = async () => {
    if (factionSeeding) return;
    setFactionSeeding(true);
    setFactionResult(null);
    try {
      const r = await adminSeedStarterFactions();
      setFactionResult(r.data);
      const ins = r.data.inserted?.length || 0;
      const upd = r.data.updated?.length || 0;
      toast.success(`Starter factions seeded — ${ins} new, ${upd} refreshed.`);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to seed factions.');
    } finally {
      setFactionSeeding(false);
    }
  };

  const handleSeedMasters = async () => {
    if (mastersSeeding) return;
    setMastersSeeding(true);
    setMastersResult(null);
    try {
      const r = await adminSeedMasterNpcs();
      setMastersResult(r.data);
      toast.success(`Master NPCs seeded — ${r.data.created} created, ${r.data.skipped} skipped (${r.data.total_after} total masters).`);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to seed master NPCs.');
    } finally {
      setMastersSeeding(false);
    }
  };

  const handleSeedRoyals = async () => {
    if (royalsSeeding) return;
    setRoyalsSeeding(true);
    setRoyalsResult(null);
    try {
      const r = await adminSeedRoyalsAndNobles();
      setRoyalsResult(r.data);
      toast.success(`Royals & nobles seeded — ${r.data.created} created, ${r.data.skipped} skipped (${r.data.total_after} total).`);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to seed royals & nobles.');
    } finally {
      setRoyalsSeeding(false);
    }
  };

  const handlePopulateCities = async () => {
    if (populating) return;
    setPopulating(true);
    setPopulateResult(null);
    try {
      const r = await adminPopulateCitiesAi(populateCount);
      setPopulateResult(r.data);
      toast.success(`AI-populated ${r.data.processed} cities — ${r.data.inserted} NPCs added.`);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to populate cities.');
    } finally {
      setPopulating(false);
    }
  };

  const handleCleanupGeoData = async () => {
    if (cleanupBusy) return;
    if (!window.confirm('Dedupe duplicate cities & locations and add unique indexes? This rewrites the geo data — safe but not reversible.')) return;
    setCleanupBusy(true);
    setCleanupResult(null);
    try {
      const r = await adminCleanupGeoData();
      setCleanupResult(r.data);
      const loc = r.data.locations || {};
      const city = r.data.cities || {};
      toast.success(`Cleanup done — locations: ${loc.rows_deleted || 0} removed (${loc.total_before || 0}→${loc.total_after || 0}); cities: ${city.rows_deleted || 0} removed.`);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Cleanup failed.');
    } finally {
      setCleanupBusy(false);
    }
  };

  const refreshImageState = React.useCallback(async () => {
    try {
      const [s, st] = await Promise.all([adminImageBatchSurvey(), adminImageBatchStatus()]);
      setImgSurvey(s.data);
      setImgStatus(st.data);
    } catch {
      // silently ignore — panel just won't update
    }
  }, []);

  React.useEffect(() => {
    refreshImageState();
    const t = setInterval(refreshImageState, 5000);
    return () => clearInterval(t);
  }, [refreshImageState]);

  const handleStartImageBatch = async ({ autoContinue = false } = {}) => {
    try {
      const r = await adminImageBatchGenerate({ autoContinue });
      if (r.data?.started) {
        toast.success(autoContinue
          ? 'Image batch started — server will run until every missing image is generated. Safe to close this tab.'
          : `Image batch started — generating up to ${r.data.state?.target_count || 25} images in the background.`);
      } else {
        toast.info(r.data?.reason || 'A batch is already in progress.');
      }
      refreshImageState();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Could not start image batch.');
    }
  };

  const handleStopImageBatch = async () => {
    try {
      const r = await adminImageBatchStop();
      if (r.data?.stopped) {
        toast.success('Stop requested — the loop will halt after the current image.');
      } else {
        toast.info(r.data?.reason || 'No batch is currently running.');
      }
      refreshImageState();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Could not stop image batch.');
    }
  };

  // Auto-continue: when the toggle is on AND there are missing images AND
  // no batch is running, kick off a server-side run-until-done batch.
  React.useEffect(() => {
    if (!imgAutoContinue) return;
    if (imgStatus?.is_running) return;
    if (!imgSurvey || imgSurvey.total_missing <= 0) return;
    const t = setTimeout(() => { handleStartImageBatch({ autoContinue: true }); }, 1500);
    return () => clearTimeout(t);
  }, [imgAutoContinue, imgStatus?.is_running, imgStatus?.last_completed_at, imgSurvey?.total_missing]);

  const handleSeedTitanSites = async () => {
    if (titanBusy) return;
    setTitanBusy(true);
    setTitanResult(null);
    try {
      const r = await adminSeedTitanSacredSites();
      setTitanResult(r.data);
      toast.success(`Titan sacred sites — ${r.data.annotated} new · ${r.data.already_annotated} previously done · ${r.data.not_found_count} slugs missing from DB.`);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Titan site seed failed.');
    } finally {
      setTitanBusy(false);
    }
  };

  const handleSeedDhorKuldorCanon = async () => {
    if (kuldorBusy) return;
    setKuldorBusy(true);
    setKuldorResult(null);
    try {
      const r = await adminSeedDhorKuldorCanon();
      setKuldorResult(r.data);
      const ins = r.data.cities?.inserted?.length || 0;
      const upd = r.data.cities?.updated?.length || 0;
      toast.success(`Dhor-Kuldor canon — ${ins} new hold-capitals · ${upd} refreshed.`);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Canon seed failed.');
    } finally {
      setKuldorBusy(false);
    }
  };

  const handleSeedAllRealms = async () => {
    if (realmsBusy) return;
    setRealmsBusy(true);
    setRealmsResult(null);
    try {
      const r = await adminSeedAllRealmsCanon();
      setRealmsResult(r.data);
      toast.success(`Full realms canon — ${r.data.total_inserted} new · ${r.data.total_updated} refreshed across ${Object.keys(r.data.by_realm || {}).length} realms.`);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Full realms seed failed.');
    } finally {
      setRealmsBusy(false);
    }
  };


  return (
  <div className="glass-dark p-8 rounded-xl">
    <div className="flex items-center gap-3 mb-6">
      <Database className="w-8 h-8 text-purple-400" />
      <div>
        <h2 className="text-2xl font-bold text-white">Database Management</h2>
        <p className="text-gray-400">Seed and manage your world data</p>
      </div>
    </div>

    {/* Repair World — one-click fix for missing city locations + nation slug */}
    <div className="bg-emerald-950/30 border border-emerald-600/40 rounded-lg p-6 mb-6" data-testid="repair-world-panel">
      <div className="flex items-center gap-3 mb-3">
        <Wrench className="w-6 h-6 text-emerald-300" />
        <h3 className="text-lg font-bold text-emerald-200">Repair World (Fix Missing Locations)</h3>
      </div>
      <p className="text-gray-400 mb-4">
        One-click fix for the &ldquo;this city has no locations yet&rdquo; issue. Normalises the
        <code className="text-emerald-300 mx-1">dhor-khuldor → dhor-kuldor</code> nation slug and
        seeds a starter set of RP locations (Town Square, Tavern, Market Row, Gate) for every
        city that currently has none. Purely additive &amp; idempotent — safe to run any time,
        never touches hand-authored locations.
      </p>
      <Button
        onClick={handleRepairWorld}
        disabled={repairBusy}
        className="bg-gradient-to-r from-emerald-700 to-teal-700 hover:from-emerald-800 hover:to-teal-800 text-base px-6 py-5"
        data-testid="repair-world-btn"
      >
        {repairBusy ? (
          <><Loader2 className="w-5 h-5 mr-2 animate-spin" />Repairing the world…</>
        ) : (
          <><Wrench className="w-5 h-5 mr-2" />Repair World Locations</>
        )}
      </Button>
      {repairResult && (
        <div className="mt-4 bg-black/40 border border-emerald-500/30 rounded-md p-4 text-sm space-y-1" data-testid="repair-world-result">
          <p className="text-emerald-200">
            <CheckCircle2 className="w-4 h-4 inline mr-1" />
            <strong>{repairResult.baseline_locations?.cities_filled || 0}</strong> empty cities filled ·{' '}
            <strong>{repairResult.baseline_locations?.locations_created || 0}</strong> locations created
          </p>
          <p className="text-emerald-200/80 text-xs">
            Nation slug: {repairResult.nation_slug?.fixed
              ? (repairResult.nation_slug?.note || 'fixed')
              : (repairResult.nation_slug?.reason || 'already canonical')}
          </p>
        </div>
      )}
    </div>

    {/* Current Status */}
    <div className="bg-black/30 rounded-lg p-6 mb-6" data-testid="db-status-block">
      <h3 className="text-lg font-bold text-purple-300 mb-4">Current Database Status</h3>
      {dbStatus ? (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-purple-600/20 rounded-lg p-4 text-center">
            <p className="text-3xl font-bold text-purple-400">{dbStatus.nations}</p>
            <p className="text-sm text-gray-400">Nations</p>
          </div>
          <div className="bg-blue-600/20 rounded-lg p-4 text-center">
            <p className="text-3xl font-bold text-blue-400">{dbStatus.cities}</p>
            <p className="text-sm text-gray-400">Cities/Towns</p>
          </div>
          <div className="bg-green-600/20 rounded-lg p-4 text-center">
            <p className="text-3xl font-bold text-green-400">{dbStatus.locations}</p>
            <p className="text-sm text-gray-400">Locations</p>
          </div>
          <div className="bg-orange-600/20 rounded-lg p-4 text-center">
            <p className="text-3xl font-bold text-orange-400">{dbStatus.users}</p>
            <p className="text-sm text-gray-400">Users</p>
          </div>
        </div>
      ) : (
        <p className="text-gray-400">Loading status...</p>
      )}
    </div>

    {/* Seed Database Section */}
    <div className="bg-black/30 rounded-lg p-6">
      <h3 className="text-lg font-bold text-purple-300 mb-2">Seed Database</h3>
      <p className="text-gray-400 mb-4">
        If your database is empty (shows 0 nations, cities, locations), click the button below
        to populate it with all the world data including nations, cities, towns, and locations.
      </p>

      {dbStatus?.is_empty && (
        <div className="bg-yellow-600/20 border border-yellow-600/40 rounded-lg p-4 mb-4">
          <p className="text-yellow-400 flex items-center gap-2">
            <AlertCircle className="w-5 h-5" />
            Your database appears to be empty. Click the button below to populate it.
          </p>
        </div>
      )}

      {/* With-images toggle */}
      <div className="flex items-center justify-between bg-black/30 border border-purple-500/20 rounded-lg p-4 mb-4">
        <div>
          <p className="text-sm font-medium text-purple-200">Generate AI Images</p>
          <p className="text-xs text-gray-500">Slower but creates illustrations for each nation, city, and location.</p>
        </div>
        <Switch
          checked={withImages}
          onCheckedChange={onToggleWithImages}
          disabled={seeding}
          data-testid="seed-with-images-toggle"
        />
      </div>

      <Button
        onClick={onSeed}
        disabled={seeding}
        className="bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-lg px-8 py-6"
        data-testid="seed-database-btn"
      >
        {seeding ? (
          <>
            <Loader2 className="w-5 h-5 mr-2 animate-spin" />
            Seeding in background…
          </>
        ) : (
          <>
            <Database className="w-5 h-5 mr-2" />
            Seed Database with World Data
          </>
        )}
      </Button>

      {/* Live progress panel */}
      {seedStatus && seedStatus.status !== 'idle' && (
        <div className="mt-6 bg-black/40 border border-purple-500/30 rounded-lg p-4" data-testid="seed-progress-panel">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              {seedStatus.status === 'running' && <Loader2 className="w-4 h-4 animate-spin text-purple-300" />}
              {seedStatus.status === 'completed' && <CheckCircle2 className="w-4 h-4 text-green-400" />}
              {seedStatus.status === 'failed' && <XCircle className="w-4 h-4 text-red-400" />}
              <span className="text-sm font-semibold text-purple-200 capitalize" data-testid="seed-status-label">
                {seedStatus.status}
                {seedStatus.phase ? ` · ${seedStatus.phase}` : ''}
              </span>
            </div>
            <span className="text-xs text-gray-400" data-testid="seed-progress-percent">{seedStatus.progress || 0}%</span>
          </div>
          <Progress value={seedStatus.progress || 0} className="h-2" />
          {seedStatus.message && (
            <p className="text-xs text-gray-400 mt-2" data-testid="seed-progress-message">{seedStatus.message}</p>
          )}
          {seedStatus.results && (
            <div className="grid grid-cols-3 gap-2 mt-3 text-center">
              <div className="bg-purple-600/20 rounded p-2">
                <p className="text-lg font-bold text-purple-300">{seedStatus.results.nations}</p>
                <p className="text-[10px] uppercase text-gray-400">Nations</p>
              </div>
              <div className="bg-blue-600/20 rounded p-2">
                <p className="text-lg font-bold text-blue-300">{seedStatus.results.cities}</p>
                <p className="text-[10px] uppercase text-gray-400">Cities</p>
              </div>
              <div className="bg-green-600/20 rounded p-2">
                <p className="text-lg font-bold text-green-300">{seedStatus.results.locations}</p>
                <p className="text-[10px] uppercase text-gray-400">Locations</p>
              </div>
            </div>
          )}
          {seedStatus.error && (
            <p className="text-xs text-red-400 mt-2" data-testid="seed-error">{seedStatus.error}</p>
          )}
        </div>
      )}

      <p className="text-xs text-gray-500 mt-4">
        Note: This will only add new data. Existing data will not be duplicated or overwritten.
        Seeding runs in the background — you can close this panel and come back later.
      </p>
    </div>

    {/* Starter Factions — separate seeder for the 6 canonical factions */}
    <div className="bg-black/30 rounded-lg p-6 mt-6">
      <div className="flex items-center gap-3 mb-3">
        <Shield className="w-6 h-6 text-amber-400" />
        <h3 className="text-lg font-bold text-amber-300">Seed Starter Factions</h3>
      </div>
      <p className="text-gray-400 mb-4">
        Idempotent — inserts the 6 canonical factions (Ardent Legion, Forsaken Court,
        Elderborn Alliance, Forgemaster&apos;s Guild, High King&apos;s Court, Loremaster&apos;s Guild)
        if missing, or refreshes their copy if already present. Also seeds each one
        with 6 founding NPC members (2 officers + 4 sworn) and an initial coffer of
        1,000,000 gold. Existing memberships, NPC rosters, and full coffers are untouched.
      </p>

      <Button
        onClick={handleSeedFactions}
        disabled={factionSeeding}
        className="bg-gradient-to-r from-amber-600 to-orange-600 hover:from-amber-700 hover:to-orange-700"
        data-testid="seed-factions-btn"
      >
        {factionSeeding ? (
          <>
            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            Seeding starter factions…
          </>
        ) : (
          <>
            <Shield className="w-4 h-4 mr-2" />
            Seed Starter Factions
          </>
        )}
      </Button>

      {factionResult && (
        <div className="mt-4 bg-black/40 border border-amber-500/30 rounded-lg p-4" data-testid="seed-factions-result">
          <p className="text-sm text-amber-200">
            <CheckCircle2 className="w-4 h-4 inline mr-1" />
            Done. {factionResult.inserted?.length || 0} inserted, {factionResult.updated?.length || 0} refreshed
            ({factionResult.total} total).
          </p>
          {factionResult.inserted?.length > 0 && (
            <p className="text-xs text-gray-400 mt-2">New: {factionResult.inserted.join(', ')}</p>
          )}
        </div>
      )}
    </div>

    {/* Master NPCs — 80-strong roster of master mentors for the Apprenticeships system */}
    <div className="bg-black/30 rounded-lg p-6 mt-6">
      <div className="flex items-center gap-3 mb-3">
        <Hammer className="w-6 h-6 text-amber-400" />
        <h3 className="text-lg font-bold text-amber-300">Seed Master NPCs</h3>
      </div>
      <p className="text-gray-400 mb-4">
        Idempotent — seeds the 80 canonical master NPCs (16 crafts × 5 nations) used
        by the Apprenticeships system. Each master has lore-flavoured name, race,
        location, quirk, and craft tag. Skips any (name, nation) pair already
        present. Run this once per environment (preview / production) to populate
        mentors for the +New apprenticeship picker.
      </p>

      <Button
        onClick={handleSeedMasters}
        disabled={mastersSeeding}
        className="bg-gradient-to-r from-amber-600 to-yellow-600 hover:from-amber-700 hover:to-yellow-700"
        data-testid="seed-masters-btn"
      >
        {mastersSeeding ? (
          <>
            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            Seeding master NPCs…
          </>
        ) : (
          <>
            <Hammer className="w-4 h-4 mr-2" />
            Seed Master NPCs
          </>
        )}
      </Button>

      {mastersResult && (
        <div className="mt-4 bg-black/40 border border-amber-500/30 rounded-lg p-4" data-testid="seed-masters-result">
          <p className="text-sm text-amber-200">
            <CheckCircle2 className="w-4 h-4 inline mr-1" />
            Done. {mastersResult.created} created, {mastersResult.skipped} skipped
            ({mastersResult.total_after} total masters now in the realm).
          </p>
        </div>
      )}
    </div>

    {/* Royals & Capital Nobles — hand-authored, 5 royals + 15 nobles */}
    <div className="bg-black/30 rounded-lg p-6 mt-6">
      <div className="flex items-center gap-3 mb-3">
        <Crown className="w-6 h-6 text-purple-300" />
        <h3 className="text-lg font-bold text-purple-200">Seed Royals &amp; Capital Nobles</h3>
      </div>
      <p className="text-gray-400 mb-4">
        Idempotent — seeds 5 hand-authored royals (one per nation) and 15 nobles
        (three per capital city: Wymroost, Aurelion Spires, Karak Vorn, Astra&apos;Lun,
        Niratha). Each is canon, with a personality, quirk, and motivation that
        points at real in-world tension. Skips any (name, nation) already present.
      </p>

      <Button
        onClick={handleSeedRoyals}
        disabled={royalsSeeding}
        className="bg-gradient-to-r from-purple-700 to-indigo-700 hover:from-purple-800 hover:to-indigo-800"
        data-testid="seed-royals-btn"
      >
        {royalsSeeding ? (
          <>
            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            Seeding royals &amp; nobles…
          </>
        ) : (
          <>
            <Crown className="w-4 h-4 mr-2" />
            Seed Royals &amp; Nobles
          </>
        )}
      </Button>

      {royalsResult && (
        <div className="mt-4 bg-black/40 border border-purple-500/30 rounded-lg p-4" data-testid="seed-royals-result">
          <p className="text-sm text-purple-200">
            <CheckCircle2 className="w-4 h-4 inline mr-1" />
            Done. {royalsResult.created} created, {royalsResult.skipped} skipped
            ({royalsResult.total_after} total royals+nobles in the realm).
          </p>
        </div>
      )}
    </div>

    {/* AI-populate empty cities with commoners & notables */}
    <div className="bg-black/30 rounded-lg p-6 mt-6">
      <div className="flex items-center gap-3 mb-3">
        <Sparkles className="w-6 h-6 text-cyan-300" />
        <h3 className="text-lg font-bold text-cyan-200">AI-Populate Empty Cities</h3>
      </div>
      <p className="text-gray-400 mb-4">
        Finds the N most-empty cities (fewer than 4 residents) and uses
        gpt-4o-mini to generate 4 commoners + 2 notables each, tagged
        <code className="text-cyan-300 mx-1">created_by: seed:ai_population</code>
        so they can be audited and refined later. Call repeatedly to cover the
        whole realm; each call costs LLM credits, so it&apos;s capped per click.
      </p>

      <div className="flex items-center gap-3 mb-3">
        <label className="text-xs text-gray-300">Cities to populate per click:</label>
        <Input
          type="number"
          min={1}
          max={25}
          value={populateCount}
          onChange={(e) => setPopulateCount(Math.max(1, Math.min(25, parseInt(e.target.value, 10) || 1)))}
          className="w-20 bg-black/40 border-cyan-500/30 text-white"
          data-testid="populate-count-input"
        />
      </div>

      <Button
        onClick={handlePopulateCities}
        disabled={populating}
        className="bg-gradient-to-r from-cyan-700 to-teal-700 hover:from-cyan-800 hover:to-teal-800"
        data-testid="populate-cities-btn"
      >
        {populating ? (
          <>
            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            Populating {populateCount} cit{populateCount === 1 ? 'y' : 'ies'}…
          </>
        ) : (
          <>
            <Sparkles className="w-4 h-4 mr-2" />
            AI-Populate {populateCount} Cit{populateCount === 1 ? 'y' : 'ies'}
          </>
        )}
      </Button>

      {populateResult && (
        <div className="mt-4 bg-black/40 border border-cyan-500/30 rounded-lg p-4" data-testid="populate-cities-result">
          <p className="text-sm text-cyan-200 mb-2">
            <CheckCircle2 className="w-4 h-4 inline mr-1" />
            Processed {populateResult.processed} cit{populateResult.processed === 1 ? 'y' : 'ies'} — {populateResult.inserted} NPC{populateResult.inserted === 1 ? '' : 's'} added.
          </p>
          {populateResult.cities?.length > 0 && (
            <ul className="text-xs text-gray-400 space-y-1">
              {populateResult.cities.map((c) => (
                <li key={c.slug}>
                  <span className="text-cyan-300">{c.name}</span> — {c.inserted} added
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>

    {/* Image Batcher — gpt-image-1 background job for missing city/location artwork */}
    <div className="bg-black/30 rounded-lg p-6 mt-6">
      <div className="flex items-center gap-3 mb-3">
        <ImageIcon className="w-6 h-6 text-fuchsia-300" />
        <h3 className="text-lg font-bold text-fuchsia-200">Generate Missing City &amp; Location Images</h3>
      </div>
      <p className="text-gray-400 mb-4">
        Runs <code className="text-fuchsia-300">gpt-image-1</code> via your
        Emergent Universal Key. Each click kicks off a background batch of up
        to <strong>25 images</strong> (cities prioritised first, then locations).
        Toggle <em>Auto-continue</em> to have the server loop batch-after-batch
        until every missing image is generated — safe to close the tab.
        Cost: ~$0.04 per image.
      </p>

      {imgSurvey && (
        <div className="mb-4 grid sm:grid-cols-3 gap-3 text-sm">
          <div className="bg-black/40 rounded-md p-3 border border-fuchsia-500/20">
            <div className="text-fuchsia-300/70 text-xs uppercase">Cities missing</div>
            <div className="text-fuchsia-100 text-2xl font-bold">{imgSurvey.cities_missing}</div>
          </div>
          <div className="bg-black/40 rounded-md p-3 border border-fuchsia-500/20">
            <div className="text-fuchsia-300/70 text-xs uppercase">Locations missing</div>
            <div className="text-fuchsia-100 text-2xl font-bold">{imgSurvey.locations_missing}</div>
          </div>
          <div className="bg-black/40 rounded-md p-3 border border-fuchsia-500/20">
            <div className="text-fuchsia-300/70 text-xs uppercase">Total remaining</div>
            <div className="text-fuchsia-100 text-2xl font-bold">{imgSurvey.total_missing}</div>
          </div>
        </div>
      )}

      <div className="flex flex-wrap items-center gap-3 mb-3">
        <Button
          onClick={() => handleStartImageBatch({ autoContinue: false })}
          disabled={imgStatus?.is_running}
          className="bg-gradient-to-r from-fuchsia-700 to-pink-700 hover:from-fuchsia-800 hover:to-pink-800"
          data-testid="image-batch-generate-btn"
        >
          {imgStatus?.is_running ? (
            <>
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              Batch in progress…
            </>
          ) : (
            <>
              <ImageIcon className="w-4 h-4 mr-2" />
              Generate Next 25
            </>
          )}
        </Button>
        {imgStatus?.is_running && (
          <Button
            onClick={handleStopImageBatch}
            variant="outline"
            className="border-red-700 text-red-200 hover:bg-red-950"
            data-testid="image-batch-stop-btn"
          >
            <XCircle className="w-4 h-4 mr-2" />
            Stop after current image
          </Button>
        )}
        <label className="flex items-center gap-2 text-sm text-fuchsia-200 cursor-pointer select-none">
          <Switch
            checked={imgAutoContinue}
            onCheckedChange={setImgAutoContinue}
            data-testid="image-batch-autocontinue-toggle"
          />
          <span>
            Auto-continue until all images are done (server-side)
            {imgAutoContinue && imgSurvey && imgSurvey.total_missing > 0 && (
              <span className="text-fuchsia-200/60 ml-2 text-xs">
                (~{Math.ceil(imgSurvey.total_missing / 25)} more batches · ~${(imgSurvey.total_missing * 0.04).toFixed(2)})
              </span>
            )}
          </span>
        </label>
      </div>

      {imgStatus && (imgStatus.iterations_run > 0 || imgStatus.generated > 0 || imgStatus.is_running) && (
        <div className="bg-black/40 border border-fuchsia-500/30 rounded-md p-3 space-y-1 text-sm" data-testid="image-batch-status-panel">
          <p className="text-fuchsia-200">
            {imgStatus.is_running ? (
              <>
                <Loader2 className="w-4 h-4 inline mr-1 animate-spin" />
                <strong>Running</strong>{imgStatus.auto_continue ? ' (auto-continue)' : ''} — generated {imgStatus.generated} ·
                {' '}failed {imgStatus.failed}
                {imgStatus.iterations_run > 0 && (
                  <span className="text-fuchsia-200/60 text-xs">
                    {' '}· iteration {imgStatus.iterations_run}
                  </span>
                )}
              </>
            ) : (
              <>
                <CheckCircle2 className="w-4 h-4 inline mr-1" />
                <strong>{imgStatus.auto_continue ? 'Run complete' : 'Last batch complete'}</strong> — generated {imgStatus.generated} ·
                {' '}failed {imgStatus.failed}
                {imgStatus.iterations_run > 0 && (
                  <span className="text-fuchsia-200/60 text-xs">
                    {' '}· {imgStatus.iterations_run} iteration{imgStatus.iterations_run === 1 ? '' : 's'}
                  </span>
                )}
                {imgStatus.last_completed_at && (
                  <span className="text-fuchsia-200/60 text-xs">
                    {' '}· {new Date(imgStatus.last_completed_at).toLocaleString()}
                  </span>
                )}
              </>
            )}
          </p>
          {imgStatus.stopped_reason && !imgStatus.is_running && (
            <p className="text-fuchsia-200/70 text-xs italic">
              {imgStatus.stopped_reason}
            </p>
          )}
          {imgStatus.last_error && (
            <p className="text-red-300/80 text-xs italic">Last error: {imgStatus.last_error}</p>
          )}
        </div>
      )}
    </div>

    {/* Tier 1 FULL — every canonical city across all five realms */}
    <div className="bg-black/30 rounded-lg p-6 mt-6">
      <div className="flex items-center gap-3 mb-3">
        <Crown className="w-6 h-6 text-yellow-300" />
        <h3 className="text-lg font-bold text-yellow-200">Tier 1 (FULL) — Seed All Realms Canon</h3>
      </div>
      <p className="text-gray-400 mb-4">
        Seeds every canonical city across all five realms:
        <span className="text-yellow-200"> Ammeonon </span>(Wymroost, Invrasil, Hielgcrom Old Town, Amberport, Duncroft),
        <span className="text-emerald-200"> Selindori </span>(Aurelion Spires, Thalenroot, Nal&apos;theris, Isenfell, Aer&apos;Cyr),
        <span className="text-amber-200"> Dhor-Kuldor </span>(Ancestor Hall, Irondeep, Gloomstone — adds to the min-viable set),
        <span className="text-red-200"> Aigraels </span>(Ironhold, Noctyss Vale, Astra&apos;Lun, Vargath),
        <span className="text-violet-200"> Veiled Realms </span>(Rakesh, Yaksha-Shi, Serant-Kresh, Moonfall, Selune&apos;s Rest, Twilight Citadel).
        Idempotent — re-running updates existing rows in place. After
        running this, all 14 Titan Sacred Sites can bind cleanly.
      </p>
      <Button
        onClick={handleSeedAllRealms}
        disabled={realmsBusy}
        className="bg-gradient-to-r from-yellow-700 via-amber-700 to-orange-700 hover:from-yellow-800 hover:via-amber-800 hover:to-orange-800"
        data-testid="seed-all-realms-btn"
      >
        {realmsBusy ? (
          <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Seeding all five realms…</>
        ) : (
          <><Crown className="w-4 h-4 mr-2" />Seed FULL Realms Canon</>
        )}
      </Button>
      {realmsResult && (
        <div className="mt-4 bg-black/40 border border-yellow-500/30 rounded-md p-3 text-sm" data-testid="seed-all-realms-result">
          <p className="text-yellow-200 mb-2">
            <CheckCircle2 className="w-4 h-4 inline mr-1" />
            <strong>{realmsResult.total_inserted}</strong> new ·{' '}
            <strong>{realmsResult.total_updated}</strong> refreshed ·{' '}
            {realmsResult.total_processed} canonical cities processed
          </p>
          <div className="grid sm:grid-cols-2 gap-1 text-xs text-yellow-100/80">
            {Object.entries(realmsResult.by_realm || {}).map(([nation, r]) => (
              <div key={nation}>
                <strong className="text-yellow-200">{nation}</strong>:{' '}
                {r.inserted.length} new, {r.updated.length} refreshed
              </div>
            ))}
          </div>
        </div>
      )}
    </div>

    {/* Tier 1 — Dhor-Kuldor canonical hold-capital cities */}
    <div className="bg-black/30 rounded-lg p-6 mt-6">
      <div className="flex items-center gap-3 mb-3">
        <Hammer className="w-6 h-6 text-amber-300" />
        <h3 className="text-lg font-bold text-amber-200">Tier 1 — Seed Dhor-Kuldor Canon (Hold-Capitals)</h3>
      </div>
      <p className="text-gray-400 mb-4">
        Inserts or updates the six canonical dwarven hold-capital cities:
        Stonehaven, Thal&apos;Karrak, Emberhold, Magmathal, Frosthold, Icehammer
        Bastion. Required for the Tongue of Y&apos;ros trial location and for
        Titan Sacred Sites to bind properly. Idempotent — safe to run more
        than once.
      </p>
      <Button
        onClick={handleSeedDhorKuldorCanon}
        disabled={kuldorBusy}
        className="bg-gradient-to-r from-amber-700 to-orange-700 hover:from-amber-800 hover:to-orange-800"
        data-testid="seed-dhor-kuldor-canon-btn"
      >
        {kuldorBusy ? (
          <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Seeding canon…</>
        ) : (
          <><Hammer className="w-4 h-4 mr-2" />Seed Dhor-Kuldor Canon</>
        )}
      </Button>
      {kuldorResult && (
        <div className="mt-4 bg-black/40 border border-amber-500/30 rounded-md p-3 text-sm" data-testid="seed-kuldor-result">
          <p className="text-amber-200">
            <CheckCircle2 className="w-4 h-4 inline mr-1" />
            <strong>{kuldorResult.cities?.inserted?.length || 0}</strong> new ·{' '}
            <strong>{kuldorResult.cities?.updated?.length || 0}</strong> refreshed
          </p>
        </div>
      )}
    </div>

    {/* Tier 2d — Titan Sacred Sites annotation */}
    <div className="bg-black/30 rounded-lg p-6 mt-6">
      <div className="flex items-center gap-3 mb-3">
        <Sparkles className="w-6 h-6 text-indigo-300" />
        <h3 className="text-lg font-bold text-indigo-200">Tier 2d — Annotate Titan Sacred Sites</h3>
      </div>
      <p className="text-gray-400 mb-4">
        Annotates a curated list of canonical locations with a{' '}
        <code className="text-indigo-300">titan_sacred_site</code> flag tying
        them to one of the Seven Titans slain by Ausar. The Quest Master AI
        weaves the themed essence (flame / frost / stone / wind / tide /
        shadow / decay) into every scene at these sites, and magic in the
        matching essence is amplified. Idempotent.
      </p>
      <Button
        onClick={handleSeedTitanSites}
        disabled={titanBusy}
        className="bg-gradient-to-r from-indigo-700 to-violet-700 hover:from-indigo-800 hover:to-violet-800"
        data-testid="seed-titan-sites-btn"
      >
        {titanBusy ? (
          <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Annotating sacred sites…</>
        ) : (
          <><Sparkles className="w-4 h-4 mr-2" />Annotate Titan Sacred Sites</>
        )}
      </Button>
      {titanResult && (
        <div className="mt-4 bg-black/40 border border-indigo-500/30 rounded-md p-3 space-y-2 text-sm" data-testid="seed-titan-result">
          <p className="text-indigo-200">
            <CheckCircle2 className="w-4 h-4 inline mr-1" />
            <strong>{titanResult.annotated}</strong> newly annotated ·{' '}
            <strong>{titanResult.already_annotated}</strong> previously done ·{' '}
            <strong>{titanResult.not_found_count}</strong> slugs missing
          </p>
        </div>
      )}
    </div>

    {/* Dedupe + indexing — fixes the "every population re-run added another copy"
        leak. One-click. Safe to run more than once. */}
    <div className="bg-black/30 rounded-lg p-6 mt-6">
      <div className="flex items-center gap-3 mb-3">
        <Trash2 className="w-6 h-6 text-rose-300" />
        <h3 className="text-lg font-bold text-rose-200">Dedupe Cities &amp; Locations + Add Indexes</h3>
      </div>
      <p className="text-gray-400 mb-4">
        Collapses every duplicate <code className="text-rose-300">(nation, city, slug)</code> group
        in the <code className="text-rose-300">locations</code> collection down to its
        oldest row, then adds the unique indexes that should have been there
        from the start. Same treatment for cities. Run this once per
        environment (preview / production); the indexes prevent any future
        duplicates from being inserted. Idempotent &amp; safe to re-run.
      </p>

      <Button
        onClick={handleCleanupGeoData}
        disabled={cleanupBusy}
        className="bg-gradient-to-r from-rose-700 to-orange-700 hover:from-rose-800 hover:to-orange-800"
        data-testid="cleanup-geo-data-btn"
      >
        {cleanupBusy ? (
          <>
            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            Cleaning up geo data…
          </>
        ) : (
          <>
            <Trash2 className="w-4 h-4 mr-2" />
            Dedupe &amp; Index Geo Data
          </>
        )}
      </Button>

      {cleanupResult && (
        <div className="mt-4 bg-black/40 border border-rose-500/30 rounded-lg p-4 space-y-2 text-sm" data-testid="cleanup-geo-result">
          <p className="text-rose-200">
            <CheckCircle2 className="w-4 h-4 inline mr-1" />
            <strong>Locations:</strong>{' '}
            {cleanupResult.locations?.rows_deleted || 0} removed ·{' '}
            {cleanupResult.locations?.total_before || 0} → {cleanupResult.locations?.total_after || 0}
          </p>
          <p className="text-rose-200">
            <CheckCircle2 className="w-4 h-4 inline mr-1" />
            <strong>Cities:</strong>{' '}
            {cleanupResult.cities?.rows_deleted || 0} removed ·{' '}
            {cleanupResult.cities?.total_before || 0} → {cleanupResult.cities?.total_after || 0}
          </p>
          <p className="text-xs text-gray-400">
            Indexes ensured: {(cleanupResult.indexes?.indexes_present || []).join(', ')}
          </p>
        </div>
      )}
    </div>
  </div>
  );
};

export default DatabaseSeedPanel;
