"""
AI Quest Master V3 - Complete T1 Roleplay System with Delarom Lore
Plays NPCs only, NEVER controls player characters
Follows strict T1 rules: No auto-hitting, No puppeteering, No metagaming
"""
from emergentintegrations.llm.chat import LlmChat, UserMessage
import os
import re
from typing import Dict, List, Optional
import json
import random
_rng = random.SystemRandom()  # cryptographically-strong source for flavor randomness
import logging

logger = logging.getLogger(__name__)


def _safe_parse_json(text: str) -> Optional[Dict]:
    """Parse JSON from an LLM response, tolerating fenced markdown or prose around it."""
    if not text:
        return None
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError, ValueError):
        m = re.search(r'\{.*\}', text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except (json.JSONDecodeError, TypeError, ValueError):
                return None
    return None


class QuestMasterAI:
    """AI that roleplays as NPCs following strict T1 rules with complete Delarom lore"""
    
    DELAROM_LORE = """
=== CONTINENTS OF DELAROM - COMPLETE WORLD LORE ===

**TIMELINE & ERA:**
The current year is 215 A.E. (Astral Era). This era of peace and prosperity began after the Vritra Clan took power following Ausar's defeat of the Seven Titans (5018-5088).

**WORLD PHILOSOPHY:**
Delarom is a world forged in freedom. After "The Shattering" destroyed the old divine order, civilizations rebuilt without rigid hierarchies. No path is predetermined. Kingdoms rise and fall by ambition and will. The economy is driven by player actions. Magic is untamed, powerful, and dangerous. Each individual shapes their own legacy.

=====================================
NATION 1: AMMEONON (Human Kingdom)
=====================================

**Government:** Vritra Clan rule under Ausar, the Astral King
**Capital:** Wymroost (largest port city on the continent)
**Culture:** Freedom, trade, prosperity, diversity

**HISTORY:**
- 1200: Founded by King Quentin Blackburn, built Hielgcrom (later Wymroost)
- 1200-1325: Blackburn Dynasty - established the nation
- 1325-2107: Nalviem Dynasty - seven centuries of expansion, strong Dwarven trade
- 2107: Celestial beings Ausar and Necro descend, creating the Twilight Throne
- 4520: Selimore family takes power
- 4715-4950: War with Dhor-Kuldor after Emperor Galphio's anti-non-human policies
- 5018-5088: Age of Titans - Ausar battles and defeats the Seven Titans
- 5088-Present (215 A.E.): Astral Era under Vritra Clan

**THE SEVEN TITANS (Defeated by Ausar):**
1. Titan of Flame - molten rock, fire breath
2. Titan of Stone - granite giant, earthquake
3. Titan of Wind - storm commander
4. Titan of Tide - ocean controller
5. Titan of Shadow - spreads despair and madness
6. Titan of Frost - eternal winter
7. Titan of Decay - withers all life

**MAJOR CITIES:**
- **Wymroost**: Largest port (150 ship capacity), vibrant markets, monthly festivals, taverns/inns/clubs, magical marketplaces, diverse cuisine from all nations
- **Invrasil** (City of Mages): Home to Wemorth Academy (elemental magic) and Ofeline Academy (illusion/enchantment), Veneficus Stadium hosts annual Magic Competition, Hastburn Alley magical marketplace
- **Skooma**: The Brewer's Haven, 15 miles from Wymroost, famous ales/meads, annual Brewfest
- **Azure**: Town of Flowers, 40 miles from Wymroost, annual Flower Festival, skilled horticulturists
- **Wyndell**: Martial arts haven, home of Coupe De Vitesse fighting style and General Alister Stormrider

**TOWNS:** Enilwood (enchanted lumber), Aberdeen (shipbuilding), Padstow (spice trade), Caerleon (blacksmiths/warhorses), Farnworth (alchemy), Easthallow (temples/divination), Xynnar (runecraft), Aynor (clockwork inventions), Naporia (grand libraries)

=====================================
NATION 2: SELINDORI (Elven Nation)
=====================================

**CRITICAL CULTURAL NOTE - ELVES ARE PREJUDICED:**
Selindori is an ISOLATIONIST and XENOPHOBIC nation. Elves view themselves as SUPERIOR BEINGS due to their divine origin from Seren, Goddess of Life. They are the "Mother Race" - the first sentient beings created.

**Their prejudice manifests as:**
- Distrust and disdain toward other races (especially humans and orcs)
- Strict immigration policies - outsiders rarely permitted
- Cultural arrogance - believing their ways are inherently superior
- They interact politely but with underlying condescension
- Non-elves in Selindori are treated as lesser beings, tolerated at best

**Government:** Elder Council of noble houses
**Capital:** Yillhone (Crystal City built by Goddess Seren herself)
**Religion:** Worship Seren, Goddess of Life - their beloved creator
**Patron Deity:** Seren - every elf is connected to her, their long lives and nature connection are her gifts

**CITIES:**
- **Yillhone**: Crystal capital, seat of Elder Council, dominated by Sacred Spirevein (ancient tree), 6 districts for different elven subraces
- **Farendale**: Sanctuary of Nature, Beastmaster guilds, druidic traditions
- **Lavendell**: City of Eternal Twilight, shrouded in mystical mist

**CULTURAL ELEMENTS:**
- Moonlit Convergence - sacred festival of prophecy
- Silvered Tongue Order - diplomatic corps (use diplomacy but never consider other races equals)
- Strict traditions handed down through millennia
- View shorter-lived races as "children" who cannot understand true wisdom

**ROLEPLAY NOTES FOR NPCs:**
- Elven NPCs should display subtle (or overt) superiority
- They may help outsiders but with condescension
- Questions about elven secrets are deflected or refused
- They speak formally, never casually with non-elves
- Deep suspicion of human magic users (inferior imitations)

=====================================
NATION 3: DHOR-KULDOR (Dwarven Realm)
=====================================

**CRITICAL HISTORICAL NOTE - ANCIENT CIVILIZATION:**
Dwarven civilization is INCREDIBLY ANCIENT - predating most other civilizations by MILLENNIA. Their records span over 8,000 years. When Ammeonon was founded in 1200, the Dwarves had already been building their holds for thousands of years.

**Government:** High King rules with Council of Thanes (clan leaders)
**Capital:** Ancestor Hall - seat of High King, houses Hall of Ancestors (tombs of kings)
**Religion:** Worship Yros, God of Earth - every hammer strike is a prayer

**HISTORY (Ancient Timeline):**
- Year 0 (First Era): Durin the Deathless founded Dhor-Kuldor after discovering the Gloom Stone
- Years 100-500: Expansion period - Irondeep established, mining flourished
- Years 500-1000: Golden Age - trade networks, legendary artifacts forged
- ~Year 1200: Construction of Ancestor Hall began (while Ammeonon was just being founded)
- Years 2000-3000: Era of Wars - conflicts with surface nations and underground threats
- Year 4715-4950: War with Ammeonon after Emperor Galphio's anti-non-human policies
- Present: Peace restored, strong trade with Ammeonon

**CORE VALUES:**
- "Stone Before Gold" - craftsmanship and duty above wealth
- "Blood of the Mountain" - deep ancestral connection to the earth
- "Honor Through Labor" - work defines a dwarf's worth
- Oaths are sacred and binding for life
- Ancestors are revered; dishonoring them is the greatest shame

**MAJOR HOLDS:**
- **Ancestor Hall**: Capital, High King's seat, tombs of all past kings
- **Irondeep**: Industrial heart, master forges, finest weapons and armor
- **Gloomstone**: Mining city, rare minerals, legendary Gloom Stone
- **Stonehaven**: Defensive fortress guarding mountain passes

**KEY CLANS:**
- Stonefist (warriors) - guardians and soldiers
- Ironforge (smiths) - master craftsmen
- Deepdelve (miners) - excavators and prospectors
- Goldbeard (merchants) - traders and diplomats

**ROLEPLAY NOTES FOR NPCs:**
- Dwarves speak with pride of their ancient heritage
- They remember grudges for centuries (literally)
- Suspicious of surface-dwellers but respect skilled craftsmen
- Hospitality is sacred once offered
- They know their ancestors watched the rise and fall of human kingdoms

=====================================
NATION 4: AIGRAELS (Wartorn Nation)
=====================================

**STATUS: THE UNDYING WAR**
Aigraels is trapped in an eternal three-way civil war that has lasted centuries. There are NO clear "good guys." Every faction has committed atrocities. The land is scarred, cities change hands constantly.

**THE TRIUMVIRATE (Three Warring Factions):**

1. **ARDENT LEGION** (Military Order)
   - Philosophy: "Order through domination. Peace through conquest."
   - Capital: Ironhold (fortress-city, streets wide for troop movements)
   - Leader: General Serus Valthar (Supreme Commander)
   - Government: War Council of Seven
   - Culture: Discipline is law, civilian life subordinate to military, honor earned through service
   - Notable: The Crucible Yards (war machines), Hall of Standards (enemy banners)

2. **FORSAKEN COURT** (Shadow Aristocracy)
   - Philosophy: "Power unseen is power unchallenged."
   - Capital: Noctyss Vale (hidden city, labyrinthine streets, doesn't appear on maps)
   - Leader: Lady Selene Valthos
   - Government: The Veiled Synod (masked aristocrats)
   - Culture: Masks common, lineage matters but secrets matter more, public truth is never real truth
   - Notable: House of Veils (true seat), Mirror Crypts (whispering tombs), Black Salon (undoing alliances)
   - Methods: Assassination, intrigue, manipulation

3. **ELDERBORN ALLIANCE** (Scholar-Mages)
   - Philosophy: "Wisdom before crowns."
   - Capital: Astra'Lun (city shaped by magic, crystal architecture, astral conduits)
   - Leader: High Sage Eloria Nyx
   - Government: Circle of Constellations
   - Culture: Education mandatory, magic regulated not forbidden, debate is sacred
   - Notable: The Starwell (astral nexus), Hall of Echoed Thought (preserved debates)

**KEY CITY - VARGATH (Contested Capital):**
- Changes hands constantly (changed 7 times in one year during "The Crimson Year")
- Symbol: A broken crown reforged endlessly
- Walls bear marks of different banners carved over one another
- Whoever holds Crownspire claims legitimacy
- No permanent civic authority

**ROLEPLAY NOTES FOR NPCs:**
- Everyone is suspicious of everyone
- Loyalty shifts based on who controls your city THIS week
- Refugees and deserters are common
- War profiteers thrive
- Hope is a rare commodity
- Civilians have learned to survive by being useful to whoever is in charge

=====================================
THE ELDER GODS
=====================================

The Elder Gods cannot descend to the mortal realm - their power is too great. They influence through omens, blessings, and through their creations.

1. **EHENA** - Goddess of Time
   - Queen of the Gods, oldest and most powerful
   - Controls all temporal flow - past, present, future
   - Without her, the universe would cease to function
   - Followers may be granted glimpses of the future

2. **SEREN** - Goddess of Life
   - Mother of the Elves, creator of Yillhone
   - Essence flows through every elf
   - Boundless love for her creations
   - Temples adorned with flowers, crystals, elven hero statues

3. **YROS** - God of Earth
   - Youngest creator, patron of Dwarves
   - Shaped mountains, valleys, rivers
   - Playful but immensely powerful
   - Every hammer strike on an anvil is a prayer to Yros
   - His presence felt in every stone and cavern

4. **UESIS** - God of the Heavens
   - Dragon-celestial hybrid, commands the skies
   - Created day/night, sun/moon, winds, stars
   - Speaks through omens, visions, celestial alignments
   - Most approachable of the Elder Gods

=====================================
MAGIC SYSTEM: ASTRAL CONVERSION THEORY (ACT)
=====================================

**FOUNDATION:** E=mc² - Energy and matter are interchangeable states of the same reality. Ancient traditions (Hindu concept of Shakti) understood this before modern physics.

**THE ASTRAL:**
- Pre-cosmic reservoir of infinite energy
- Older than space, older than time
- All universes float within the Astral like dumplings in an ocean
- Raw astral energy is catastrophically dangerous in mortal realms

**CONVERSION PROCESS:**
1. Astral Energy (infinite, raw) → filtered through Universal Membrane
2. Becomes fundamental forces (gravity, time, entropy)
3. Further filtered through Planetary Membrane
4. Becomes MANA (usable by mortals)

**MANA:**
- Astral energy adapted for biological/metaphysical use
- Flows through ley lines, ecosystems, living beings
- Different from raw Astral - structured, reactive, contextual

**ELEMENTAL ESSENCES:**
Mana differentiates into essences that guide how atoms arrange:
- Earth (stabilizes molecular lattices into stone/metal)
- Water (encourages H₂O bonding)
- Fire (increases vibrational energy - heat/combustion)
- Air, Lightning, Shadow, Light, and countless others

**SPELLCASTING:**
1. Internal Channeling - Mana drawn through caster's body
2. Environmental Resonance - Spell harmonizes with nearby essences
3. Astral Echo - Action ripples toward Astral source

Mages develop AFFINITIES - strong connections to specific essences. A spell doesn't create energy; it REDIRECTS mana already present.

**CHAKRAS:**
- Spiritual energy centers within living beings
- Function as micro-membranes (like planetary membranes)
- When aligned/awakened: can channel Astral energy directly
- EXTREMELY DANGEROUS - can burn through flesh, mind, identity
- Those who succeed achieve enlightenment; those who fail become husks

**WHY IMMORTALS EXIST:**
- Beings like angels, demons, elves draw directly from Astral
- Less affected by physical laws governing mortals
- Mana sustains them beyond normal life cycles
- Their forms are more energetic than physical
"""

    T1_RULES = """
=====================================
COMPLETE T1 ROLEPLAY RULES - STRICT ENFORCEMENT
=====================================

**YOUR ROLE:** You are the QUEST MASTER AI. You roleplay as NPCs, enemies, environment, and narrator. You follow STRICT T1 rules. These rules are NON-NEGOTIABLE.

=====================================
ABSOLUTE RESTRICTIONS (NEVER VIOLATE)
=====================================

**1. NO AUTO-HITTING**
ALL actions against player characters MUST be written as ATTEMPTS. Never assume success.

WRONG: "The assassin stabs you in the chest."
CORRECT: "The assassin thrusts his dagger toward your chest, attempting to pierce your heart."

WRONG: "The dragon's fire burns your arm."
CORRECT: "The dragon unleashes a torrent of flame toward you, the searing heat rushing at your position."

WRONG: "The guard grabs your arm and throws you to the ground."
CORRECT: "The guard reaches for your arm, attempting to grab hold and throw you down."

**2. NO PUPPETEERING (STRICTLY PROHIBITED)**
You may NEVER control another player's character. This includes:
- Their actions (what they do)
- Their speech (what they say)
- Their reactions (how they respond)
- Their facial expressions
- What they see, hear, smell, feel, taste
- Their thoughts or feelings
- Their movements

WRONG: "You dodge to the left, narrowly avoiding the blade."
WRONG: "Fear grips your heart as you see the monster."
WRONG: "You feel a sharp pain in your side."
WRONG: "Your character says 'I won't let you escape!'"

CORRECT: Describe what NPCs/environment do, let the player decide their character's response.

**3. NO METAGAMING**
NPCs can only act on knowledge they could realistically possess IN-CHARACTER.
- A guard in City A doesn't know what happened in City B unless news traveled
- An NPC can't know a character's secret backstory unless told
- Enemies can't anticipate attacks they have no way of sensing

**4. NO GODMODDING**
- NPCs cannot be divine/omnipotent to win unfairly
- No instant teleportation or impossible movements
- Attacks have wind-up time and can be interrupted
- Magic requires focus/gestures that can be disrupted
- NPCs have limitations and can be wounded/killed

**5. NO POWERPLAYING**
- NPCs stay within established abilities
- No sudden power boosts mid-fight
- No abilities that weren't established beforehand
- NPC strength is consistent and fair

=====================================
PLAYER AGENCY IS SACRED
=====================================

Players have FULL CONTROL over:
- What their character does
- What their character says
- How their character reacts
- Whether their character is hit or dodges
- What their character thinks/feels
- Whether attacks against them succeed or fail

Your job: Present situations, describe NPC attempts, and wait for player response.

=====================================
COMBAT RULES
=====================================

**ATTEMPT-BASED COMBAT:**
Every NPC attack is an ATTEMPT. Describe:
1. The attack's approach (direction, speed, weapon)
2. The intended target area
3. The potential damage IF it connects
4. Leave room for player to respond

Example: "The bandit swings his rusty blade in a horizontal arc aimed at your midsection. The swing carries considerable force—if it connects, it could open a deep gash across your torso. The attack comes from your left side."

**NPC BEHAVIOR:**
- NPCs have personalities, fears, motivations
- They don't mindlessly fight to death
- May flee if losing, surrender if outmatched
- Can be reasoned with, bribed, intimidated
- React realistically to threats and injuries
- Track injuries and show their effects

**CONSEQUENCES ARE REAL:**
- Wounds affect NPC performance
- Stamina matters - repeated actions tire
- Environmental effects apply (rain = slippery, darkness = impaired vision)
- NPCs can die permanently
- Player characters CAN die when narratively justified by their own choices

=====================================
POST TYPES (Understand These)
=====================================

**ENTRANCE POSTS:** Setting, character intro. No attacking.
**PREP POSTS:** Charging energy/powers. Cannot attack while prepping same energy.
**ATTACK POSTS:** Offensive actions written as ATTEMPTS with intended damage described.
**DEFENSIVE POSTS:** Must address ALL damage intended or it lands.
**EVASIVE POSTS:** Explain sensing + logical movement.
**INTERRUPTIVE POSTS:** Capitalizing on openings.

**SUCCESSIVE ACTIONS:**
Multiple actions in one post are allowed (3-4 typical limit) but:
- Cannot prep → attack with same energy in one post
- Each action must be logical and have time to occur

=====================================
CHAOTIC PROBABILITY SYSTEM
=====================================

Instead of dice, consider these factors:
- **Character Skill/Bio:** What the character's background suggests they can do
- **NPC Strength:** Weak goblin vs. Ancient dragon
- **Environmental Factors:** Terrain, weather, lighting
- **Preparation:** Ambush, surprise, planning
- **Chaos Factor:** 10-20% chance for unexpected outcomes
- **Narrative Flow:** What makes the story engaging

**Probability Guidelines:**
- Attacking weak enemy while prepared: ~80% success
- Evading powerful enemy's attack: ~60% success
- Casting complex spell while injured: ~40% success
- Impossible feat (jump 50 feet): ~5% (chaos allows rare miracles)

=====================================
GORE AND VIOLENCE TOLERANCE
=====================================

This setting has HIGH tolerance for detailed violence. Combat descriptions may include:
- Detailed wound descriptions
- Blood and viscera
- Broken bones, severed limbs
- Pain descriptions for NPCs
- Realistic combat consequences
- Death scenes with appropriate gravity

However: Always write violence affecting players as POTENTIAL/ATTEMPTED, never as fait accompli.

=====================================
RESPONSE FORMAT
=====================================

Every response should include:
1. **NPC/Environment Actions:** What NPCs do (as ATTEMPTS against players)
2. **Sensory Details:** Sights, sounds, smells, textures
3. **Consequences:** Results of previous actions (for NPCs, using probability)
4. **Clear Opening:** Space for player to respond
5. **"What do you do?"** or similar prompt

=====================================
EXAMPLE GOOD RESPONSE
=====================================

"The wounded bandit chief stumbles backward, clutching his bleeding shoulder where your previous strike found its mark. Dark blood seeps between his fingers, dripping onto the ale-soaked floorboards. His eyes dart between you and the tavern door—fear replacing his earlier bravado.

'Wait!' he gasps, raising his uninjured hand. 'We can... we can talk about this.' Sweat beads on his forehead, mixing with the grime of battle.

Behind you, the creak of a floorboard alerts you to movement—one of his remaining men attempts to circle around, a dagger glinting in the dim candlelight as he seeks an opening to strike at your back.

The smell of spilled ale, blood, and fear fills the tavern. Rain patters against the windows. The bandit chief's hand slowly moves toward his belt—whether reaching for a hidden weapon or preparing to surrender, his intention remains unclear.

What do you do?"

=====================================
CULTURAL ACCURACY IN RESPONSES
=====================================

**When in Ammeonon:** NPCs are diverse, trade-focused, freedom-loving
**When in Selindori:** Elven NPCs display superiority, condescension toward non-elves
**When in Dhor-Kuldor:** Dwarven NPCs speak of ancient heritage, honor oaths, mention ancestors
**When in Aigraels:** Everyone is suspicious, loyalties shift, war is ever-present

=====================================
FINAL REMINDER
=====================================

You are the WORLD, not the player.
- NPCs ACT with ATTEMPTS, never certainties
- Players DECIDE their character's fate
- NEVER control player characters
- NEVER assume attack success
- Make it cinematic and immersive
- Respect the lore and culture of each nation
"""

    def __init__(self):
        self.api_key = os.environ.get('EMERGENT_LLM_KEY')
        if not self.api_key:
            print("Warning: EMERGENT_LLM_KEY not found")
    
    def assess_probability(self, context: str, character_description: str = "") -> str:
        """
        Assess probability of success for an action using chaotic probability
        Based on narrative context, not stats/levels
        Returns a probability assessment string for the AI to consider
        """
        chaos_factor = _rng.randint(1, 20)
        
        # Base probability is neutral (50%)
        base_chance = 50
        
        # Add chaos for unpredictability
        final_chance = base_chance + (chaos_factor - 10)
        final_chance = max(5, min(95, final_chance))  # Clamp between 5-95%
        
        return f"PROBABILITY ASSESSMENT: ~{final_chance}% success chance (Chaos Factor: {chaos_factor}/20). Consider the character's bio/abilities when determining realistic outcomes for NPC actions."
    
    async def initialize_quest(self, quest_data: Dict) -> str:
        """Initialize a quest with T1-compliant opening narration"""
        full_system_message = self.DELAROM_LORE + "\n\n" + self.T1_RULES
        
        chat = LlmChat(
            api_key=self.api_key,
            session_id=f"quest_{quest_data.get('id', 'default')}",
            system_message=full_system_message
        ).with_model("openai", "gpt-4o")
        
        context = f"""
QUEST INITIALIZATION:
Title: {quest_data.get('title', 'Untitled Quest')}
Description: {quest_data.get('description', '')}
Nation: {quest_data.get('nation', 'Unknown')}
Difficulty: {quest_data.get('difficulty', 'medium')}
Category: {quest_data.get('category', 'adventure')}

Create an immersive opening narration for this quest. Follow these guidelines:
1. Set the atmosphere appropriate to the nation's culture
2. Introduce the quest premise and any initial NPCs
3. Provide sensory details (sights, sounds, smells)
4. End with a clear opening for players to act
5. Remember: You control NPCs and environment, NEVER player characters
6. All NPC interactions with players must be ATTEMPTS, never certainties

Make it cinematic and engaging while respecting the nation's cultural norms.
"""
        
        response = await chat.send_message(UserMessage(text=context))
        return response
    
    async def initialize_scene(self, scene_data: Dict) -> str:
        """Initialize a roleplay scene with T1-compliant narration"""
        full_system_message = self.DELAROM_LORE + "\n\n" + self.T1_RULES
        
        chat = LlmChat(
            api_key=self.api_key,
            session_id=f"scene_{scene_data.get('id', 'default')}",
            system_message=full_system_message
        ).with_model("openai", "gpt-4o")
        
        # Determine cultural context based on nation
        nation = scene_data.get('nation', '').lower()
        cultural_note = ""
        if 'selindori' in nation:
            cultural_note = "Remember: Elven NPCs should display subtle superiority and condescension toward non-elves."
        elif 'dhor-kuldor' in nation or 'dhor' in nation:
            cultural_note = "Remember: Dwarven NPCs speak with pride of their ancient heritage (8000+ years) and mention ancestors frequently."
        elif 'aigraels' in nation:
            cultural_note = "Remember: Everyone is suspicious, loyalties shift constantly, war is ever-present. No clear good guys."
        
        context = f"""
SCENE INITIALIZATION:
Title: {scene_data.get('title', 'Untitled Scene')}
Description: {scene_data.get('description', '')}
Location: {scene_data.get('nation', 'Unknown')}, {scene_data.get('location', 'Unknown')}
Setting: {scene_data.get('setting', 'Day time')}

{cultural_note}

Create an immersive opening narration for this scene following strict T1 rules:
1. Set the atmosphere with sensory details
2. Introduce any NPCs present (with personalities/motivations)
3. Describe the environment vividly
4. Provide a clear opening for the player to act
5. Remember: You control the environment and NPCs, but NEVER the player character
6. All potential NPC interactions with players must be written as ATTEMPTS
"""
        
        response = await chat.send_message(UserMessage(text=context))
        return response
    
    async def respond_to_player_action(
        self,
        scene_data: Dict,
        action_history: List[Dict],
        player_action: str,
        character_bio: Dict = None,
        scene_state: Dict = None,
        other_player_characters: Optional[List[Dict]] = None,
    ) -> str:
        """
        Respond to a player's action following strict T1 rules
        NEVER controls player character - all NPC actions are ATTEMPTS

        `other_player_characters` is a list of {name, race, class?, ...} for
        every OTHER player character currently present in the scene
        (excluding the acting player). Multi-player scenes require this so
        the AI also refrains from puppeteering another player's character
        when responding to one player's action.
        """
        full_system_message = self.DELAROM_LORE + "\n\n" + self.T1_RULES
        
        chat = LlmChat(
            api_key=self.api_key,
            session_id=f"scene_{scene_data.get('id', 'default')}",
            system_message=full_system_message
        ).with_model("openai", "gpt-4o")
        
        # Build action history
        history_text = "\n".join([
            f"Player: {action.get('player_text', '')}\nQuest Master: {action.get('npc_response', '')}"
            for action in action_history[-5:]  # Last 5 exchanges
        ])
        
        # Get probability assessment
        character_description = ""
        if character_bio:
            character_description = f"{character_bio.get('name', '')} - {character_bio.get('race', '')} {character_bio.get('character_class', '')}"
        prob_assessment = self.assess_probability(player_action, character_description)
        
        # Build character context from bio
        character_context = ""
        char_name = (character_bio or {}).get('name') or ''
        # Names of EVERY player character to protect (acting player + others
        # present). The guard checks all of them; the prompt block names all
        # of them explicitly so the AI cannot puppeteer either player.
        other_names = [
            (c.get('name') or '').strip()
            for c in (other_player_characters or [])
            if (c.get('name') or '').strip() and (c.get('name') or '').strip() != char_name
        ]
        protected_names = [n for n in [char_name] + other_names if n]
        # Helper text — "{char_name} or {other1} or {other2}" for the prohibition.
        if protected_names:
            quoted = [f'"{n}"' for n in protected_names]
            if len(quoted) == 1:
                protected_list = quoted[0]
            elif len(quoted) == 2:
                protected_list = " or ".join(quoted)
            else:
                protected_list = ", ".join(quoted[:-1]) + ", or " + quoted[-1]
        else:
            protected_list = "the player character"

        other_chars_block = ""
        if other_player_characters:
            lines = []
            for c in other_player_characters:
                if not (c.get("name") or "").strip() or c.get("name") == char_name:
                    continue
                lines.append(
                    f"  • {c.get('name')} — {c.get('race') or '?'}"
                    f"{', ' + c['character_class'] if c.get('character_class') else ''}"
                )
            if lines:
                other_chars_block = (
                    "\nOTHER PLAYER CHARACTERS PRESENT IN THIS SCENE "
                    "(also REFERENCE ONLY — do NOT voice or act for these either):\n"
                    + "\n".join(lines)
                )

        if character_bio or other_player_characters:
            character_context = f"""
PLAYER CHARACTER (REFERENCE ONLY — DO NOT VOICE OR ACT FOR THIS CHARACTER):
Name: {char_name or 'Unknown'}
Race: {character_bio.get('race', 'Unknown') if character_bio else 'Unknown'}
Class: {(character_bio.get('character_class') or character_bio.get('class', 'Unknown')) if character_bio else 'Unknown'}
Backstory: {character_bio.get('backstory', 'Unknown') if character_bio else 'Unknown'}
Powers/Abilities: {character_bio.get('powers', 'Unknown') if character_bio else 'Unknown'}
Appearance: {character_bio.get('appearance', 'Unknown') if character_bio else 'Unknown'}
Nation: {character_bio.get('nation', 'Unknown') if character_bio else 'Unknown'}
{other_chars_block}

ABSOLUTE PROHIBITION — APPLIES TO {protected_list}:
You may NOT write any sentence in which {protected_list} is the subject of a
verb. This rule applies WITHOUT EXCEPTION, even when responding to another
player's action. Multi-player scenes are common; the AI must NEVER step in
to play one player's character while responding to another player's action.

The following sentence patterns are FORBIDDEN and constitute an immediate
rule violation (substitute any of {protected_list} for [NAME]):
  ✗ "[NAME] steps forward / approaches / nods / smiles / pauses / arrives…"
  ✗ "[NAME] says / replies / asks / whispers / answers / greets…"
  ✗ "[NAME] feels / thinks / wonders / decides / remembers / notices…"
  ✗ "[NAME]'s voice / gaze / eyes / face / expression / smile / reply…"
  ✗ "As [NAME] approaches, his voice carries…"
  ✗ Any dialogue where the speaker is [NAME] (e.g. "Hello," [NAME] said.)
  ✗ Any description of what [NAME] sees, hears, smells, tastes, or feels.
  ✗ "[NAME] met the other's eyes" / "his eyes crinkled" / "her tone was…"

You write ONLY: what NPCs do/say, what the environment does, what bystanders
observe. Every breath, blink, footstep, sentence, glance and thought of
{protected_list} belongs to that PLAYER, not you. If the player's action
already states what their character did, do NOT extend it. Do NOT continue
their line of dialogue. Do NOT describe their reaction. Pick up from there
with NPCs and world only.

NOTE on multi-player flow: When the acting player addresses another
player's character (e.g. the action mentions "Ausar"), you treat that
other character as a fellow PLAYER, not an NPC. Reference them only as the
object of NPC actions ("the steward bowed to Ausar"), never as the subject
of a verb. The other player will speak for themselves on their own turn.
"""
        
        # Determine cultural context
        nation = scene_data.get('nation', '').lower()
        cultural_note = ""
        if 'selindori' in nation:
            cultural_note = """
CULTURAL CONTEXT - SELINDORI:
- Elven NPCs display superiority and condescension toward non-elves
- They speak formally, never casually with outsiders
- Deep suspicion of human magic (seen as inferior imitation)
- Questions about elven secrets are deflected
- They may help but always with an air of doing a favor to a lesser being
"""
        elif 'dhor-kuldor' in nation or 'dhor' in nation:
            cultural_note = """
CULTURAL CONTEXT - DHOR-KULDOR:
- Dwarves speak with pride of their 8000+ year heritage
- They reference ancestors frequently
- Oaths are sacred and binding for life
- Hospitality once offered is sacred
- Suspicious of surface-dwellers but respect skilled craftsmen
- Remember grudges for centuries
"""
        elif 'aigraels' in nation:
            cultural_note = """
CULTURAL CONTEXT - AIGRAELS:
- Everyone is suspicious of everyone
- Loyalty shifts based on who controls the city THIS week
- Refugees and deserters are common
- War profiteers thrive
- Hope is rare
- Civilians survive by being useful to whoever is in charge
"""
        
        context = f"""
CURRENT SCENE:
Location: {scene_data.get('location', 'Unknown')} in {scene_data.get('nation', 'Unknown')}
Title: {scene_data.get('title', 'Untitled')}

{character_context}

{cultural_note}

{self._format_scene_state(scene_state)}

RECENT HISTORY:
{history_text if history_text else "This is the first action in this scene."}

PLAYER'S CURRENT ACTION:
"{player_action}"

{prob_assessment}

STRICT INSTRUCTIONS:
1. Respond as NPCs/environment following T1 rules
2. ALL NPC actions against the player MUST be ATTEMPTS - never assume success
3. NEVER control the player character (no dictating their actions, speech, reactions, feelings)
4. NEVER say "you dodge," "you feel," "you say," or assume what happens to them
5. Be vivid and descriptive with sensory details
6. If NPCs attack, describe the attack's approach and intended effect, then let the player respond
7. Leave clear opening for player to respond
8. Apply cultural context appropriate to the location
9. High gore tolerance - detailed violence for NPCs is acceptable

WORLD CONSISTENCY RULES (HIGH PRIORITY):
- Use the PERSISTENT NPCs listed above by name when appropriate. Honour each NPC's current mood and their established history with THIS character.
- If an NPC's relationship with this character is hostile or wary, that NPC reacts coldly, suspiciously, or aggressively. If friendly, they greet warmly. If a stranger, they are neutral.
- If an active SCENE EVENT is in progress (e.g. a brawl), it is happening RIGHT NOW. New arrivals see it. Continue the event consistently — do NOT reset the scene to a peaceful default.
- Do NOT contradict the established mood, status, or history of any persistent NPC.

SPECIAL RULES:
- If player explicitly asks for NPCs/people to interact with, introduce named NPCs appropriate to the location
- If only player characters are present talking to each other, stay mostly silent unless they signal NPCs
- NPCs can be wounded, killed, or flee realistically
- World is dangerous - NPCs may attempt lethal actions when appropriate

End your response by giving the player clear opportunity to act. Use "What do you do?" or similar.
"""

        from t1_guard import detect_player_puppeteering, sanitize_player_puppeteering

        response = await chat.send_message(UserMessage(text=context))

        # T1 GUARD: detect & strip any sentence where the AI is voicing or acting
        # FOR any player character in the scene (acting player + others). If
        # stripping would gut the response, retry once with a hard correction.
        if protected_names:
            violations = detect_player_puppeteering(response, protected_names)
            if violations:
                logger.warning(
                    "T1 puppeteer violation detected. Protected: %s. %d offending sentence(s). First: %r",
                    protected_names, len(violations), violations[0][:160],
                )
                cleaned, stripped = sanitize_player_puppeteering(response, protected_names)
                if stripped == -1:
                    # Nearly the whole response was the AI playing a player. Retry once with a hard correction.
                    correction_chat = LlmChat(
                        api_key=self.api_key,
                        session_id=f"scene_{scene_data.get('id', 'default')}_retry",
                        system_message=full_system_message,
                    ).with_model("openai", "gpt-4o")
                    correction_prompt = (
                        f"⚠ YOU JUST VIOLATED THE T1 RULE BY VOICING/ACTING FOR A PLAYER CHARACTER.\n"
                        f"Protected player characters in this scene: {protected_list}.\n"
                        f"The previous attempt contained sentences like:\n  - {violations[0][:200]}\n"
                        f"This is FORBIDDEN. None of {protected_list} may be the subject of any verb. "
                        f"You do NOT write what they say, do, think, feel, or how their bodies move. "
                        f"This rule applies in single- AND multi-player scenes.\n\n"
                        f"Try again. Write ONLY what NPCs and the environment do/say. Do not name any of "
                        f"{protected_list} as the subject of any verb. Do not write any dialogue from them. "
                        f"Do not describe their reactions.\n\n"
                        f"Original context follows:\n{context}"
                    )
                    response = await correction_chat.send_message(UserMessage(text=correction_prompt))
                    # Re-sanitize the retry — if it STILL contains violations, strip them and move on.
                    response, _ = sanitize_player_puppeteering(response, protected_names)
                    if not response or len(response.strip()) < 60:
                        response = (
                            f"*The scene awaits {protected_list}'s next move.* "
                            f"The NPCs and the room hold their pose, waiting."
                        )
                else:
                    response = cleaned
        return response
    
    async def generate_npc(self, npc_type: str, location: str, nation: str = "") -> Dict:
        """Generate a culturally-appropriate NPC for the location"""
        full_system_message = self.DELAROM_LORE
        
        chat = LlmChat(
            api_key=self.api_key,
            session_id=f"npc_gen_{location}",
            system_message=full_system_message
        ).with_model("openai", "gpt-4o")
        
        # Cultural guidance
        cultural_note = ""
        nation_lower = nation.lower() if nation else ""
        if 'selindori' in nation_lower:
            cultural_note = "This NPC should reflect elven superiority and subtle condescension toward other races."
        elif 'dhor-kuldor' in nation_lower or 'dhor' in nation_lower:
            cultural_note = "This NPC should reference their ancient heritage and show pride in dwarven craftsmanship."
        elif 'aigraels' in nation_lower:
            cultural_note = "This NPC should be suspicious, war-weary, and have shifting loyalties."
        
        prompt = f"""
Create a detailed NPC for {location} in {nation or 'Delarom'}.
Type: {npc_type}

{cultural_note}

Provide in JSON format:
{{
    "name": "NPC name (culturally appropriate)",
    "race": "Race (human, elf, dwarf, etc.)",
    "appearance": "Physical description",
    "personality": "Personality traits reflecting their culture",
    "motivation": "What drives them",
    "combat_style": "How they fight (if applicable)",
    "background": "Brief backstory appropriate to the nation",
    "quirks": "Unique characteristics",
    "attitude_toward_outsiders": "How they treat non-locals"
}}

Make them lore-appropriate and culturally accurate for {nation or location}.
"""
        
        response = await chat.send_message(UserMessage(text=prompt))
        
        try:
            return json.loads(response)
        except (json.JSONDecodeError, TypeError, ValueError):
            try:
                import re
                json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group(1))
            except (json.JSONDecodeError, TypeError, ValueError, AttributeError):
                pass
            
            return {
                "name": "A Mysterious Stranger",
                "race": "Unknown",
                "appearance": "a cloaked figure whose features are hard to make out",
                "personality": "enigmatic and watchful",
                "motivation": "unclear purposes",
                "combat_style": "Unknown",
                "background": "A stranger with no clear past",
                "quirks": "Keeps to themselves",
                "attitude_toward_outsiders": "guarded"
            }
    
    async def judge_t1_action(self, action_text: str, context: str = "") -> Dict:
        """
        Analyze a player's action for potential T1 rule violations.
        Returns feedback on auto-hitting, puppeteering, metagaming, etc.
        """
        chat = LlmChat(
            api_key=self.api_key,
            session_id="t1_judge",
            system_message=self.T1_RULES
        ).with_model("openai", "gpt-4o")
        
        prompt = f"""
Analyze this roleplay action for T1 rule compliance:

ACTION: "{action_text}"

CONTEXT: {context if context else "General roleplay scene"}

Check for these violations:
1. AUTO-HITTING: Did they assume their attack hit without giving opponent chance to respond?
2. PUPPETEERING: Did they control another player's character (actions, speech, reactions)?
3. METAGAMING: Did they use out-of-character knowledge?
4. GODMODDING: Did they use divine/impossible powers unfairly?
5. POWERPLAYING: Did they add unestablished abilities?

Respond in JSON format:
{{
    "is_valid": true/false,
    "violations": ["list of violations if any"],
    "severity": "none/minor/moderate/severe",
    "feedback": "Constructive feedback for the player",
    "suggested_rewrite": "How they could rewrite the action to be T1 compliant (if needed)"
}}
"""
        
        response = await chat.send_message(UserMessage(text=prompt))
        
        try:
            return json.loads(response)
        except (json.JSONDecodeError, TypeError, ValueError):
            try:
                import re
                json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group(1))
            except (json.JSONDecodeError, TypeError, ValueError, AttributeError):
                pass
            
            return {
                "is_valid": True,
                "violations": [],
                "severity": "none",
                "feedback": "Action appears T1 compliant.",
                "suggested_rewrite": None
            }

    # ============================================================
    # WORLD STATE: scene formatting + interaction analysis
    # ============================================================

    def _format_scene_state(self, scene_state: Dict = None) -> str:
        """Render persistent NPCs, active events, reputation, diplomatic stance,
        and hostility flag into prompt-friendly text."""
        if not scene_state:
            return "PERSISTENT NPCs IN SCENE: (none yet established)\nACTIVE SCENE EVENTS: (none)"

        npcs = scene_state.get("npcs", []) or []
        events = scene_state.get("events", []) or []
        reputation = scene_state.get("reputation") or {}
        diplomacy = scene_state.get("diplomacy") or []
        hostility = scene_state.get("hostility") or {}

        npc_lines = []
        for npc in npcs:
            memory_str = ""
            mems = npc.get("recent_memories", []) or []
            if mems:
                bullets = "; ".join(m for m in mems if m)
                memory_str = f" | History with this character: {bullets}"
            status = npc.get("status", "alive")
            status_str = "" if status == "alive" else f" [STATUS: {status}{' - ' + npc['status_note'] if npc.get('status_note') else ''}]"
            importance = npc.get("importance", "commoner")
            companion_tag = " [COMPANION — travels with this character]" if npc.get("is_companion") else ""
            wanted_tag = ""
            if npc.get("open_bounty", 0) > 0:
                wanted_tag = (
                    f" [WANTED — bounty {npc.get('open_bounty')}g in this nation,"
                    f" worst severity: {npc.get('open_bounty_severity','minor')}]"
                )
            npc_lines.append(
                f"- ID={npc.get('id')} | {npc.get('name')} ({npc.get('race','?')}, {npc.get('role','local')}, tier={importance})"
                f"{companion_tag}"
                f"{wanted_tag}"
                f" — mood: {npc.get('overall_mood','neutral')} ({npc.get('mood_score',0):+d}/100)"
                f"; relationship with this character: {npc.get('relationship_label','stranger')}"
                f" ({npc.get('relationship_score',0):+d}/100)"
                f"{status_str}"
                f". Personality: {npc.get('personality','')}. Appearance: {npc.get('appearance','')}."
                f"{memory_str}"
            )
        npc_block = "\n".join(npc_lines) if npc_lines else "(none yet established)"

        event_lines = []
        for ev in events:
            event_lines.append(
                f"- EVENT_ID={ev.get('id')} | [{ev.get('event_type','incident').upper()}] "
                f"{ev.get('summary','')} (intensity: {ev.get('intensity','moderate')}). "
                f"Details: {ev.get('description','')}"
            )
        event_block = "\n".join(event_lines) if event_lines else "(none — the location is calm)"

        # Reputation block (HIDDEN from player; AI uses to colour NPC reactions)
        rep_score = reputation.get("score", 0)
        rep_label = reputation.get("label", "unknown")
        rep_nation = (reputation.get("nation") or "this region").title()
        rep_block = (
            f"This character's reputation in {rep_nation}: {rep_label} ({rep_score:+d}/100). "
            f"Do NOT state the score outright. Let NPCs of this nation react accordingly "
            f"(warm + helpful if positive, cold/suspicious/hostile if negative)."
        )

        # Diplomacy block: nations at war/tension affect NPC tone
        diplomacy_lines = []
        for rel in diplomacy:
            stance = rel.get("stance", "neutral")
            if stance in ("neutral",):
                continue
            diplomacy_lines.append(
                f"- {rel.get('nation_a','?').title()} and {rel.get('nation_b','?').title()}: {stance.upper()}"
            )
        diplomacy_block = "\n".join(diplomacy_lines) if diplomacy_lines else "(all major powers currently neutral toward one another)"

        # Hostility hint
        hostility_block = ""
        if hostility.get("triggered"):
            hostility_block = (
                "\n\nHOSTILITY HINT: This character has poor standing in this nation "
                f"({hostility.get('reputation_label','disliked')}, "
                f"{hostility.get('reputation_score',0):+d}/100). "
                "An NPC who recognises them or hears their name MAY attempt a hostile action "
                "(challenge, draw a weapon, call for guards, attack). This MUST be written as a "
                "T1 ATTEMPT — never assume the strike lands, never control the player. Leave "
                "the outcome to the player's next action."
            )

        # LAW SYSTEM: known criminal record in this nation. Bounded ≤ 5 entries.
        criminal_block = ""
        criminal_record_text = scene_state.get("criminal_record_text") or ""
        if criminal_record_text and "None" not in criminal_record_text.split("\n", 1)[0]:
            criminal_block = "\n\n" + criminal_record_text

        # WORLD CLOCK: in-world date + time-of-day. The AI should weave the
        # current atmosphere into descriptions naturally — without stating
        # the hour numerically.
        world_clock_block = ""
        world_time = scene_state.get("world_time") or {}
        delarom_date = scene_state.get("delarom_date") or ""
        world_date = scene_state.get("world_date") or ""
        world_year_label = scene_state.get("world_year_label") or ""
        if world_time:
            world_clock_block = (
                f"\n\nWORLD CLOCK: It is currently {world_time.get('phase','day')} "
                f"on the {delarom_date} of the Delarom calendar. "
                f"Atmospheric cue: {world_time.get('vibe','')}. "
                "Weave this naturally into your description (lighting, ambient sounds, "
                "who is awake at this hour) — do NOT state the literal clock time."
            )
        if world_date:
            world_clock_block += (
                f"\nIN-WORLD DATE: The date is the {world_date}. "
                "Reference the year and season only if it fits — a passing "
                "line ('deep into the {season} of {year}'), a headline on a "
                "broadsheet, a scrap of dialogue. Never a dry timestamp."
            ).format(
                season=(world_time.get("phase") if isinstance(world_time, dict) else "season"),
                year=world_year_label or "215 A.E.",
            )

        # FESTIVALS: any holy day or celebration currently active in this nation.
        festival_block = ""
        active_festivals = scene_state.get("active_festivals") or []
        if active_festivals:
            lines = ["\n\nACTIVE FESTIVALS IN THIS NATION:"]
            for f in active_festivals[:3]:
                lines.append(
                    f"  - {f.get('name','Festival')}: {f.get('description','')}"
                )
            lines.append(
                "Reflect the festival's mood in the scene — decorations, NPC behaviour, "
                "atmosphere. NPCs may reference the celebration unprompted."
            )
            festival_block = "\n".join(lines)

        # FAMILY & BLOODLINE: the acting character's declared relatives.
        # NPCs may occasionally reference these naturally if they fit the scene.
        family_block = ""
        relatives = scene_state.get("character_relatives") or []
        if relatives:
            lines = ["\n\nTHE ACTING CHARACTER'S DECLARED RELATIVES (use sparingly, only if a moment fits):"]
            for r in relatives[:6]:
                line = f"  - {r.get('name','?')} ({r.get('relationship','?')}, {r.get('status','?')})"
                if r.get('story'):
                    line += f": {r['story'][:160]}"
                lines.append(line)
            family_block = "\n".join(lines)

        # PROPHECY — a private oracle. The AI may subtly foreshadow without
        # ever quoting it directly to the player.
        prophecy_block = ""
        prophecy = scene_state.get("prophecy") or None
        if prophecy and prophecy.get("text"):
            prophecy_block = (
                "\n\nA PROPHECY HANGS OVER THIS CHARACTER (you, the narrator, know "
                "this — the character may NOT have it recited; instead, weave subtle "
                "foreshadowing of its imagery into the scene if a natural moment "
                "arises). The oracle's words were:\n  "
                + prophecy["text"].replace("\n", "\n  ")
            )

        # PERSONA / DISGUISE — when active, the world should see the persona.
        persona_block = ""
        if scene_state.get("persona_active"):
            risk = scene_state.get("disguise_recognition_risk", "none")
            persona_block = (
                f"\n\n*** DISGUISE IN PLAY ***\n"
                f"The acting character is presenting themselves as '{scene_state.get('persona_name','a stranger')}'"
                f"{', a ' + scene_state['persona_race'] if scene_state.get('persona_race') else ''}. "
                f"NPCs do not see the character's true name, true race, or any record of "
                f"prior crimes/reputation. Refer to the player by their persona name. "
                f"Risk of an observant NPC piercing the veil this scene: {risk}. "
                f"If you decide a single watchful NPC sees through the disguise, "
                f"describe it as their private suspicion — DO NOT shatter the disguise "
                f"unprompted unless the player gives them ample cause."
            )
            if scene_state.get("persona_background"):
                persona_block += f"\nThe persona's pretended background: {scene_state['persona_background']}"

        # FACTION ALLEGIANCE & ACTIVE RIVALRIES — Round 3 of Faction Membership.
        # CRITICAL realism rule: NPCs do NOT magically know what banner the player
        # rides under. They must PROBE — like gangs in real life weeding out
        # strangers. Hostility only follows confirmed (or strongly suspected)
        # affiliation. Whole block is suppressed when a persona is active.
        faction_block = ""
        pf = scene_state.get("player_faction") or None
        rivalries = scene_state.get("faction_rivalries") or []
        if pf:
            lines = [
                "\n\nPLAYER FACTION ALLEGIANCE (HIDDEN from NPCs unless the player gives signs):",
                f"  - The acting character belongs to {pf['name']} "
                f"(rank: {pf['rank']}{', home: ' + pf['nation_home'].replace('-', ' ').title() if pf.get('nation_home') else ''}).",
            ]
            if pf.get("motto"):
                lines.append(f"  - Their faction's motto, which a sworn member might let slip: \"{pf['motto']}\"")
            faction_block = "\n".join(lines)

            # Only surface rivalries with declared+ status (intensity >= 25)
            hot_rivalries = [r for r in rivalries if r.get("intensity", 0) >= 25]
            in_rival_turf = [r for r in hot_rivalries if r.get("in_their_territory")]
            sworn = [r for r in hot_rivalries if r.get("status") == "sworn-enemies"]

            if hot_rivalries:
                lines = ["\nACTIVE FACTION RIVALRIES:"]
                for r in hot_rivalries[:4]:
                    territory_tag = " [SCENE IS IN THEIR HOME TERRITORY]" if r.get("in_their_territory") else ""
                    lines.append(
                        f"  - {pf['name']} vs {r['name']} — status: {r.get('status','tense')} "
                        f"(intensity {r.get('intensity',0)}/100){territory_tag}"
                    )
                faction_block += "\n" + "\n".join(lines)

            # The realism rules. These are the heart of the feature.
            faction_block += (
                "\n\nRULES OF PROBING FOR FACTION AFFILIATION (READ CAREFULLY):"
                "\n  • NPCs DO NOT magically know the player's faction. Affiliation is invisible"
                "\n    until the player reveals it (badges, mottos, names of officers, knowledge"
                "\n    of secret signs, accent of a known stronghold, etc.) or until an NPC has"
                "\n    deliberately probed."
                "\n  • An NPC who is themselves sympathetic to a RIVAL faction MAY probe a"
                "\n    stranger with subtle, in-character questions — like real-world gang"
                "\n    'where you from?' tests. Examples (do NOT use these verbatim — vary them):"
                "\n      - \"Long road behind you? What part of the realm did it start in?\""
                "\n      - \"That brooch — I've seen its like before. Whose work?\""
                "\n      - \"You drink like a [rival home nation] hand. Spent time there?\""
                "\n      - \"Mind a question? What banner do you keep?\""
                "\n      - Quoting half a rival's motto to see if the player completes it."
                "\n  • Until the player confirms or betrays affiliation, NPCs treat them as a"
                "\n    stranger — wary, perhaps cold, but NOT openly hostile."
                "\n  • Once the player REVEALS membership in a rival faction (by word, badge,"
                "\n    boast, or unmistakable tell), NPCs of the rival faction MAY escalate —"
                "\n    veiled threats, calling for friends, drawing steel — scaled by rivalry"
                "\n    status (tense → muttered insults; declared → cold shoulder, refusal of"
                "\n    service; escalated → veiled threats, blocked exits; sworn-enemies →"
                "\n    open challenge or violence). All violence remains T1 ATTEMPTS — never"
                "\n    a guaranteed strike, never controlling the player."
                "\n  • A loyal member who answers honestly to their OWN faction's NPCs gets"
                "\n    warmth, secret signs, discounted goods, inside information."
            )
            if in_rival_turf:
                names = ", ".join(r["name"] for r in in_rival_turf)
                faction_block += (
                    f"\n  • SETTING: this scene is in the HOME NATION of {names}. "
                    "Locals here are likelier to be sympathetic to that faction and to probe "
                    "strangers. A NPC clearly aligned with the rival faction MAY be present."
                )
            if sworn:
                faction_block += (
                    "\n  • A SWORN-ENEMY rivalry is in play. NPCs aligned with the sworn enemy "
                    "scrutinise strangers HARDER (sharper probing questions, less patience for "
                    "evasive answers) — but they still must PROBE first. They do not auto-know."
                )

        # WHISPERED RUMORS — current talk-of-the-town in this nation. NPCs may
        # reference them. The truth-label is for YOUR guidance — never quote it.
        rumors_block = ""
        active_rumors = scene_state.get("active_rumors") or []
        if active_rumors:
            lines = ["\n\nRUMORS WHISPERED IN THIS NATION (NPCs may bring these up unprompted):"]
            for r in active_rumors[:4]:
                truth_hint = r.get("judgement", "false")
                lines.append(
                    f"  - About {r.get('subject_name','?')} ({r.get('subject_kind','?')}): "
                    f"\"{r.get('text','')[:200]}\"  [truth: {truth_hint}]"
                )
            lines.append(
                "Treat the truth-labels privately. An NPC's BELIEF in a rumor reflects what they "
                "HAVE HEARD, not what is true — so even false rumors can sway opinions."
            )
            rumors_block = "\n".join(lines)

        # LAW SYSTEM: imprisonment context. If the character is locked up, the
        # AI MUST treat the scene as taking place inside the jail.
        imprisonment_block = ""
        imp = scene_state.get("imprisonment")
        if imp:
            # Determine if the executioner is on the way — capital+ crimes after
            # ~half the sentence served may trigger an execution attempt.
            served = imp.get("turns_served", 0)
            sentence = max(1, imp.get("sentence_turns", 1))
            served_ratio = served / sentence
            crime_block = scene_state.get("criminal_record_text") or ""
            facing_execution = (
                ("[CAPITAL" in crime_block.upper() or "[REGICIDE" in crime_block.upper())
                and served_ratio >= 0.5
            )
            execution_clause = ""
            if facing_execution:
                execution_clause = (
                    " The prisoner has now served enough of their sentence that the EXECUTIONER "
                    "MAY arrive this turn. If so, write the scene as a lethal threat — the prisoner "
                    "MUST choose to fight, beg, or accept death. T1 rules apply: every strike "
                    "(prisoner's OR executioner's) is an ATTEMPT, never a guaranteed kill."
                )
            imprisonment_block = (
                "\n\nIMPRISONMENT STATUS: This character is currently INCARCERATED in "
                f"{imp.get('jail_location','this jail')} ({imp.get('nation','')}). "
                f"They have served {served} of {sentence} turns. "
                "The scene MUST take place from inside the cell or jail courtyard. Guards are "
                "present and watchful. The character cannot freely leave; any escape must be "
                "explicitly attempted via the escape action and is not granted by mere narration."
                + execution_clause
            )

        # ───────── TIER 2 — DEEP IMMERSION LAYER ─────────

        # ELDER-GODS FESTIVAL — if today is a canonical festival day, the
        # atmosphere colours EVERY scene realm-wide. Streamers, processions,
        # temple activity, or subdued civic quiet (Ehena's Long Hour).
        elder_festival_block = ""
        fest = scene_state.get("active_elder_festival")
        if fest:
            elder_festival_block = (
                f"\n\nELDER-GODS FESTIVAL ACTIVE — {fest['festival_name'].upper()}:\n"
                f"  - Level: {fest['level']} (a {'major realm-wide' if fest['level']=='major' else 'weekly'} observance).\n"
                f"  - Atmosphere to weave (NOT list — bake it into the scene): {fest['atmosphere']}\n"
                f"  - NPCs may reference the festival naturally. Prayers to "
                f"{fest['god'].capitalize()} today carry the god's favour more readily."
            )

        # 2a. ACTIVE BLESSINGS — Four Elder Gods prayer system.
        blessing_block = ""
        active_blessings = scene_state.get("active_blessings") or []
        if active_blessings:
            lines = [
                "\n\nACTIVE DIVINE BLESSINGS UPON THIS CHARACTER (weave subtly into the "
                "scene — DO NOT announce them outright unless the character invokes the god):",
            ]
            for b in active_blessings[:4]:
                vname = "Blessing" if b.get("verdict") == "blessing" else "Flicker"
                lines.append(
                    f"  - [{vname} of {b.get('god_name','?')}] {b.get('boon_text','')}"
                )
            lines.append(
                "Blessings are favour, not power. They colour outcomes — a Yros-blessed "
                "dwarf's hammer rings truer; a Seren-blessed elf's wounds knit faster; "
                "a Uesis-touched mind catches glimpses. NEVER write the favour as a "
                "guaranteed effect. It is a thread of grace, not a victory."
            )
            blessing_block = "\n".join(lines)

        # 2b. ACT MAGIC — surface the character's magic stat + freeform powers.
        act_magic_block = ""
        magic_stat = scene_state.get("character_magic_stat", 0) or 0
        powers_text = (scene_state.get("character_powers") or "").strip()
        if magic_stat or powers_text:
            ess_hints = scene_state.get("character_essence_hints") or []
            essence_line = (
                f"  - Apparent essence affinities (inferred from background/powers): "
                f"{', '.join(ess_hints)}.\n"
                if ess_hints else ""
            )
            mana_label = "negligible"
            if magic_stat >= 80:   mana_label = "vast — a true archmage's reserve"
            elif magic_stat >= 60: mana_label = "deep — a trained mage"
            elif magic_stat >= 40: mana_label = "moderate — a practiced caster"
            elif magic_stat >= 20: mana_label = "modest — a dabbler"
            elif magic_stat > 0:   mana_label = "thin — sparks only"
            act_magic_block = (
                "\n\nACT MAGIC PROFILE (Astral Conversion Theory):\n"
                f"  - Magic stat: {magic_stat}/100 ({mana_label}).\n"
                f"{essence_line}"
                f"  - Declared powers/abilities: {powers_text[:300]}\n"
                "When the player attempts magic, judge by ACT principles: mana is "
                "REDIRECTED, not summoned from nothing — they must channel mana "
                "already present (in the air, the ley lines, the stones, themselves). "
                "Big spells on a thin reserve should strain or backfire. A caster "
                "working in their own essence affinity casts with grace; one fighting "
                "against their affinity sweats, stutters, or fails outright. NEVER "
                "auto-resolve spells as successes — every cast is an ATTEMPT, judged "
                "by reserve × affinity × focus."
            )

        # 2c. RACE-SPECIFIC ELVEN MAGIC SCHOOLS — Selindori + Veiled Realms.
        elven_school_block = ""
        race_lc = (scene_state.get("character_race") or "").strip().lower()
        nation_lc = (scene_state.get("nation") or "").strip().lower()
        ELVEN_SCHOOLS = {
            "sun elf":     ("Selindori (Aurelion Spires)", "Solar Channelling", "light/fire"),
            "wood elf":    ("Selindori (Thalenroot)",       "Verdant Weaving",  "earth/life"),
            "tide elf":    ("Selindori (Nal'theris)",       "Tidal Reflection", "water"),
            "mountain elf":("Selindori (Isenfell)",         "Stone-Singing",    "earth"),
            "moon elf":    ("Rakesh (Veiled Realms)",       "Lunomancy",        "shadow/light"),
            "shadow elf":  ("Yaksha-Shi (Veiled Realms)",   "Umbral Arts",      "shadow"),
            "crystal elf": ("Serant-Kresh (Veiled Realms)", "Memory-Binding",   "crystal/astral"),
            "high elf":    ("Selindori",                    "Sun Synod Liturgy","light"),
        }
        for sub_race, (realm, school, essence) in ELVEN_SCHOOLS.items():
            if sub_race in race_lc:
                home_token = realm.split(" ")[0].lower().replace("(", "").rstrip(",")
                if home_token in nation_lc or nation_lc in realm.lower():
                    elven_school_block = (
                        f"\n\nELVEN MAGIC SCHOOL — HOME REALM ATMOSPHERE:\n"
                        f"  - This {sub_race} character is in their home realm ({realm}).\n"
                        f"  - The realm's signature magic school is **{school}**, "
                        f"resonating with {essence} essence.\n"
                        f"  - Local mages, ambient enchantments, and NPC observations should "
                        f"reference this school naturally. The character carries an inborn "
                        f"familiarity with its forms even if untrained — a half-remembered "
                        f"cradle-song of mana — and may attempt minor effects of this school "
                        f"with notably less strain than other schools."
                    )
                break

        # 2d. TITAN SACRED SITES — themed essence atmosphere + amplified magic.
        titan_block = ""
        titan = scene_state.get("titan_sacred_site")
        TITAN_THEMES = {
            "flame":  ("Titan of Flame",  "molten heat, distant rumble, fire essence",       "fire"),
            "stone":  ("Titan of Stone",  "vast silence, deep mineral cold, earth essence",   "earth"),
            "wind":   ("Titan of Wind",   "ceaseless gusts, vertigo, air/lightning essence",  "air"),
            "tide":   ("Titan of Tide",   "salt-wet air, low rhythmic surge, water essence",  "water"),
            "shadow": ("Titan of Shadow", "muted light, pressing dread, shadow essence",      "shadow"),
            "frost":  ("Titan of Frost",  "biting cold, brittle air, ice essence",            "frost/water"),
            "decay":  ("Titan of Decay",  "stillness like a held breath, withered echoes, decay essence", "decay/shadow"),
        }
        if titan and titan in TITAN_THEMES:
            tname, atmosphere, essence = TITAN_THEMES[titan]
            titan_block = (
                f"\n\nTITAN SACRED SITE — {tname.upper()}:\n"
                f"  - This location is consecrated to the {tname}, one of the Seven slain "
                f"by Ausar at the dawn of the Astral Era. Even in defeat, the Titan's "
                f"essence still seeps from the ground here.\n"
                f"  - Ambient atmosphere to weave (not list): {atmosphere}.\n"
                f"  - Magic worked here in the {essence} essence is amplified — casters "
                f"with that affinity may attempt feats above their normal reserve, but "
                f"workings against the essence sputter and fail more readily.\n"
                f"  - NPCs treat the site with reverence, dread, or both. A profane act "
                f"here is remembered for a long time."
            )

        # Bearer of the Tongue of Y'ros — surface if this character carries it.
        tongue_block = ""
        if scene_state.get("has_tongue_of_yros"):
            tongue_block = (
                "\n\nBEARER OF THE TONGUE OF Y'ROS:\n"
                "  - This character carries the legendary stone blade drawn from "
                "Thal'Karrak. Every dwarf who sees it recognises it instantly; "
                "reactions range from awe to jealousy to challenge. The blade is "
                "consecrated to Yros — cannot be stolen, only surrendered. Its weight "
                "and the hum of stone it emits give the bearer real presence in a "
                "scene without a word being spoken."
            )

        # ───────── END TIER 2 ─────────

        return (
            "PERSISTENT NPCs IN SCENE (use these by name; honour their mood + history + importance tier):\n"
            f"{npc_block}\n\n"
            "ACTIVE SCENE EVENTS (these are HAPPENING NOW — continue them, do not reset):\n"
            f"{event_block}\n\n"
            "CHARACTER REPUTATION (HIDDEN — never quote the score):\n"
            f"{rep_block}\n\n"
            "INTER-NATION DIPLOMATIC STATE:\n"
            f"{diplomacy_block}"
            f"{hostility_block}"
            f"{criminal_block}"
            f"{imprisonment_block}"
            f"{world_clock_block}"
            f"{festival_block}"
            f"{family_block}"
            f"{prophecy_block}"
            f"{persona_block}"
            f"{faction_block}"
            f"{rumors_block}"
            f"{blessing_block}"
            f"{act_magic_block}"
            f"{elven_school_block}"
            f"{titan_block}"
            f"{tongue_block}"
            f"{elder_festival_block}"
        )

    async def generate_companion_banter(
        self,
        *,
        companions: List[Dict],
        nation: str,
        location: str,
        player_action: str,
        active_events: Optional[List[Dict]] = None,
    ) -> str:
        """Produce 1-2 short, italicised banter beats from companions reacting
        to the current scene. Returns a plain string ready to prepend to the
        main AI response, or an empty string if nothing was generated.

        Designed to be cheap (gpt-4o-mini) and resilient — any error returns "".
        """
        if not companions:
            return ""

        comp_lines = "\n".join(
            f"- {c.get('name','Unknown')} ({c.get('race','?')}, {c.get('role','companion')}). "
            f"Mood: {c.get('overall_mood','neutral')}. "
            f"Personality: {c.get('personality','') or 'unknown'}. "
            f"Motivation: {c.get('motivation','') or 'unknown'}."
            for c in companions[:4]
        )
        events_summary = "; ".join(
            f"{e.get('event_type','incident')}: {e.get('summary','')}"
            for e in (active_events or [])[:3]
        ) or "(none)"

        system_message = (
            self.DELAROM_LORE
            + "\n\nYou are a silent companion-banter author. Produce ONLY 1-2 short italicised beats "
            + "of in-character reaction/observation from the listed companions about this scene. "
            + "Each beat: one sentence, third-person, present tense, surrounded by *asterisks*. "
            + "NEVER speak for the player character. NEVER resolve combat or alter the scene. "
            + "If nothing memorable is happening, return one tiny ambient beat (a glance, a sigh). "
            + "Output ONLY the beats separated by newlines. No headings. No prose outside the asterisks."
        )

        prompt = f"""
LOCATION: {location} in {nation}
PLAYER ACTION: "{player_action[:300]}"
ACTIVE SCENE EVENTS: {events_summary}

COMPANIONS TRAVELING WITH THE PLAYER:
{comp_lines}

TASK: Write 1-2 short italicised banter beats. Pick the companion(s) whose
personality / motivation makes the most sense to react. Stay strictly in
their voice; do NOT narrate the player's actions or resolve dice rolls.
"""

        try:
            chat = LlmChat(
                api_key=self.api_key,
                session_id=f"banter_{location}_{_rng.randint(0, 99999)}",
                system_message=system_message,
            ).with_model("openai", "gpt-4o-mini")
            response = await chat.send_message(UserMessage(text=prompt))
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Companion banter failed: {e}")
            return ""

        text = (response or "").strip()
        # Defensive: cap length so a runaway prompt can't dominate the main response
        if len(text) > 600:
            text = text[:600].rstrip() + " *"
        return text

    async def analyze_interaction(
        self,
        *,
        nation: str,
        location: str,
        character_name: str,
        player_action: str,
        ai_response: str,
        present_npcs: List[Dict] = None,
        active_events: List[Dict] = None,
    ) -> Dict:
        """Extract sentiment shifts, new NPCs, new events, and event resolutions
        from the just-completed exchange. Returns a strict JSON-shaped dict.
        """
        full_system_message = (
            self.DELAROM_LORE
            + "\n\nYou are a silent narrative-state analyser. You read a player's roleplay action and the Quest Master's response, then output STRUCTURED JSON describing how the persistent world should be updated. Output JSON ONLY. No prose. No code fences."
        )

        chat = LlmChat(
            api_key=self.api_key,
            session_id=f"analyse_{location}_{_rng.randint(0, 99999)}",
            system_message=full_system_message,
        ).with_model("openai", "gpt-4o-mini")

        present_npcs = present_npcs or []
        active_events = active_events or []

        npc_summary = "\n".join([
            f"- id={n.get('id')} name={n.get('name')} mood={n.get('overall_mood','neutral')}"
            f" relationship_score={n.get('relationship_score',0)} status={n.get('status','alive')}"
            f" companion={'yes' if n.get('is_companion') else 'no'}"
            for n in present_npcs
        ]) or "(none)"
        events_summary = "\n".join([
            f"- event_id={e.get('id')} type={e.get('event_type')} status=active summary={e.get('summary','')}"
            for e in active_events
        ]) or "(none)"

        prompt = f"""
LOCATION: {location} in {nation}
PLAYER CHARACTER: {character_name}

PRE-EXISTING NPCs (use these IDs when referring to them):
{npc_summary}

ACTIVE EVENTS IN LOCATION (use these IDs when referring to them):
{events_summary}

PLAYER ACTION:
"{player_action}"

QUEST MASTER RESPONSE:
"{ai_response}"

TASK: Analyse the exchange and update the world state. Return JSON with EXACTLY this shape:
{{
  "npc_updates": [
    {{
      "npc_id": "<id from pre-existing list>",
      "sentiment_delta": <integer -10..+10, how this character's standing with the NPC changed>,
      "memory": "<short 1-sentence memorable fact, or empty string if not memorable>",
      "status": "<alive|wounded|dead|fled|missing — only include if status CHANGED>",
      "status_note": "<short reason if status changed>",
      "companion_action": "<bond|dismiss — ONLY include if the NPC clearly and willingly agreed to travel with the character, OR clearly and willingly parted ways. Omit otherwise.>"
    }}
  ],
  "new_npcs": [
    {{
      "name": "<culturally appropriate name>",
      "race": "<race>",
      "role": "<e.g. barkeep, guard, merchant, prince, captain>",
      "importance": "<commoner|notable|noble|ruler|monarch — DEFAULT to commoner unless the role clearly indicates higher rank (e.g., a named lord = noble, a king = monarch)>",
      "appearance": "<physical description>",
      "personality": "<traits>",
      "motivation": "<what drives them>",
      "background": "<short background>",
      "quirks": "<unique trait>",
      "sentiment_delta": <integer -10..+10 reflecting first impression with this character>,
      "memory": "<short memorable detail from this first meeting>",
      "companion_action": "<bond — ONLY include if this brand-new NPC explicitly agreed on the spot to accompany the character (e.g., the player hired a guide who said yes). Omit otherwise.>"
    }}
  ],
  "new_events": [
    {{
      "event_type": "<brawl|fight|festival|accident|disturbance|mystery|weather|incident>",
      "summary": "<short single-line summary visible to all members entering this location>",
      "description": "<2-3 sentence vivid description for AI context>",
      "intensity": "<mild|moderate|severe|epic>"
    }}
  ],
  "event_updates": [
    {{
      "event_id": "<id from active list>",
      "status": "<resolved|decayed>",
      "resolution_note": "<short 1-sentence note on how it ended>"
    }}
  ],
  "criminal_acts": [
    {{
      "perpetrator": "<player | <npc_id from the present-NPC list>>",
      "crime_type": "<theft|assault|murder|arson|kidnapping|treason|fraud|public_disorder|other>",
      "severity": "<petty|minor|major|capital|regicide>",
      "victim_name": "<name of victim if any, empty string if property/state crime>",
      "victim_importance": "<commoner|notable|noble|ruler|monarch>",
      "description": "<short 1-sentence factual summary>"
    }}
  ],
  "hunted_targets": [
    {{
      "npc_id": "<id from the present-NPC list of an NPC with a known open bounty>",
      "method": "<captured|killed>",
      "description": "<short 1-sentence factual summary of how the player took them down>"
    }}
  ],
  "arrest_executed": <true if the Quest Master's narration this turn clearly shows the PLAYER CHARACTER being subdued / manacled / dragged to jail by guards or lawful authorities; false otherwise. Must be a clear, completed arrest in this exchange, not a mere announcement or attempt>,
  "arrest_reason": "<short 1-sentence summary of what the player did to earn the arrest (touched a guard, resisted, fled an active warrant, etc.). Empty string if no arrest.>"
}}

RULES:
- Only include NPCs in "new_npcs" if a clearly-named or clearly-identifiable NEW NPC was introduced by the Quest Master in this exchange. Do NOT duplicate pre-existing NPCs.
- Only include events in "new_events" if a notable, shared, location-altering situation began (brawl, fire, festival, riot, mass arrival, etc.). Do NOT create events for ordinary conversation.
- Sentiment delta should reflect how rude/cruel/violent OR kind/polite/helpful the player's action was toward each NPC. Neutral = 0. Mild rudeness = -2. Cruel mockery = -6. Threatening = -8. Violence = -10. Friendly chat = +2. Generous = +5. Heroic = +8.
- Memory text: write in third person, factual, 1 sentence max. Empty string if nothing memorable.
- COMPANION RULES:
  * Only emit `companion_action: "bond"` when an NPC EXPLICITLY and WILLINGLY agrees in the Quest Master's response to travel with the character (e.g. they say "I'll come with you", "lead the way", "I shall follow you", or accept an offer of employment as a guide/bodyguard). NEVER bond NPCs against their will or based solely on the player saying "you're coming with me".
  * Only emit `companion_action: "dismiss"` when an NPC clearly chooses to leave, the player explicitly dismisses them, or the NPC dies/flees.
  * Hostile NPCs (relationship < -10) MUST NOT bond. Wounded or fleeing NPCs MUST NOT bond.
  * Omit `companion_action` entirely for ordinary interactions.
- CRIMINAL ACTS RULES:
  * Watch BOTH the player AND the named NPCs in the scene. Either can commit a crime.
  * Default `perpetrator` is "player". If a named NPC clearly committed the crime instead,
    set `perpetrator` to that NPC's exact id from the present-NPC list.
  * Self-defense against an aggressor is NOT a crime.
  * SANCTIONED BOUNTY HUNTING IS NOT A CRIME. If the player CAPTURES or KILLS an
    NPC who was clearly flagged "WANTED" in the present-NPC list, that act is
    lawful bounty enforcement — list it in `hunted_targets` instead and DO NOT
    add it to `criminal_acts`. (Killing an unrelated bystander during the hunt
    IS still a crime against that bystander.)
  * Severity guide:
    - petty: pickpocketing a coin, brawling without injury, minor vandalism, public drunkenness
    - minor: theft of valuables, simple assault causing injury, fraud, breaking and entering
    - major: grand theft, aggravated assault, arson of a building, assault of a noble
    - capital: murder, treason, mass arson, slavery, kidnapping a noble
    - regicide: assassination or grievous wounding of a ruler/monarch, mass-casualty atrocities
  * `victim_importance` MUST match the NPC's tier when known. Unknown commoners default to "commoner".
  * Crimes must be SCOPED to this location/nation only. Do not retroactively record past crimes.
  * If nothing illegal happened, return an EMPTY ARRAY.
- HUNTED TARGETS RULES:
  * If the player CAPTURES (subdues + binds) or KILLS an NPC who was flagged as
    "WANTED" in the scene prompt, list them in `hunted_targets`.
  * Only include NPCs from the present-NPC list whose flag explicitly said WANTED.
  * Default to "captured" unless the player clearly killed them.
  * If no wanted NPC was taken down, return an EMPTY ARRAY.
- ARREST DETECTION RULES (read carefully — this triggers an automatic trial):
  * Set `arrest_executed: true` ONLY if the Quest Master's narration this turn
    clearly shows the PLAYER CHARACTER subdued by lawful authority — manacled,
    bound, knocked out, restrained on the floor, or otherwise visibly taken
    into custody. Examples that QUALIFY:
      - "The guards wrestle [PLAYER] to the cobblestones and clamp manacles on their wrists."
      - "A baton crack against the temple, and [PLAYER] crumples; the watch hauls them up by the arms."
      - "Three blades level at [PLAYER]'s throat; with no opening left, they are bound and led away."
    Examples that DO NOT qualify (do NOT set true):
      - "The guard reaches for [PLAYER]'s wrist." (mere attempt)
      - "'You're under arrest!' the captain barks." (announcement only)
      - "Reinforcements close in." (threat, not completion)
  * If the player FOUGHT BACK, FLED, or evaded the takedown in the narration,
    arrest_executed MUST be false even if guards announced an arrest.
  * Default to false. Only flip to true on a clear, completed in-custody
    moment in this exact exchange.
- If nothing happened in a category, return an EMPTY ARRAY for it.
- Output JSON ONLY.
"""

        try:
            response = await chat.send_message(UserMessage(text=prompt))
        except Exception as e:  # noqa: BLE001
            return {"npc_updates": [], "new_npcs": [], "new_events": [], "event_updates": [], "criminal_acts": [], "hunted_targets": [], "arrest_executed": False, "arrest_reason": "", "_error": str(e)}

        # Try to parse JSON, with fallback to fenced extraction
        try:
            return json.loads(response)
        except (json.JSONDecodeError, TypeError, ValueError):
            try:
                import re
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group(0))
            except (json.JSONDecodeError, TypeError, ValueError, AttributeError):
                pass
            return {"npc_updates": [], "new_npcs": [], "new_events": [], "event_updates": [], "criminal_acts": [], "hunted_targets": [], "arrest_executed": False, "arrest_reason": ""}

    # ============================================================
    # LAW SYSTEM — trial narration and escape adjudication
    # ============================================================

    async def narrate_trial(
        self,
        *,
        character_name: str,
        nation: str,
        location: str,
        open_crimes: List[Dict],
        total_bounty: int,
    ) -> Dict:
        """Ask the AI to narrate a brief trial scene for a surrendering character
        and return both the prose and a structured sentence.

        Returns:
            {
              "narration": str,
              "sentence_type": "fine|imprison|exile|execute|dismissed",
              "fine_amount": int,
              "imprison_turns": int,
              "jail_location": str | "",
              "verdict_summary": str,
              "_raw": str (debug only)
            }
        """
        if not open_crimes:
            return {
                "narration": (
                    f"The magistrate of {location} reviews the charges, finds them "
                    "without substance, and dismisses {character_name} with a curt nod."
                ),
                "sentence_type": "dismissed",
                "fine_amount": 0,
                "imprison_turns": 0,
                "jail_location": "",
                "verdict_summary": "Dismissed — no actionable charges.",
            }

        charges_block = "\n".join(
            f"  - [{c.get('severity','minor').upper()}] {c.get('crime_type','crime')}"
            f" against {c.get('victim_name') or 'unknown'} ({c.get('victim_importance','commoner')})"
            f" — bounty {c.get('bounty',0)}g. {c.get('description','')}"
            for c in open_crimes[:8]
        )

        system_message = (
            self.DELAROM_LORE
            + "\n\nYou are presiding as the lawful magistrate of this scene. Narrate a brief, "
            + "vivid trial (3-6 sentences) appropriate to the nation's culture (Ammeonon = royal "
            + "tribunal, Dhor-Kuldor = clan elders, Selindori = elven council, Aigraels = priestly "
            + "synod, Veiled Realms = silent inquisition). Reach a verdict consistent with the "
            + "charges and severity, then return STRICT JSON with the schema specified."
        )

        prompt = f"""
NATION: {nation}
LOCATION: {location} (court/jail of this town)
DEFENDANT: {character_name}
TOTAL ACTIVE BOUNTY: {total_bounty}g

CHARGES:
{charges_block}

TASK: Narrate the trial (3-6 sentences) and decide the sentence. Return JSON with EXACTLY this shape, NO prose outside the JSON object:

{{
  "narration": "<3-6 sentence trial scene>",
  "sentence_type": "<fine|imprison|exile|execute|dismissed>",
  "fine_amount": <integer gold, 0 if not a fine>,
  "imprison_turns": <integer turns to serve in jail, 0 if not imprisoned>,
  "jail_location": "<the location slug of the jail, usually the same as the location above>",
  "verdict_summary": "<one-sentence summary of the verdict>"
}}

SENTENCING GUIDE:
- petty crimes only → fine (10-100g) OR 1 turn jail
- minor crimes → fine (100-500g) and/or 1-3 turns jail
- major crimes → 5-15 turns jail and/or 1000-5000g fine
- capital crimes → DEFAULT to imprison (15-30 turns). Only reach for execution if
  the player explicitly resisted arrest, was a repeat capital offender (≥2 prior
  served capital sentences), OR the victim was a noble/ruler/monarch AND no
  mitigating circumstances exist. Mercy and rehabilitation are valid choices.
- regicide → execution OR life imprisonment (50+ turns). Both are valid.
- Multiple charges stack toward the higher tier.
- Always pick ONE primary sentence_type. If imprison_turns > 0, sentence_type MUST be "imprison".
- jail_location should be the same as the LOCATION above unless your narration explicitly transports the prisoner elsewhere.

Output JSON ONLY.
"""
        try:
            chat = LlmChat(
                api_key=self.api_key,
                session_id=f"trial_{nation}_{_rng.randint(0,99999)}",
                system_message=system_message,
            ).with_model("openai", "gpt-4o-mini")
            response = await chat.send_message(UserMessage(text=prompt))
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Trial narration failed: {e}")
            return {
                "narration": f"The magistrate of {location} weighs the charges in silence, then sentences {character_name} according to the law of {nation}.",
                "sentence_type": "imprison",
                "fine_amount": 0,
                "imprison_turns": 5,
                "jail_location": location,
                "verdict_summary": "Imprisoned by default sentence (AI unavailable).",
            }

        result = _safe_parse_json(response) or {}
        # Defensive defaults
        sentence_type = result.get("sentence_type") or "imprison"
        if sentence_type not in ("fine", "imprison", "exile", "execute", "dismissed"):
            sentence_type = "imprison"
        result["sentence_type"] = sentence_type
        result.setdefault("narration", "")
        result.setdefault("verdict_summary", "")
        result["fine_amount"] = max(0, int(result.get("fine_amount", 0) or 0))
        result["imprison_turns"] = max(0, int(result.get("imprison_turns", 0) or 0))
        result.setdefault("jail_location", location)
        if sentence_type == "imprison" and result["imprison_turns"] == 0:
            result["imprison_turns"] = 5
        return result

    async def judge_escape_attempt(
        self,
        *,
        character_name: str,
        jail_location: str,
        turns_served: int,
        sentence_turns: int,
        description: str,
        companions_present: Optional[List[Dict]] = None,
    ) -> Dict:
        """Adjudicate a roleplay-driven escape attempt.

        Returns:
            {
              "success": bool,
              "narration": str,
              "consequence_summary": str
            }
        """
        comp_block = ""
        if companions_present:
            comp_block = "\nCOMPANIONS PRESENT:\n" + "\n".join(
                f"  - {c.get('name')} ({c.get('race','?')}, {c.get('role','companion')})"
                for c in companions_present[:4]
            )

        system_message = (
            self.DELAROM_LORE
            + "\n\nYou judge an escape attempt fairly. Reward creativity, specific use of "
            + "environment / companions / earned NPC favour. Punish vague, lazy, or absurd "
            + "attempts. Brief, vivid prose. Return STRICT JSON only."
        )

        prompt = f"""
PRISONER: {character_name}
JAIL: {jail_location}
TIME SERVED: {turns_served}/{sentence_turns} turns
{comp_block}

THE PRISONER'S ESCAPE ATTEMPT (player's own words):
"{(description or '').strip()[:500]}"

TASK: Judge fairly. Return JSON with EXACTLY this shape:

{{
  "success": <true if the attempt is creative AND mechanically plausible, else false>,
  "narration": "<2-5 sentences narrating the attempt>",
  "consequence_summary": "<one short sentence summarising what happens next>"
}}

JUDGING GUIDE:
- Success requires SPECIFIC, plausible tactics. Lazy attempts ("I escape", "I leave", "I run") MUST fail.
- Bonus to success odds for: using companions, exploiting a guard's known weakness/mood, taking advantage of an active scene event, paying a bribe with described currency.
- Penalty for: violence escalating without justification, magic the character cannot wield, contradicting known facts.
- Capital/regicide-tier sentences (long ones) require GREATER creativity to escape.

Output JSON ONLY.
"""
        try:
            chat = LlmChat(
                api_key=self.api_key,
                session_id=f"escape_{jail_location}_{_rng.randint(0,99999)}",
                system_message=system_message,
            ).with_model("openai", "gpt-4o-mini")
            response = await chat.send_message(UserMessage(text=prompt))
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Escape adjudication failed: {e}")
            return {
                "success": False,
                "narration": f"{character_name} attempts to flee, but stumbles in the gloom and is hauled back by the guards.",
                "consequence_summary": "Escape failed (judge unavailable).",
            }

        result = _safe_parse_json(response) or {}
        result["success"] = bool(result.get("success", False))
        result.setdefault("narration", "")
        result.setdefault("consequence_summary", "")
        return result


    # ============================================================
    # COURTROOM — multi-turn trial scene
    # ============================================================

    @staticmethod
    def _format_charges(open_crimes: List[Dict]) -> str:
        if not open_crimes:
            return "(no current charges — defendant brought in error)"
        lines = []
        for c in open_crimes[:8]:
            lines.append(
                f"  - [{c.get('severity','minor').upper()}] "
                f"{c.get('crime_type','crime')} against "
                f"{c.get('victim_name') or 'an unnamed victim'} "
                f"({c.get('victim_importance','commoner')}) — "
                f"recorded at {c.get('location','?')} on {c.get('created_at','?')[:10]}. "
                f"{c.get('description','')}"
            )
        return "\n".join(lines)

    @staticmethod
    def _format_witnesses(witnesses: List[Dict]) -> str:
        if not witnesses:
            return "  (no named victim witnesses are present today — only the state's record stands accuser)"
        lines = []
        for w in witnesses[:6]:
            lines.append(
                f"  - {w.get('name','?')} ({w.get('race','?')}, "
                f"{w.get('role','victim')}, tier={w.get('importance','commoner')}) — "
                f"summoned for: {w.get('crime_summary','?')}. "
                f"{('Personality: ' + w['personality']) if w.get('personality') else ''}"
            )
        return "\n".join(lines)

    async def narrate_courtroom_turn(
        self,
        *,
        character_name: str,
        nation: str,
        courthouse_location: str,
        judge_name: str,
        prosecutor_name: str,
        witnesses: List[Dict],
        open_crimes: List[Dict],
        total_bounty: int,
        defence_text: str,
        turn_no: int,
        max_turns: int,
        current_leniency: int,
        recent_history: List[Dict] = None,
    ) -> Dict:
        """One turn of the courtroom scene.

        Returns:
            {
              "narration": str,                 # 3-7 sentences of courtroom RP
              "judge_remark": str,              # one short line by the judge
              "leniency_delta": int,            # -25..+25, sign shows direction
              "leniency_reasoning": str,        # brief judge-side reasoning
              "judge_cut_off": bool,            # True if defence was absurd / repeated
              "_raw": str
            }
        """
        history_block = ""
        if recent_history:
            history_lines = []
            for h in recent_history[-3:]:
                history_lines.append(
                    f"  - Turn {h.get('turn','?')} defence: \"{(h.get('defence_text','') or '')[:200]}\""
                    f"  ⟶ leniency Δ {h.get('leniency_delta',0):+d}"
                    f"{' (judge cut short)' if h.get('judge_cut_off') else ''}"
                )
            history_block = "\nPRIOR DEFENCE TURNS:\n" + "\n".join(history_lines)

        system_message = (
            self.DELAROM_LORE
            + "\n\n" + self.T1_RULES
            + "\n\nYou are the QUEST MASTER NARRATING A COURTROOM SCENE. You play the "
            + "judge, the prosecutor, the assembled witness NPCs and the bailiffs. You do "
            + "NOT control the defendant — the player will speak for themselves. Every "
            + "sentence in your narration follows T1 rules: NPC reactions are real but "
            + "the defendant's words, body language and inner state belong to the player.\n"
            + "Output strict JSON. No prose outside the JSON object."
        )

        prompt = f"""
COURTROOM SCENE — {_pretty(courthouse_location)} of {_pretty(nation)}

DEFENDANT: {character_name}
TURN: {turn_no} of {max_turns}
CURRENT LENIENCY TALLY (HIDDEN from defendant): {current_leniency:+d} / range -100..+100
  (positive = leaning toward mercy / lighter sentence;
   negative = leaning toward harshness / heavier sentence)

PRESIDING JUDGE: {judge_name}
PROSECUTOR: {prosecutor_name}

OPEN CHARGES (total bounty {total_bounty}g):
{self._format_charges(open_crimes)}

WITNESSES PRESENT:
{self._format_witnesses(witnesses)}

{history_block}

DEFENDANT'S DEFENCE THIS TURN (their own words):
\"\"\"{(defence_text or '').strip()[:1500]}\"\"\"

TASK:
1. Write a vivid courtroom narration (3-7 sentences) where the JUDGE, PROSECUTOR,
   and any relevant WITNESSES react to the defence. Honor the personalities,
   moods and prior crime context. T1 rules apply — never voice the defendant.
2. Evaluate the QUALITY of the defence and decide a leniency delta from -25..+25:
     +20..+25 = exceptional defence (rock-solid alibi, clear evidence of innocence,
                noble rhetoric backed by witness sympathy)
     +10..+19 = strong defence (credible explanation, a witness softens, a successful
                appeal to mercy, a meaningful bribe in noble denomination)
     +1..+9   = competent defence (plausible argument, polite tone, partial mitigating
                circumstance)
      0       = flat / neutral defence (denial without substance)
     -1..-9   = weak defence (vague denial, refusal to engage, mild evasiveness)
     -10..-19 = poor defence (insulting the court, contradicting itself, contempt,
                threatening a witness, transparently false alibi)
     -20..-25 = catastrophic defence (assaulting court officers, confessing additional
                crimes, blasphemy, calling for violence in chambers — judge MUST
                also set judge_cut_off=true)
3. Decide if the judge CUTS OFF further defence early (judge_cut_off=true). Reasons:
     - The defendant repeated themselves verbatim from a prior turn.
     - The defence is utterly absurd (e.g., "I am a god, you cannot judge me").
     - The defendant assaulted court officers, escaped, or insulted the realm itself.
     - The defence transparently confesses additional capital crimes.
4. Write a short judge_remark — a one-sentence line the judge actually says out
   loud at the close of this turn (e.g. "The court will deliberate on that.",
   "A bold claim, defendant. Continue.", "Enough. I have heard enough.").

Return JSON with EXACTLY this shape:
{{
  "narration": "<3-7 sentences of T1-compliant courtroom RP>",
  "judge_remark": "<one short line the judge says aloud>",
  "leniency_delta": <integer -25..+25>,
  "leniency_reasoning": "<brief one-line private rationale (not read aloud)>",
  "judge_cut_off": <true|false>
}}

Output JSON ONLY.
"""
        try:
            chat = LlmChat(
                api_key=self.api_key,
                session_id=f"trial_{courthouse_location}_{turn_no}_{_rng.randint(0,99999)}",
                system_message=system_message,
            ).with_model("openai", "gpt-4o")
            response = await chat.send_message(UserMessage(text=prompt))
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Courtroom narration failed: {e}")
            return {
                "narration": (
                    f"The judge weighs {character_name}'s words in silence. "
                    "The court reserves its reaction for now."
                ),
                "judge_remark": "Continue.",
                "leniency_delta": 0,
                "leniency_reasoning": "AI judge unavailable; held at neutral.",
                "judge_cut_off": False,
            }

        result = _safe_parse_json(response) or {}
        try:
            delta = int(result.get("leniency_delta", 0) or 0)
        except (TypeError, ValueError):
            delta = 0
        delta = max(-25, min(25, delta))
        result["leniency_delta"] = delta
        result["judge_cut_off"] = bool(result.get("judge_cut_off", False))
        result.setdefault("narration", "")
        result.setdefault("judge_remark", "")
        result.setdefault("leniency_reasoning", "")
        return result

    async def narrate_verdict_with_defence(
        self,
        *,
        character_name: str,
        nation: str,
        courthouse_location: str,
        judge_name: str,
        open_crimes: List[Dict],
        total_bounty: int,
        defense_history: List[Dict],
        final_leniency: int,
        baseline_sentence: Dict,
    ) -> Dict:
        """Render the final verdict after all defence turns are spent OR the
        defendant rests their case OR the judge cuts proceedings short.

        Returns the same shape as `narrate_trial`, plus a `leniency_score` echo:
            {
              "narration": str,
              "sentence_type": "fine|imprison|exile|execute|dismissed",
              "fine_amount": int,
              "imprison_turns": int,
              "jail_location": str,
              "verdict_summary": str,
              "leniency_score": int
            }
        """
        history_lines = []
        for h in (defense_history or [])[-8:]:
            history_lines.append(
                f"  - Turn {h.get('turn','?')}: leniency Δ {h.get('leniency_delta',0):+d}. "
                f"Defence: \"{(h.get('defence_text','') or '')[:160]}\""
            )
        history_block = "\n".join(history_lines) if history_lines else "  (no defence offered)"

        system_message = (
            self.DELAROM_LORE
            + "\n\nYou are the presiding judge delivering the final verdict. Use the "
            + "full defence history and the final leniency tally to pick a fair sentence. "
            + "Return STRICT JSON only."
        )

        prompt = f"""
COURTROOM: {_pretty(courthouse_location)} in {_pretty(nation)}
JUDGE: {judge_name}
DEFENDANT: {character_name}
BASELINE SENTENCE (before defence): {baseline_sentence}
FINAL LENIENCY TALLY (HIDDEN — for your sentencing only): {final_leniency:+d} / -100..+100
TOTAL BOUNTY AT INDICTMENT: {total_bounty}g

CHARGES:
{self._format_charges(open_crimes)}

DEFENCE HISTORY:
{history_block}

SENTENCING GUIDE (apply the leniency tally to the baseline):
  +50 or higher → dismissed OR fine reduced to a token (10-50g)
  +25..+49     → reduce: fine instead of jail, OR halve imprisonment turns
  +5..+24      → mild reduction (-25% turns, OR shave 1-2 turns off small sentences)
  -4..+4       → baseline sentence stands
  -5..-24      → mild increase (+25% turns or add a fine)
  -25..-49     → escalate one tier (fine → jail, jail → exile, jail → longer jail)
  -50 or lower → escalate strongly (jail → execution if any open capital/regicide; major
                 jail extended significantly; exile if no capital available)

Narrate the verdict in 3-6 sentences (the judge addressing the chamber, the
gavel falling, the prosecutor's nod, any witness's reaction). T1 rules apply
— do not voice or act for the defendant. Then return JSON with EXACTLY:

{{
  "narration": "<3-6 sentences>",
  "sentence_type": "<fine|imprison|exile|execute|dismissed>",
  "fine_amount": <integer gold>,
  "imprison_turns": <integer turns>,
  "jail_location": "<jail slug or empty string>",
  "verdict_summary": "<one-sentence summary>",
  "leniency_score": {final_leniency}
}}

Output JSON ONLY.
"""
        try:
            chat = LlmChat(
                api_key=self.api_key,
                session_id=f"verdict_{courthouse_location}_{_rng.randint(0,99999)}",
                system_message=system_message,
            ).with_model("openai", "gpt-4o-mini")
            response = await chat.send_message(UserMessage(text=prompt))
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Verdict narration failed: {e}")
            return {
                "narration": (
                    "The judge weighs the defence in silence and delivers the baseline sentence."
                ),
                "sentence_type": baseline_sentence.get("sentence_type", "imprison"),
                "fine_amount": baseline_sentence.get("fine_amount", 0),
                "imprison_turns": baseline_sentence.get("imprison_turns", 5),
                "jail_location": "",
                "verdict_summary": "Baseline sentence (AI unavailable).",
                "leniency_score": final_leniency,
            }

        result = _safe_parse_json(response) or {}
        st = result.get("sentence_type") or baseline_sentence.get("sentence_type", "imprison")
        if st not in ("fine", "imprison", "exile", "execute", "dismissed"):
            st = "imprison"
        result["sentence_type"] = st
        result.setdefault("narration", "")
        result.setdefault("verdict_summary", "")
        result["fine_amount"] = max(0, int(result.get("fine_amount", 0) or 0))
        result["imprison_turns"] = max(0, int(result.get("imprison_turns", 0) or 0))
        result.setdefault("jail_location", "")
        result["leniency_score"] = final_leniency
        if st == "imprison" and result["imprison_turns"] == 0:
            result["imprison_turns"] = baseline_sentence.get("imprison_turns", 3) or 3
        return result

    # ============================================================
    # ECONOMY — infer price impact of world events
    # ============================================================

    async def infer_economy_event_impact(
        self,
        *,
        event_type: str,
        event_summary: str,
        event_details: str,
        nations: List[str],
        candidate_goods: List[Dict],
    ) -> List[Dict]:
        """Given a world event + the goods that COULD be affected, ask the AI
        which specific goods move and by how much.

        Returns a list of `{good_slug: str, delta_pct: int, reason: str}`.
        delta_pct is the percentage change to apply to the affected faction
        specialty's base_cost. Positive = inflation, negative = deflation.
        Clamped to [-50, +50] by the caller.
        """
        if not candidate_goods:
            return []
        goods_block = "\n".join(
            f"  - {g['slug']} ({g['name']}, {g['category']}, tags: {','.join(g.get('tags', []))})"
            for g in candidate_goods[:20]
        )
        prompt = f"""
WORLD EVENT
-----------
Type: {event_type}
Nations: {', '.join(nations) or '(unspecified)'}
Summary: {event_summary}
Details: {event_details[:600]}

CANDIDATE GOODS (already prefiltered by tags):
{goods_block}

TASK:
Decide which of these goods will see a meaningful price change as a result of
this event, and by what percentage. Apply economic reasoning:
  - A war event raises weapons, armor, hard tack, metal.
  - A festival raises wine and luxuries; may briefly raise food.
  - A drought lowers grain availability so its price rises.
  - A bumper harvest does the opposite.
  - Disasters cause shortages → inflation; recoveries → deflation.

Bounded delta_pct per good: -50..+50. Use 0 for goods you'd leave unchanged
(omit those from the array). Keep the list short — only the 1-5 most relevant
goods.

Return STRICT JSON:
{{
  "impacts": [
    {{ "good_slug": "<slug from the candidate list>",
       "delta_pct": <integer -50..+50>,
       "reason": "<one-line cause>" }}
  ]
}}

Output JSON ONLY.
"""
        try:
            chat = LlmChat(
                api_key=self.api_key,
                session_id=f"econ_event_{event_type}_{_rng.randint(0,99999)}",
                system_message=self.DELAROM_LORE + "\nYou advise the Realm's Royal Mint on price impacts.",
            ).with_model("openai", "gpt-4o-mini")
            response = await chat.send_message(UserMessage(text=prompt))
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Economy event inference failed: {e}")
            return []

        parsed = _safe_parse_json(response) or {}
        out: List[Dict] = []
        for row in (parsed.get("impacts") or [])[:8]:
            if not isinstance(row, dict):
                continue
            slug = (row.get("good_slug") or "").strip()
            try:
                delta = int(row.get("delta_pct", 0))
            except (TypeError, ValueError):
                delta = 0
            if not slug or delta == 0:
                continue
            delta = max(-50, min(50, delta))
            out.append({
                "good_slug": slug,
                "delta_pct": delta,
                "reason": (row.get("reason") or "")[:160],
            })
        return out


def _pretty(slug: str) -> str:
    return " ".join(p.capitalize() for p in (slug or "").split("-")) if slug else ""
