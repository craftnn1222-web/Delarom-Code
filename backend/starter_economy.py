"""Canonical goods catalogue for the Delarom economy.

Imported by both the offline `seed_economy.py` CLI and the in-app admin
endpoint `POST /api/economy/admin/seed-catalogue`. Single source of truth.

Each good has:
    slug              — unique kebab-case identifier
    name              — display name
    category          — used for AI event matching + UI grouping
    unit              — "per bar", "per bushel", etc.
    default_base_cost — starting cost in gold per unit (used when a faction
                        first claims this good as a specialty)
    is_service        — services don't accumulate inventory; cost moves
                        more slowly with events
    tags              — flexible list the AI uses to match world events
                        (e.g. "war" event raises items tagged ["weapon"])
"""

CANONICAL_GOODS = [
    # ── Metals & raw materials ──
    {"slug": "iron-ore",         "name": "Iron Ore",         "category": "metal",   "unit": "per cart-load", "default_base_cost": 20,  "is_service": False, "tags": ["metal", "raw", "war"]},
    {"slug": "iron-ingots",      "name": "Iron Ingots",      "category": "metal",   "unit": "per bar",       "default_base_cost": 45,  "is_service": False, "tags": ["metal", "war", "weapons"]},
    {"slug": "steel-ingots",     "name": "Steel Ingots",     "category": "metal",   "unit": "per bar",       "default_base_cost": 110, "is_service": False, "tags": ["metal", "war", "weapons", "armor"]},
    {"slug": "silver-bullion",   "name": "Silver Bullion",   "category": "metal",   "unit": "per pound",     "default_base_cost": 180, "is_service": False, "tags": ["metal", "currency", "luxury"]},
    {"slug": "gold-bullion",     "name": "Gold Bullion",     "category": "metal",   "unit": "per pound",     "default_base_cost": 900, "is_service": False, "tags": ["metal", "currency", "luxury"]},
    {"slug": "stone-blocks",     "name": "Quarried Stone",   "category": "stone",   "unit": "per block",     "default_base_cost": 12,  "is_service": False, "tags": ["stone", "raw", "build"]},
    {"slug": "uncut-gems",       "name": "Uncut Gemstones",  "category": "luxury",  "unit": "per gem",       "default_base_cost": 250, "is_service": False, "tags": ["luxury", "raw"]},

    # ── Food & drink ──
    {"slug": "grain",            "name": "Grain",            "category": "food",    "unit": "per bushel",    "default_base_cost": 4,   "is_service": False, "tags": ["food", "staple", "harvest"]},
    {"slug": "salted-fish",      "name": "Salted Fish",      "category": "food",    "unit": "per barrel",    "default_base_cost": 18,  "is_service": False, "tags": ["food", "coast"]},
    {"slug": "spiced-wine",      "name": "Spiced Wine",      "category": "luxury",  "unit": "per cask",      "default_base_cost": 90,  "is_service": False, "tags": ["luxury", "drink", "festival"]},
    {"slug": "cured-meats",      "name": "Cured Meats",      "category": "food",    "unit": "per side",      "default_base_cost": 35,  "is_service": False, "tags": ["food", "preserved"]},
    {"slug": "hard-tack",        "name": "Hard Tack Bread",  "category": "food",    "unit": "per crate",     "default_base_cost": 8,   "is_service": False, "tags": ["food", "staple", "war"]},

    # ── Textiles & leatherwork ──
    {"slug": "wool-bolts",       "name": "Wool Bolts",       "category": "textile", "unit": "per bolt",      "default_base_cost": 22,  "is_service": False, "tags": ["textile", "clothing"]},
    {"slug": "silken-cloth",     "name": "Silken Cloth",     "category": "textile", "unit": "per bolt",      "default_base_cost": 200, "is_service": False, "tags": ["textile", "luxury", "elven"]},
    {"slug": "tanned-leather",   "name": "Tanned Leather",   "category": "textile", "unit": "per hide",      "default_base_cost": 30,  "is_service": False, "tags": ["leather", "armor"]},

    # ── Crafted goods ──
    {"slug": "iron-swords",      "name": "Iron Swords",      "category": "weapon",  "unit": "per blade",     "default_base_cost": 140, "is_service": False, "tags": ["weapon", "war", "metal"]},
    {"slug": "steel-armor",      "name": "Steel Plate",      "category": "armor",   "unit": "per suit",      "default_base_cost": 800, "is_service": False, "tags": ["armor", "war", "metal", "luxury"]},
    {"slug": "fine-jewelry",     "name": "Fine Jewelry",     "category": "luxury",  "unit": "per piece",     "default_base_cost": 600, "is_service": False, "tags": ["luxury", "gems"]},
    {"slug": "stonework",        "name": "Carved Stonework", "category": "stone",   "unit": "per block",     "default_base_cost": 80,  "is_service": False, "tags": ["stone", "build", "luxury"]},

    # ── Reagents & magical ──
    {"slug": "arcane-reagents",  "name": "Arcane Reagents",  "category": "reagent", "unit": "per vial",      "default_base_cost": 320, "is_service": False, "tags": ["reagent", "magic"]},
    {"slug": "mountain-herbs",   "name": "Mountain Herbs",   "category": "reagent", "unit": "per pouch",     "default_base_cost": 60,  "is_service": False, "tags": ["reagent", "medicine", "herb"]},
    {"slug": "rune-scrolls",     "name": "Rune Scrolls",     "category": "reagent", "unit": "per scroll",    "default_base_cost": 450, "is_service": False, "tags": ["reagent", "magic", "knowledge"]},

    # ── Services ──
    {"slug": "scribing-service", "name": "Scribing Services","category": "service", "unit": "per commission","default_base_cost": 50,  "is_service": True,  "tags": ["service", "knowledge"]},
    {"slug": "healing-service",  "name": "Healing Services", "category": "service", "unit": "per session",   "default_base_cost": 75,  "is_service": True,  "tags": ["service", "medicine"]},
    {"slug": "guard-service",    "name": "Guard Services",   "category": "service", "unit": "per fortnight", "default_base_cost": 120, "is_service": True,  "tags": ["service", "war", "security"]},
]


# Faction → specialties. The base cost listed here is what THIS faction
# charges to produce 1 unit of the good. Cities buying from this faction pay
# this cost plus the faction-to-city tariff.
STARTER_FACTION_SPECIALTIES = {
    # The Forgemaster's Guild — the smith-princes of Dhor-Kuldor.
    "forgemasters-guild": [
        {"good_slug": "iron-ore",      "base_cost": 18,  "capacity": 200, "description": "Mountain ore mined from clan-held veins"},
        {"good_slug": "iron-ingots",   "base_cost": 40,  "capacity": 120, "description": "Smelted in clan forges"},
        {"good_slug": "steel-ingots",  "base_cost": 95,  "capacity": 60,  "description": "Folded steel — guild-marked"},
        {"good_slug": "iron-swords",   "base_cost": 130, "capacity": 30,  "description": "Standard infantry blades"},
        {"good_slug": "steel-armor",   "base_cost": 750, "capacity": 8,   "description": "Forge-master plate, runed-fitted"},
    ],

    # The Loremaster's Guild — scribes, scrolls, magical knowledge.
    "loremasters-guild": [
        {"good_slug": "rune-scrolls",     "base_cost": 420, "capacity": 12, "description": "Authenticated rune-scrolls from the Vault of Names"},
        {"good_slug": "scribing-service", "base_cost": 48,  "capacity": 25, "description": "Master scribes for hire"},
        {"good_slug": "arcane-reagents",  "base_cost": 300, "capacity": 20, "description": "Catalogued and provenanced reagents"},
    ],

    # The High King's Court — sets the realm's coin standard.
    "high-kings-court": [
        {"good_slug": "gold-bullion",   "base_cost": 870, "capacity": 6,  "description": "Crown-stamped bullion from the King's mint"},
        {"good_slug": "silver-bullion", "base_cost": 170, "capacity": 24, "description": "Royal silver, taxation-grade"},
        {"good_slug": "guard-service",  "base_cost": 110, "capacity": 15, "description": "King's-mark veterans for hire"},
    ],

    # The Ardent Legion — Aigraels loyalists; produce mostly war goods.
    "ardent-legion": [
        {"good_slug": "iron-swords",   "base_cost": 145, "capacity": 25, "description": "Legion-pattern blades"},
        {"good_slug": "tanned-leather","base_cost": 28,  "capacity": 60, "description": "Banner-leather, lacquered legion colours"},
        {"good_slug": "hard-tack",     "base_cost": 7,   "capacity": 200,"description": "Field rations baked at the garrison"},
        {"good_slug": "guard-service", "base_cost": 115, "capacity": 20, "description": "Legion mercenaries (under-contract)"},
    ],

    # The Forsaken Court — exiles, spies, contraband.
    "forsaken-court": [
        {"good_slug": "uncut-gems",     "base_cost": 220, "capacity": 8,  "description": "Salvaged from sacked estates (no questions asked)"},
        {"good_slug": "spiced-wine",    "base_cost": 80,  "capacity": 30, "description": "Old-noble vintages, smuggled through back-channels"},
        {"good_slug": "arcane-reagents","base_cost": 290, "capacity": 12, "description": "Acquired from ruined towers, provenance unclear"},
    ],

    # The Elderborn Alliance — druids and old-blood folk of Aigraels.
    "elderborn-alliance": [
        {"good_slug": "mountain-herbs", "base_cost": 55,  "capacity": 80, "description": "Hand-foraged remedies from sacred groves"},
        {"good_slug": "wool-bolts",     "base_cost": 20,  "capacity": 50, "description": "Highland wool from the alliance's flocks"},
        {"good_slug": "cured-meats",    "base_cost": 32,  "capacity": 35, "description": "Smoked venison, alliance-pattern"},
        {"good_slug": "healing-service","base_cost": 70,  "capacity": 18, "description": "Druidic healers — house-call only"},
    ],
}


# Categories that the AI economy event hook recognises.
EVENT_CATEGORY_TAGS = {
    "war":      ["war", "weapon", "armor", "metal"],
    "festival": ["festival", "drink", "luxury", "food"],
    "disaster": ["food", "staple", "harvest"],
    "blight":   ["food", "staple", "harvest", "reagent"],
    "trial":    [],  # trials don't move markets
    "crime":    [],
}
