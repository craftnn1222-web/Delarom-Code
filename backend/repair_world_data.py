"""World-data repair utilities.

Two idempotent fixes for the "some cities show no locations" regression that
appeared after the canon-city + Titan Sacred Sites seeding:

1. `fix_nation_slug`      — normalise the lone `nations` doc still on the old
                            `dhor-khuldor` slug to the canonical `dhor-kuldor`
                            used by every `cities`/`locations` row (and the web
                            hard-coded slugs). Without this, the mobile World
                            tab (which reads `/nations/images`) can't resolve
                            that nation's cities.
2. `ensure_baseline_locations` — for every city that has ZERO active locations,
                            insert a small starter set of RP-enabled locations
                            so no city is a dead-end. Purely additive and
                            idempotent; never touches hand-authored locations.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Dict, List

# (slug-suffix, name template, location_type, description template)
BASELINE_LOCATIONS: List[tuple] = [
    (
        "town-square",
        "{name} Town Square",
        "Landmark",
        "The open heart of {name}, where citizens gather beneath the sky — "
        "merchants, heralds, and wanderers all crossing paths.",
    ),
    (
        "tavern",
        "The Hearth of {name}",
        "Tavern",
        "A warm, crowded tavern in {name}. Ale flows freely, rumours travel "
        "faster than coin, and a corner table always waits for a new tale.",
    ),
    (
        "market",
        "{name} Market Row",
        "Market",
        "The bustling market row of {name} — spice, steel, and secrets change "
        "hands from dawn till dusk.",
    ),
    (
        "gate",
        "{name} Gate",
        "Gate",
        "The great gate of {name}, where every arrival is weighed by the "
        "guards' watchful eyes and the city's mood turns on who passes through.",
    ),
]


async def fix_nation_slug(db, old: str = "dhor-khuldor", new: str = "dhor-kuldor") -> Dict:
    """Rename the outlier nation slug to the canonical one. Idempotent."""
    old_doc = await db.nations.find_one({"slug": old})
    if not old_doc:
        return {"fixed": False, "reason": f"no '{old}' nation doc (already canonical)"}
    new_doc = await db.nations.find_one({"slug": new})
    if new_doc:
        # Canonical already exists — just drop the stale duplicate.
        await db.nations.delete_one({"slug": old})
        return {"fixed": True, "note": f"removed stale duplicate '{old}' ('{new}' already present)"}
    await db.nations.update_one(
        {"slug": old},
        {"$set": {"slug": new, "name": "Dhor-Kuldor"}},
    )
    return {"fixed": True, "note": f"renamed '{old}' -> '{new}'"}


async def ensure_baseline_locations(db) -> Dict:
    """Give every city with no active locations a starter set. Idempotent."""
    created: List[str] = []
    cities_filled = 0
    cities = await db.cities.find(
        {}, {"_id": 0, "nation": 1, "slug": 1, "name": 1}
    ).to_list(length=None)

    for city in cities:
        nation = city.get("nation")
        cslug = city.get("slug")
        if not nation or not cslug:
            continue
        cname = city.get("name") or cslug.replace("-", " ").title()

        active = await db.locations.count_documents(
            {"nation": nation, "city": cslug, "is_active": True}
        )
        if active > 0:
            continue

        cities_filled += 1
        for suffix, name_t, ltype, desc_t in BASELINE_LOCATIONS:
            lslug = f"{cslug}-{suffix}"
            exists = await db.locations.find_one(
                {"nation": nation, "city": cslug, "slug": lslug}, {"_id": 1}
            )
            if exists:
                continue
            doc = {
                "id": str(uuid.uuid4()),
                "nation": nation,
                "city": cslug,
                "slug": lslug,
                "name": name_t.format(name=cname),
                "location_type": ltype,
                "description": desc_t.format(name=cname),
                "image_url": None,
                "is_active": True,
                "is_rp_enabled": True,
                "is_baseline": True,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            await db.locations.insert_one(doc)
            created.append(f"{nation}/{cslug}/{lslug}")

    return {"cities_filled": cities_filled, "locations_created": len(created), "created": created}


async def repair_world_data(db) -> Dict:
    """Run both repairs and return a combined summary."""
    return {
        "nation_slug": await fix_nation_slug(db),
        "baseline_locations": await ensure_baseline_locations(db),
    }
