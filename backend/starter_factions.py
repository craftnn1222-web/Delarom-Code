"""Starter-factions catalogue — the canonical 6 in-world organisations seeded
into a fresh Continents of Delarom database.

Imported BOTH by the offline `seed_factions.py` CLI script AND by the
in-app admin endpoint `POST /api/factions/admin/seed-starter`. Sharing one
source of truth means a redeploy is enough to seed any new environment —
no shell access required.
"""
STARTER_FACTIONS = [
    {
        "slug": "ardent-legion",
        "name": "The Ardent Legion",
        "nation_home": "aigraels",
        "motto": "Through Fire, the Throne Endures",
        "description": (
            "Loyalists who still bend the knee to the Old Crown. They fight to "
            "restore the unbroken throne of Aigraels and to scour the land of the "
            "Forsaken Court. Their banners burn bright in every campaign, and their "
            "officers see surrender as the final treason."
        ),
        "color_hex": "#dc2626",
        "icon": "swords",
    },
    {
        "slug": "forsaken-court",
        "name": "The Forsaken Court",
        "nation_home": "aigraels",
        "motto": "We Were Cast Aside — Now We Cast Down",
        "description": (
            "Exiled nobles, broken oathmen, and those who watched their houses "
            "burn at the Old Crown's order. The Forsaken Court hold no love for "
            "any throne. They strike from the shadows, paying coin in grudges "
            "and old debts. Some are knights without colours; others are nothing "
            "more than ghosts with a grievance."
        ),
        "color_hex": "#475569",
        "icon": "skull",
    },
    {
        "slug": "elderborn-alliance",
        "name": "The Elderborn Alliance",
        "nation_home": "aigraels",
        "motto": "The Land Remembers Before the Throne",
        "description": (
            "Druids, wardens, and old-blood folk who reject the very idea of "
            "kings. They claim Aigraels belongs to no crown — it belongs to the "
            "elder things sleeping beneath its hills. The Alliance prefers "
            "diplomacy and patient ruin to open war, but they have spilled blood "
            "when the land asked it of them."
        ),
        "color_hex": "#16a34a",
        "icon": "tree",
    },
    {
        "slug": "forgemasters-guild",
        "name": "The Forgemaster's Guild",
        "nation_home": "dhor-kuldor",
        "motto": "Steel Is Patience Made Sharp",
        "description": (
            "The smith-princes of Dhor Kuldor. To forge a weapon worthy of a Hero "
            "is to earn a guild seat; to forge a weapon worthy of a King is to "
            "earn a mountain. The Forgemasters keep the old rune-craft alive and "
            "answer only to the High King's Court — when they answer at all."
        ),
        "color_hex": "#f59e0b",
        "icon": "hammer",
    },
    {
        "slug": "high-kings-court",
        "name": "The High King's Court",
        "nation_home": "dhor-kuldor",
        "motto": "What Was Sworn Is Iron",
        "description": (
            "The royal household of Dhor Kuldor — not a ceremonial body but a "
            "working council. Every clan-thane, every grudge-keeper, every senior "
            "officer of the realm answers here. To stand at the High King's table "
            "is to speak with the weight of stone behind every word."
        ),
        "color_hex": "#7c3aed",
        "icon": "crown",
    },
    {
        "slug": "loremasters-guild",
        "name": "The Loremaster's Guild",
        "nation_home": "dhor-kuldor",
        "motto": "Ink Outlives Iron",
        "description": (
            "Scholars, scribes, and rune-readers who maintain the great Vault of "
            "Names beneath the mountain. Loremasters travel the realms recording "
            "deeds, copying maps, and recovering knowledge from ruins. The "
            "Guild's seal opens doors that armies cannot break."
        ),
        "color_hex": "#0ea5e9",
        "icon": "scroll",
    },
]
