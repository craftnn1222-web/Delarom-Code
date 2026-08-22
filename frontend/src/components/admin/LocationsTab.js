import React, { useMemo, useState } from 'react';
import { MapPin, Edit2, Search } from 'lucide-react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';

/**
 * Roleplay Locations tab — list of dynamic RP locations with edit / toggle.
 *
 * Hardened for realms with 1500+ locations:
 *  - Filter by nation, by city, free-text search by name/slug.
 *  - Cap render to 200 cards (with a "show all" toggle) so the page can't
 *    drown the browser if filters are wide open.
 *  - Group header shows the active filter + total count so admins know
 *    what they're looking at instead of guessing.
 */
const LocationsTab = ({ locations, onNewLocation, onEditLocation, onToggleActive }) => {
  const [nation, setNation] = useState('all');
  const [city, setCity] = useState('all');
  const [search, setSearch] = useState('');
  const [showAll, setShowAll] = useState(false);

  // Unique nation + city values present in the data (cheap derivations).
  const nations = useMemo(
    () => Array.from(new Set(locations.map((l) => l.nation).filter(Boolean))).sort(),
    [locations]
  );
  const citiesForNation = useMemo(() => {
    const scope = nation === 'all' ? locations : locations.filter((l) => l.nation === nation);
    return Array.from(new Set(scope.map((l) => l.city).filter(Boolean))).sort();
  }, [locations, nation]);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return locations
      .filter((l) => nation === 'all' || l.nation === nation)
      .filter((l) => {
        if (city === 'all') return true;
        if (city === '__nation_level__') return !l.city;
        return l.city === city;
      })
      .filter((l) => {
        if (!q) return true;
        return (
          (l.name || '').toLowerCase().includes(q) ||
          (l.slug || '').toLowerCase().includes(q)
        );
      });
  }, [locations, nation, city, search]);

  const RENDER_CAP = 200;
  const visible = showAll ? filtered : filtered.slice(0, RENDER_CAP);
  const hiddenCount = filtered.length - visible.length;

  return (
    <>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-2xl font-bold text-purple-300 flex items-center gap-2">
          <MapPin className="w-5 h-5" />
          Roleplay Locations
          <span className="text-sm font-normal text-gray-400 ml-2">
            ({filtered.length} of {locations.length})
          </span>
        </h2>
        <Button
          size="sm"
          onClick={onNewLocation}
          className="bg-gradient-to-r from-purple-600 to-pink-600"
          data-testid="new-location-btn"
        >
          <Edit2 className="w-4 h-4 mr-1" /> New Location
        </Button>
      </div>

      {/* Filter bar */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-3 mb-5">
        <div>
          <label className="text-xs text-gray-400 block mb-1">Nation</label>
          <select
            value={nation}
            onChange={(e) => { setNation(e.target.value); setCity('all'); }}
            className="w-full bg-black/30 border border-purple-500/30 rounded-md px-3 py-2 text-sm text-white"
            data-testid="locations-filter-nation"
          >
            <option value="all">All nations</option>
            {nations.map((n) => (
              <option key={n} value={n} className="bg-gray-900">{n}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="text-xs text-gray-400 block mb-1">City</label>
          <select
            value={city}
            onChange={(e) => setCity(e.target.value)}
            className="w-full bg-black/30 border border-purple-500/30 rounded-md px-3 py-2 text-sm text-white"
            data-testid="locations-filter-city"
          >
            <option value="all">All cities</option>
            <option value="__nation_level__">— Nation-level (no parent city) —</option>
            {citiesForNation.map((c) => (
              <option key={c} value={c} className="bg-gray-900">{c}</option>
            ))}
          </select>
        </div>
        <div className="md:col-span-2">
          <label className="text-xs text-gray-400 block mb-1">Search name or slug</label>
          <div className="relative">
            <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="e.g. tyr-temple, market square"
              className="bg-black/30 border-purple-500/30 text-white pl-8"
              data-testid="locations-filter-search"
            />
          </div>
        </div>
      </div>

      {filtered.length === 0 ? (
        <div className="glass-dark p-8 rounded-xl text-center text-gray-400" data-testid="locations-empty">
          No locations match the current filters.
        </div>
      ) : (
        <>
          <div className="grid md:grid-cols-2 gap-4">
            {visible.map((loc, idx) => (
              <div
                key={`${loc.id}-${loc.nation}-${loc.slug}-${idx}`}
                className="glass-dark p-4 rounded-xl border border-purple-500/30"
                data-testid={`location-${loc.id}`}
              >
                <div className="flex items-start justify-between mb-2">
                  <div>
                    <p className="text-xs text-purple-300 uppercase tracking-wide mb-1">
                      {loc.nation}{loc.city ? ` · ${loc.city}` : ' · (nation-level)'}
                    </p>
                    <h3 className="text-lg font-bold text-white">{loc.name}</h3>
                    <p className="text-xs text-gray-400">Slug: {loc.slug}</p>
                  </div>
                  <div className="flex flex-col items-end gap-1 text-xs">
                    <span
                      className={`px-2 py-1 rounded-full border ${
                        loc.is_active
                          ? 'bg-green-600/20 text-green-400 border-green-600/40'
                          : 'bg-red-600/20 text-red-400 border-red-600/40'
                      }`}
                    >
                      {loc.is_active ? 'Active' : 'Inactive'}
                    </span>
                    <span
                      className={`px-2 py-1 rounded-full border ${
                        loc.is_rp_enabled
                          ? 'bg-blue-600/20 text-blue-400 border-blue-600/40'
                          : 'bg-gray-600/20 text-gray-400 border-gray-600/40'
                      }`}
                    >
                      {loc.is_rp_enabled ? 'RP Enabled' : 'RP Disabled'}
                    </span>
                  </div>
                </div>

                {loc.location_type && (
                  <p className="text-xs text-purple-200 mb-1">Type: {loc.location_type}</p>
                )}
                <p className="text-sm text-gray-300 line-clamp-3 mb-3">{loc.description}</p>

                <div className="flex gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    className="border-purple-500/50 text-purple-300"
                    onClick={() => onEditLocation(loc)}
                  >
                    Edit
                  </Button>
                  <Button
                    size="sm"
                    className={loc.is_active ? 'bg-red-600 hover:bg-red-700' : 'bg-green-600 hover:bg-green-700'}
                    onClick={() => onToggleActive(loc)}
                  >
                    {loc.is_active ? 'Disable' : 'Enable'}
                  </Button>
                </div>
              </div>
            ))}
          </div>

          {hiddenCount > 0 && (
            <div className="mt-5 text-center">
              <Button
                size="sm"
                variant="outline"
                onClick={() => setShowAll(true)}
                className="border-purple-500/50 text-purple-300"
                data-testid="locations-show-all"
              >
                Show {hiddenCount} more locations (rendering all may slow the page)
              </Button>
            </div>
          )}
        </>
      )}
    </>
  );
};

export default LocationsTab;
