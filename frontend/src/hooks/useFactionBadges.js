import { useEffect, useState, useMemo, useRef } from 'react';
import { getFactionsForCharactersBatch } from '../utils/api';

/**
 * Batched, de-duped faction lookup for character IDs.
 *
 * Pass an array of character ids; returns a memoised `{[id]: factionInfo|null}`
 * map. Re-runs only when the set of ids changes. Designed for list-style
 * surfaces (forum thread replies, RP scene participant rows) where calling
 * /characters/:id/faction one-at-a-time would be quadratic in latency.
 *
 * The hook keeps an in-component cache, so adding more ids to the list
 * only fetches the NEW ids — already-known mappings stay hot.
 */
const useFactionBadges = (characterIds) => {
  const [cache, setCache] = useState({});
  const inflight = useRef(new Set());

  // Stable sorted key so [a,b] and [b,a] don't trigger a refetch.
  const keyedIds = useMemo(
    () => Array.from(new Set((characterIds || []).filter(Boolean))).sort(),
    [characterIds],
  );

  useEffect(() => {
    const missing = keyedIds.filter((id) => !(id in cache) && !inflight.current.has(id));
    if (missing.length === 0) return;
    missing.forEach((id) => inflight.current.add(id));

    let cancelled = false;
    (async () => {
      try {
        const r = await getFactionsForCharactersBatch(missing);
        if (cancelled) return;
        setCache((prev) => ({ ...prev, ...r.data }));
      } catch (_e) {
        // Soft-fail — badges just won't render. Don't block the page.
      } finally {
        missing.forEach((id) => inflight.current.delete(id));
      }
    })();

    return () => { cancelled = true; };
  }, [keyedIds, cache]);

  return cache;
};

export default useFactionBadges;
