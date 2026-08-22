"""Seed master-NPC mentors for the Apprenticeships system (Phase 5).

Creates one master NPC per craft per nation (16 crafts × 5 nations = 80 NPCs),
each placed at a thematically appropriate location in that nation. Idempotent:
if an NPC with the same (name, nation) already exists, it is left alone.

Run:
    python /app/backend/seed_master_npcs.py
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


# ---------------------------------------------------------------------------
# Master roster: 16 crafts × 5 nations. Each entry is lore-flavoured for its
# nation. `location` names are real locations that exist in the seeded map.
# ---------------------------------------------------------------------------

MASTERS = {
    # ─── Ammeonon (cosmopolitan, magical, scholarly) ──────────────────────
    "ammeonon": [
        ("smith",       "Brask Cinderhand",      "Human",     "Cinderforge Lane",            "Patient anvilsmith; quenches blades by humming."),
        ("mage",        "Mistress Yelara Vex",   "Half-Elf",  "Wemorth Academy",             "Veiled in star-charts; refuses to teach the fearful."),
        ("bard",        "Old Cael Pennywhistle", "Human",     "The Drunken Dryad",           "Knows 1,007 verses; sings the right one for the right grief."),
        ("surgeon",     "Doctor Imael Quill",    "Human",     "Yhul Academy of Oneirics",    "Wears spectacles he never cleans; never loses a patient to fear."),
        ("scribe",      "Sister Anwen Inkmoor",  "Human",     "The Grand Archives",          "Mute by oath; teaches by guided hand."),
        ("alchemist",   "Master Tholm Briarsap", "Halfling",  "Botanical Workshop",          "Smells of mint and lightning; tastes everything."),
        ("ranger",      "Warden Selene Briarfox","Wood-Elf",  "Heartgrove Conclave",         "Walks the boundary moss-shod; speaks to crows."),
        ("scholar",     "Magister Orlon Pell",   "Human",     "Scholar's Sanctum",           "Argues with statues; cites three books per sentence."),
        ("duelist",     "Lady Veska of Pearlstrand","Human",  "Pearlstrand Promenade",       "Wears one earring; the other is buried with a rival."),
        ("priest",      "Father Esmod the Patient","Human",   "Silver Moon Inn",             "Will marry you, bury you, or talk you out of either."),
        ("shadowblade", "Whisper-Kael Drenn",    "Half-Elf",  "Hastburn Alley",              "Never names a price aloud; pupils pay in promises."),
        ("navigator",   "Captain Mara Saltlung", "Human",     "The Grand Docks",             "Tattooed with every coast she has rounded."),
        ("loremaster",  "Curator Lior Sennevar", "Tiefling",  "Vault of Echoes",             "Smells of vellum; remembers your grandfather's name."),
        ("tailor",      "Madame Hessia Loom",    "Human",     "The Flower Market",           "Dresses queens by day, dancers by night."),
        ("huntsman",    "Greyhound-Tev",         "Human",     "Glade of Whispers",           "Goes barefoot in any weather; calls his dogs 'cousins.'"),
        ("courier",     "Swift-Foot Jenna",      "Halfling",  "Floating Lantern Street",     "Has never lost a letter; refuses to read them."),
    ],

    # ─── Selindori (radiant, druidic, watery, golden) ─────────────────────
    "selindori": [
        ("smith",       "Tamarin Goldhammer",    "Sun-Elf",   "The Living Armory",           "Folds gold into steel; refuses to forge for cowards."),
        ("mage",        "Lyra Sunmote",          "Sun-Elf",   "The Auric Archive",           "Speaks only at midday; her shadow is shaped like a leaf."),
        ("bard",        "Wynn Rootsong",         "Wood-Elf",  "Rootsong Walk",               "Tunes a harp made from a fallen guardian tree."),
        ("surgeon",     "Branch-Mother Iselle",  "Wood-Elf",  "The Healing Springs",         "Stitches with thorn-needle; refuses payment from the poor."),
        ("scribe",      "Scribe Devnan Reedwright","Human",   "Watershrine of Devdan",       "Writes only on river-soaked vellum; ink is mineral and slow."),
        ("alchemist",   "Mistress Sapfire Olen", "Wood-Elf",  "Sapfire Hall",                "Distils tree-sap into starlight; smells faintly of resin."),
        ("ranger",      "Warden Halric of Fen",  "Half-Elf",  "Fen's Bastion",               "Carries no sword; the forest is his sword."),
        ("scholar",     "Magister Aurelai",      "Sun-Elf",   "The White Archive",           "Has read every line of the Solar Concordance, twice."),
        ("duelist",     "Sir Calderon Dawnward", "Sun-Elf",   "Dawnward Promenade",          "Salutes the sun before every bout; never disarms his student."),
        ("priest",      "High Acolyte Seralinne","Sun-Elf",   "Grand Temple of Seren",       "Voice carries through cloister stone; eyes never blink in prayer."),
        ("shadowblade", "Master Verre of the Shroud","Half-Elf","The Veiled Sanctuary",      "Teaches duty before discipline; teaches discipline before death."),
        ("navigator",   "Tide-Master Olerin",    "Sea-Elf",   "Devdan's Crossing",           "Reads the rivers like other men read maps."),
        ("loremaster",  "Recorder Velsen Hawthorn","Human",   "Hall of Winter Psalms",       "Knows the lineage of every reigning house since the Glasswar."),
        ("tailor",      "Seamstress Anya Rootspun","Wood-Elf","The Bark & Blade",            "Weaves linen with thread of greenest silk-vine."),
        ("huntsman",    "Master Threnvar",       "Wood-Elf",  "The Grove of Fen",            "Hangs no trophy; remembers each kill by name."),
        ("courier",     "Quickwillow Pip",       "Halfling",  "Rippleway",                   "Outpaces river-otters; once delivered a vow before the speaker arrived."),
    ],

    # ─── Dhor-Kuldor (dwarven, forges, runes, deep crafts) ──────────────
    "dhor-kuldor": [
        ("smith",       "Grandmaster Borrik Stoneheart","Dwarf","Master Smith's Hall",      "Three braids in his beard; one for each son lost to the forge."),
        ("mage",        "Runesmith Hilda Emberveil","Dwarf",  "Rune Library",                "Carves spells in stone; refuses to teach the impatient."),
        ("bard",        "Old Drukkin Stoutverse","Dwarf",     "Ironmaster's Hall",           "Sings drinking songs that move armies."),
        ("surgeon",     "Healer Tova Ironvein",  "Dwarf",     "Memorial Wall",               "Carries a hammer beside her bone-saw; uses both."),
        ("scribe",      "Master Engraver Holm",  "Dwarf",     "Great Book Chamber",          "Letters chiselled, never inked; words last for centuries."),
        ("alchemist",   "Master Brewer Falka",   "Dwarf",     "Crystal Caverns",             "Distils dragonfire; her labs have no windows."),
        ("ranger",      "Warden Aelfric Coldgate","Dwarf",    "Northern Watch",              "Has not slept indoors in twelve winters."),
        ("scholar",     "Loremaster Durin Threadbeard","Dwarf","Loremaster's Sanctum",       "Owns the only complete genealogy of the Iron Kings."),
        ("duelist",     "Hand-Captain Brenna Ironguard","Dwarf","Blade Testing Range",       "Bested seventeen challengers; she taught fourteen of them."),
        ("priest",      "High Lithwarden Murik",  "Dwarf",    "Ancestor's Gate",             "Speaks for the dead; the dead, it is said, speak back."),
        ("shadowblade", "Shaft-Master Helga Veindark","Dwarf","Shadowmark Tunnel",           "Trains apprentices in lightless rooms; their first lesson is patience."),
        ("navigator",   "Admiral Krogan Deepkeel","Dwarf",    "Admiral's Tower",             "Knows every reef of the Iron Coast by the sound it makes."),
        ("loremaster",  "Chronicler Bahrim Stoneglass","Dwarf","Hall of a Thousand Pillars", "His memory is the official one; rivals are flattered to be his footnotes."),
        ("tailor",      "Weaver Margit Goldcloth","Dwarf",    "Treasury of Ages",            "Sews ceremonial robes from spider-silk and gold-thread."),
        ("huntsman",    "Slayer Korvel Trollbane","Dwarf",    "Slayer Shrine",               "Eats only what he kills; kills only what he can name."),
        ("courier",     "Runner Inka Quickfoot", "Halfling",  "Patent Office",               "Was orphaned in the Tunnels; outran wolves to be adopted."),
    ],

    # ─── Aigraels (imperial, crown, formal, mirrored) ─────────────────────
    "aigraels": [
        ("smith",       "Imperial Smith Velken Mark", "Human","The Forge of Names",          "Each blade he forges is given a single, secret name."),
        ("mage",        "Archmagus Thalindra of the Veil","High-Elf","The Astral Forum",     "Wears no jewellery; her power leaves marks enough."),
        ("bard",        "Court Bard Reovan Crowsong","Tiefling","The Silent Opera",          "Sings in three voices at once; one of them isn't his."),
        ("surgeon",     "Surgeon-Royal Magnia Vell","Human", "House of Veils",               "Operates by candlelight; her hands have not trembled in forty years."),
        ("scribe",      "Master Scrivener Pell",  "Human",   "Memory Wells",                 "Writes every contract in the dialect of its losing party."),
        ("alchemist",   "Magister Ovain Glassroot","High-Elf","The Gloom Exchange",          "Trades poisons by colour; refuses to label any vial."),
        ("ranger",      "Warden-Captain Cyrene Stormhold","Human","The Old Bastions",        "Has hunted both deer and pretenders to the throne."),
        ("scholar",     "Magnate-Reader Sennar",  "Human",   "The Quiet Spire",              "Reads only by starlight; refuses electric light as discourteous."),
        ("duelist",     "Sir Vorelian Brassoath","Human",    "Field of Standards",           "Has fought twenty-three duels; has lost none and forgiven six."),
        ("priest",      "Crown-Confessor Idris", "Half-Elf", "Pelor Temple",                 "Hears confession at dawn; condemns at dusk; pardons at midnight."),
        ("shadowblade", "Mistress of Mirrors Velka","Tiefling","The Mirror Crypts",          "Trains by candlelight in front of seven mirrors at once."),
        ("navigator",   "Captain Edras Highwind","Human",    "The Iron Ascendant",           "Sails the sky as readily as the sea."),
        ("loremaster",  "Imperial Chronicler Auren","High-Elf","The Ancient Crown",          "Has the Empire's full lineage memorised; tells it to no one."),
        ("tailor",      "Couturier Madame Lorelle","Human",  "The Golden Crown",             "Dresses the court; her invoices are sealed in wax."),
        ("huntsman",    "Master of the Hunt Bram Holter","Human","The Crucible Yards",      "Rides one horse, breeds many; his hounds know him by scent only."),
        ("courier",     "Diplomatic Runner Sevren","Human",  "The Broken Forum",             "Carries treaties unread; brings back signed copies in less than a day."),
    ],

    # ─── Veiled-Realms (lunar, secretive, twilight, hush) ─────────────────
    "veiled-realms": [
        ("smith",       "Forge-Mistress Nyssa Eclipse","Tiefling","Hall of Blades Unseen",   "Forges only by moonlight; her hammer strikes silent."),
        ("mage",        "Moon-Mage Ilthemar",     "Half-Elf","The Orrery of Fate",           "Predicts only what already happens; refuses to forecast hope."),
        ("bard",        "Threnodist Mira of the Crescent","Tiefling","Temple of the Three Phases","Sings dirges so old the gods have forgotten them."),
        ("surgeon",     "Soft-Hand Vael of the Hospice","Sea-Elf","Eclipse Hospice",         "Tends both the dying and the merely sad; teaches both."),
        ("scribe",      "Glass-Scribe Anor",      "Half-Elf","The Memory Vault",             "Engraves on obsidian; copies are charged in tears, not coin."),
        ("alchemist",   "Steward Cinderveil",     "Tiefling","Blackroot Ward",               "Distils silences; her workshop is the quietest place in the realm."),
        ("ranger",      "Stalker Velnen Twiceshadow","Wood-Elf","Whisperfall Path",          "Has walked into both the Lightless Halls and back out."),
        ("scholar",     "Reader-of-Last-Names Orhel","Tiefling","Hall of Last Names",        "Catalogues the dying; weeps no longer."),
        ("duelist",     "Veiled-Blade Suren",    "Half-Elf", "The Trial Maze",               "Fights blindfolded; the blindfold is for the opponent's dignity."),
        ("priest",      "Lunar Hierarch Sephine","High-Elf", "The Moon Queen's Throne",      "Tides obey her; pilgrims do not always."),
        ("shadowblade", "Whisper-Master Korren of the Blackrobes","Half-Elf","The Lightless Halls","Names of his students are unknown even to themselves."),
        ("navigator",   "Tide-Pilot Vela of the Crescent","Sea-Elf","The Tidal Steps",       "Reads moonlight on water like writing on a page."),
        ("loremaster",  "Archivist Mournwell",   "Tiefling","The Grand Archive",             "Knows three lost languages and refuses to speak the fourth."),
        ("tailor",      "Veil-Weaver Madame Olune","Tiefling","Embassy Row",                  "Sews mourning veils that make the wearer briefly unrecognisable."),
        ("huntsman",    "Shadow-Stalker Mirren","Half-Elf",  "The Last Shadow",              "Hunts in twilight only; refuses to hunt at noon as unsporting."),
        ("courier",     "Hush-Runner Anaïse",   "Halfling",  "The Information Exchange",     "Couriers secrets; her own she keeps in a locked drawer she has lost."),
    ],
}


PERSONALITIES = {
    "smith":       ("Stern, methodical, generous with skill but stingy with praise.",  "To forge a blade that outlives the one who wields it."),
    "mage":        ("Cold-burning intellect, impatient with sloppy thinking.",         "To map every joint of the world's hidden mechanism."),
    "bard":        ("Warm, theatrical, fiercely loyal to anyone who sings true.",      "To make a song that survives the singer."),
    "surgeon":     ("Quiet, precise, never flinching at the worst of bodies.",         "To deny death one more patient at a time."),
    "scribe":      ("Unhurried, exact, frowns at smudged ink as at a betrayal.",       "To preserve the right name in the right place."),
    "alchemist":   ("Curious to the point of recklessness, smells of strange smoke.",  "To distil the world into useful drops."),
    "ranger":      ("Patient as moss, brusque with strangers, gentle with beasts.",    "To keep one wild place wild a little longer."),
    "scholar":     ("Argumentative, deeply read, quotes more than they coin.",         "To find the one footnote that overturns the field."),
    "duelist":     ("Courteous as steel, swift as flame, never the first to insult.",  "To die with the salute given before the riposte."),
    "priest":      ("Grave, kind, sees through dishonesty without contempt.",          "To stand between the suffering and the silence."),
    "shadowblade": ("Soft-spoken, watchful; teaches more by absence than presence.",   "To pass on a craft that must not be misused."),
    "navigator":   ("Salt-cured, blunt, tells the truth even when ruinous.",           "To draw a chart of a sea no one has yet named."),
    "loremaster":  ("Slow, dry, dryly funny; remembers everything that was ever true.","To save one fact a year from being forgotten."),
    "tailor":      ("Exacting, glamorous, attentive to a buttonhole as to a vow.",     "To dress someone for the moment they will be remembered for."),
    "huntsman":    ("Plain, weathered, refuses to romanticise the kill.",              "To keep the herd healthy and the table fed."),
    "courier":     ("Bright-eyed, untiring, the keeper of a thousand secrets unread.", "To deliver one letter that changes a life."),
}


async def seed_master_npcs(db) -> dict:
    """Idempotently seed all master NPCs into the given Mongo db.

    Returns a summary `{created, skipped, total_after}` so callers (CLI or
    HTTP admin route) can report it back. Safe to call repeatedly: skips
    any (name, nation) pair already present.
    """
    created = 0
    skipped = 0
    for nation, roster in MASTERS.items():
        for craft, name, race, location, quirk in roster:
            existing = await db.npcs.find_one({"name": name, "nation": nation}, {"_id": 0})
            if existing:
                skipped += 1
                continue
            personality, motivation = PERSONALITIES[craft]
            npc = {
                "id": str(uuid.uuid4()),
                "name": name,
                "race": race,
                "role": f"Master {craft.capitalize()}",
                "nation": nation,
                "location": location,
                "appearance": "",
                "personality": personality,
                "motivation": motivation,
                "background": (
                    f"Decades of practice have made {name} the foremost {craft} of {nation.replace('-', ' ').title()}. "
                    f"Apprentices travel far to study at {location}; few are accepted, fewer still complete the work."
                ),
                "quirks": quirk,
                "importance": "notable",
                "overall_mood": "neutral",
                "mood_score": 0,
                "status": "alive",
                "status_note": "",
                "companion_of": None,
                "created_by_character_id": None,
                "is_admin_seeded": True,
                "created_by": "seed:master_npcs",
                # Custom field used by /api/apprenticeships/mentors:
                "craft": craft,
                "created_at": _now_iso(),
                "last_seen_at": _now_iso(),
            }
            await db.npcs.insert_one(npc)
            created += 1
    total_after = await db.npcs.count_documents({"craft": {"$exists": True, "$ne": None}})
    return {"created": created, "skipped": skipped, "total_after": total_after}


async def main():
    mongo_url = os.environ["MONGO_URL"]
    db_name = os.environ["DB_NAME"]
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    summary = await seed_master_npcs(db)
    print(f"Master NPC seeding complete — created: {summary['created']}, "
          f"skipped (already present): {summary['skipped']}, "
          f"total masters now: {summary['total_after']}.")


if __name__ == "__main__":
    asyncio.run(main())
