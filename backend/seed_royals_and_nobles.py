"""Hand-authored royals & capital nobles for the Continents of Delarom.

20 lore-faithful NPCs total:
  - 5 royals (one ruler per nation)
  - 15 nobles (3 per nation capital — Wymroost, Aurelion Spires, Karak Vorn,
    Astra'Lun, Niratha)

Each entry has a single-sentence quirk, a personality block, a motivation
that points at real in-world tension, and a `created_by` tag so admins can
audit/refine these later separately from the AI-generated populace.

Idempotent: `seed_royals_and_nobles(db)` skips any (name, nation) already
present.
"""
import asyncio
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient


load_dotenv(Path(__file__).parent / ".env")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─────────────────────────────────────────────────────────────────────────
# ROYALS — one ruling sovereign per nation.
# ─────────────────────────────────────────────────────────────────────────
ROYALS = [
    {
        "name": "Empress Marielle Wymrose, the Sealed Tongue",
        "race": "Human",
        "role": "Empress of Ammeonon",
        "nation": "ammeonon",
        "location": "Wymroost",
        "personality": "Patient, watchful, never raises her voice — and never repeats herself.",
        "motivation": "Keep the academies free of imperial leash, even from her own crown.",
        "quirks": "Keeps a raven trained to repeat the last sentence spoken at court back to her in private.",
        "background": (
            "Marielle Wymrose rose from a trade-house, married a dying duke, and within ten years "
            "had unified the squabbling port-lords of Ammeonon under a single seal. She rules from "
            "the Pearl Throne in Wymroost, surrounded by ledgers as much as guards. Foreign envoys "
            "find her hospitable and unreadable in equal measure."
        ),
    },
    {
        "name": "Sun-Queen Lyssoria Aurelion, the Goldborn",
        "race": "Sun-Elf",
        "role": "Sun-Queen of Selindori",
        "nation": "selindori",
        "location": "Aurelion Spires",
        "personality": "Radiant, deliberate, gives audience only in shafts of sunlight.",
        "motivation": "Carry the line of Sun unbroken to the next eclipse — twenty-two years hence.",
        "quirks": "Speaks aloud only between dawn and dusk; in winter her decrees are sung by her heralds.",
        "background": (
            "Lyssoria is the seventy-third of her line and the first to take the throne without "
            "marrying a Moon-consort — a deliberate gesture against the Veiled Realms. Her court "
            "calls her radiant; her enemies call her brittle. She has not lost a single petitioner "
            "to the Spires in eleven years."
        ),
    },
    {
        "name": "High King Borr Stoneheart, the Unhelmed",
        "race": "Dwarf",
        "role": "High King of Dhor-Kuldor",
        "nation": "dhor-kuldor",
        "location": "Karak Vorn",
        "personality": "Blunt as a hammer-fall, slow to anger, slower to forgive a slight to a guildhouse.",
        "motivation": "Prove the Iron Halls can stand without one ounce of Selindori silver.",
        "quirks": "Forged his own crown from a melted-down ceremonial chain; refuses to wear the ancestral one.",
        "background": (
            "Borr took the High Throne at Karak Vorn by acclamation of the seven guildhouses, not "
            "by inheritance. His own father is still alive, presiding as Loremaster — an arrangement "
            "the realm finds either touching or scandalous depending on the cup in hand."
        ),
    },
    {
        "name": "Emperor Aurelius the Mirrored",
        "race": "High-Elf",
        "role": "Emperor of Aigraels",
        "nation": "aigraels",
        "location": "Astra'Lun",
        "personality": "Courteous to a fault, never refuses an audience, never grants one without a witness.",
        "motivation": "Keep every mask in the empire intact, including his own.",
        "quirks": "It is said a second Aurelius walks the throne room when he himself is absent; no one will confirm it.",
        "background": (
            "Aurelius has held the Mirrored Throne for forty-eight years without naming an heir. "
            "His ministers say he sleeps three hours a night and reads everything sealed in the "
            "Imperial Vault before it is filed. The Empire's enemies say his confidence is a "
            "perfectly polished facade — and so far they have been wrong."
        ),
    },
    {
        "name": "Moon-Queen Thessaline of the Tides",
        "race": "High-Elf",
        "role": "Moon-Queen of the Veiled Realms",
        "nation": "veiled-realms",
        "location": "Niratha",
        "personality": "Quiet, patient, listens longer than is comfortable before answering.",
        "motivation": "See the next Eclipse-Rite sung before her own time ends.",
        "quirks": "Dreams the name of each new moon a fortnight before it rises; her dreams have not erred in two centuries.",
        "background": (
            "Thessaline ascended the Moon Throne at Niratha during the last full lunar conjunction "
            "and is expected to abdicate at the next. She rarely leaves the Twilight Court but "
            "every Eclipse she walks the entire shore of the Crescent alone, refusing escort."
        ),
    },
]


# ─────────────────────────────────────────────────────────────────────────
# NOBLES — three per nation capital, each with a clear court function.
# ─────────────────────────────────────────────────────────────────────────
NOBLES = [
    # Ammeonon — Wymroost
    {
        "name": "Lord Edran of House Wymrose",
        "race": "Human",
        "role": "Lord of the Harbour Fortunes",
        "nation": "ammeonon",
        "location": "Wymroost",
        "personality": "Hearty, generous in public, ruthlessly precise in his ledger.",
        "motivation": "Own the harbour duties of Wymroost outright by the next decade.",
        "quirks": "Wears a coin from every nation he has out-bargained on a chain at his throat.",
        "background": (
            "Cousin to the Empress and master of the port's shipyards. Edran can ruin a rival's "
            "season with a single signature; he uses the threat far more than the act."
        ),
    },
    {
        "name": "Lady Elaine of the Pearled Hand",
        "race": "Human",
        "role": "Patron of the Wemorth Academy",
        "nation": "ammeonon",
        "location": "Wymroost",
        "personality": "Sharp-tongued in private, breathtakingly courteous in court.",
        "motivation": "Keep the Academies independent of the imperial purse — even at her own cost.",
        "quirks": "Has never been seen without her left hand sheathed in pearl-stitched silk; the reason is hers alone.",
        "background": (
            "House Pearled trades in rare arcane materials and underwrites half the Wemorth roster. "
            "Elaine's lectures on diplomatic etiquette are mandatory for new envoys to Wymroost."
        ),
    },
    {
        "name": "Count Veswin Tallow",
        "race": "Half-Elf",
        "role": "Quiet buyer of shipyards",
        "nation": "ammeonon",
        "location": "Wymroost",
        "personality": "Soft-spoken, asks twice as many questions as he answers.",
        "motivation": "Acquire enough hulls to break House Wymrose's grip on the harbour.",
        "quirks": "Drinks only watered wine; says strong drink loosens the tongue and he prefers other men's.",
        "background": (
            "A minor count who, in the last seven years, has bought controlling stakes in nine "
            "small shipyards along the Central Coast. The Pearl Throne is aware. So is Lord Edran."
        ),
    },
    # Selindori — Aurelion Spires
    {
        "name": "Lord Vendris Goldleaf",
        "race": "Sun-Elf",
        "role": "High Steward of the Crystal Vaults",
        "nation": "selindori",
        "location": "Aurelion Spires",
        "personality": "Meticulous, reserved, never repeats a question.",
        "motivation": "Catalogue every relic in the Vaults before the next eclipse.",
        "quirks": "Files reports in his own invented shorthand; only he and the Sun-Queen can read it.",
        "background": (
            "Has served three monarchs and intends to serve a fourth. The Crystal Vaults answer to "
            "him, and through him to the Sun-Queen — never the other way."
        ),
    },
    {
        "name": "Lady Phyriel Sunmote",
        "race": "Sun-Elf",
        "role": "Envoy-Royal to Ammeonon",
        "nation": "selindori",
        "location": "Aurelion Spires",
        "personality": "Graceful, watchful, smiles only when she has already won.",
        "motivation": "Secure a permanent Selindori embassy in Wymroost without ceding Spires privilege.",
        "quirks": "Carries an unstrung longbow as a walking-stick; will not part with it indoors.",
        "background": (
            "Sister to the late Sun-Consort. Negotiated the present grain-and-silver pact with "
            "Empress Marielle and has not lost a clause to her since."
        ),
    },
    {
        "name": "Baron Ilrien Brightwater",
        "race": "Sun-Elf",
        "role": "Captain of the Solar Watch",
        "nation": "selindori",
        "location": "Aurelion Spires",
        "personality": "Earnest, brave, talks rather less than the troubadours pretend.",
        "motivation": "See the Solar Watch reform without losing its old veterans.",
        "quirks": "Polishes his own sabre; will not have a squire touch the edge.",
        "background": (
            "The Watch guards every gate of the Aurelion Spires. Ilrien took command after his "
            "father fell at the Glasswar and has refused six promotions to the High Council since."
        ),
    },
    # Dhor-Kuldor — Karak Vorn
    {
        "name": "Thane Dargrim Hammerhand",
        "race": "Dwarf",
        "role": "Master of the High Forges",
        "nation": "dhor-kuldor",
        "location": "Karak Vorn",
        "personality": "Loud, boastful, would die for any apprentice and frequently threatens to.",
        "motivation": "See his eldest daughter recognised as the first female Master Smith of Karak Vorn.",
        "quirks": "Names every hammer he forges; refuses to sell to a buyer who cannot pronounce the name.",
        "background": (
            "Master of the seven royal forges. Dargrim's strikes are said to be audible three levels "
            "down on a quiet night."
        ),
    },
    {
        "name": "Thane Kessa Goldbeard",
        "race": "Dwarf",
        "role": "Mistress of the Royal Vaults",
        "nation": "dhor-kuldor",
        "location": "Karak Vorn",
        "personality": "Stern, dry-humoured, almost impossible to fluster.",
        "motivation": "Audit every guildhouse coffer before the next succession.",
        "quirks": "Plaits gold thread through her beard for each oath kept; her beard is now over a foot long.",
        "background": (
            "The only Thane in living memory to refuse a Crown commission — twice. The High King "
            "respects her for it and asks her opinion on every major spending oath."
        ),
    },
    {
        "name": "Reckoner Volgrim the Bound",
        "race": "Dwarf",
        "role": "Speaker for the Deep Clans",
        "nation": "dhor-kuldor",
        "location": "Karak Vorn",
        "personality": "Slow, thoughtful, never speaks in the High King's hall without being addressed.",
        "motivation": "Win a permanent seat for the Deep Clans on the High Council.",
        "quirks": "Bound by an old oath never to look on direct sunlight; wears a slatted iron mask at any threshold above the third level.",
        "background": (
            "Came up from the Iron Deeps as the chosen voice of nine deep-clans. Powerful enough "
            "to be feared at court, polite enough that no one yet has the excuse to act on it."
        ),
    },
    # Aigraels — Astra'Lun
    {
        "name": "Duke Casavir of House Veltrane",
        "race": "High-Elf",
        "role": "Speaker of the Mirrors",
        "nation": "aigraels",
        "location": "Astra'Lun",
        "personality": "Effortlessly charming, never the first to drop a name in conversation.",
        "motivation": "Be the one whose mirror the Emperor consults first, last, and in private.",
        "quirks": "Refuses to be portrayed in any painting; the empire has only sketches of him, all by his own hand.",
        "background": (
            "House Veltrane has provided three Speakers of the Mirrors in the last century. Casavir "
            "is by some distance the most dangerous, precisely because the empire underestimates him."
        ),
    },
    {
        "name": "Duchess Iselys Highvein",
        "race": "High-Elf",
        "role": "Mistress of the Astral Guard",
        "nation": "aigraels",
        "location": "Astra'Lun",
        "personality": "Precise, formal, eats with her sword on the table — always sheathed.",
        "motivation": "Reform the Astral Guard so it answers to the Throne, not the noble houses.",
        "quirks": "Touches the pommel of her sword once before each sentence she means to keep.",
        "background": (
            "The Astral Guard has been suborned by every noble house in turn for two hundred years. "
            "Iselys is the first Mistress in living memory to refuse every bribe — and to publish "
            "the names of those who tried."
        ),
    },
    {
        "name": "Margrave Tavren Pell",
        "race": "Tiefling",
        "role": "Keeper of the Imperial Seals",
        "nation": "aigraels",
        "location": "Astra'Lun",
        "personality": "Quiet, courteous, asks for nothing and remembers everything.",
        "motivation": "See the Seal-Office continue to outlive any one emperor.",
        "quirks": "Carries a small wooden seal of his own design that has never been impressed on any document; what it depicts is unknown.",
        "background": (
            "The only tiefling ever to hold a Margraviate at Astra'Lun. He keeps the Imperial "
            "Seals and the lists of every document they have ever closed. Even the Emperor will "
            "not enter the Seal-Office unannounced."
        ),
    },
    # Veiled Realms — Niratha
    {
        "name": "Lord Carven of the Crescent",
        "race": "High-Elf",
        "role": "Speaker for the Moon-Court",
        "nation": "veiled-realms",
        "location": "Niratha",
        "personality": "Soft-spoken, mournfully witty, never raises a toast he means to keep.",
        "motivation": "Make peace with Selindori without losing the Crescent's old liberties.",
        "quirks": "Always carries a small silvered pebble; says it is the last of his mother's gifts.",
        "background": (
            "Speaks for the Moon-Court at every Selindori embassy. Has refused four marriages and "
            "two duchies, preferring, he says, the long hours of patient sorrow to the short ones "
            "of glory."
        ),
    },
    {
        "name": "Lady Sylinda Twiceshade",
        "race": "Half-Elf",
        "role": "Mistress of the Hush Embassy",
        "nation": "veiled-realms",
        "location": "Niratha",
        "personality": "Watchful, dry-humoured, never the first to disagree in council.",
        "motivation": "Keep the Hush Embassy's old privilege of refusing to write down what is told it.",
        "quirks": "Conducts her business in a different colour each season; black in autumn, blue in winter, etc.",
        "background": (
            "The Hush Embassy is the only office in the Veiled Realms that may speak with foreign "
            "courts without referring the matter to the Moon-Queen. Sylinda has held it for "
            "nineteen years and has never been overruled."
        ),
    },
    {
        "name": "Baron Thennir of Whisperfall",
        "race": "Sea-Elf",
        "role": "Captain of the Silent Watch",
        "nation": "veiled-realms",
        "location": "Niratha",
        "personality": "Patient as a tide, gentle to his Watch, merciless to deserters.",
        "motivation": "Keep the Silent Watch unbribed even as the noble houses test it harder each year.",
        "quirks": "Never crosses a threshold without first listening at it for the count of three.",
        "background": (
            "The Silent Watch guards every door at Niratha and is sworn to speak only by hand-sign "
            "while on duty. Thennir is fluent in the sign-tongue and has trained every captain in "
            "use today."
        ),
    },
]


async def seed_royals_and_nobles(db) -> dict:
    """Idempotently seed all 5 royals + 15 nobles into the given Mongo db.

    Returns `{created, skipped, total_after}` so callers (CLI or HTTP admin
    route) can report it back. Skips any (name, nation) pair already present.
    """
    created = 0
    skipped = 0
    for entry in ROYALS + NOBLES:
        existing = await db.npcs.find_one(
            {"name": entry["name"], "nation": entry["nation"]}, {"_id": 0}
        )
        if existing:
            skipped += 1
            continue
        npc = {
            "id": str(uuid.uuid4()),
            "name": entry["name"],
            "race": entry["race"],
            "role": entry["role"],
            "nation": entry["nation"],
            "location": entry["location"],
            "appearance": "",
            "personality": entry["personality"],
            "motivation": entry["motivation"],
            "background": entry["background"],
            "quirks": entry["quirks"],
            "importance": "royal" if entry in ROYALS else "noble",
            "overall_mood": "neutral",
            "mood_score": 0,
            "status": "alive",
            "status_note": "",
            "companion_of": None,
            "created_by_character_id": None,
            "is_admin_seeded": True,
            "created_by": "seed:royals_and_nobles",
            "created_at": _now_iso(),
            "last_seen_at": _now_iso(),
        }
        await db.npcs.insert_one(npc)
        created += 1
    total_after = await db.npcs.count_documents(
        {"importance": {"$in": ["royal", "noble"]}}
    )
    return {"created": created, "skipped": skipped, "total_after": total_after}


async def main():
    mongo_url = os.environ["MONGO_URL"]
    db_name = os.environ["DB_NAME"]
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    summary = await seed_royals_and_nobles(db)
    print(
        "Royals & nobles seeding complete — "
        f"created: {summary['created']}, "
        f"skipped: {summary['skipped']}, "
        f"total royals+nobles now: {summary['total_after']}."
    )


if __name__ == "__main__":
    asyncio.run(main())
