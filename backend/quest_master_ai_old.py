"""
AI Quest Master - Handles quest roleplay and T1 combat
"""
from emergentintegrations.llm.chat import LlmChat, UserMessage
import os
from typing import Dict, List
import json

class QuestMasterAI:
    """AI that roleplays quests and enforces T1 combat rules"""
    
    DELAROM_LORE = """
=== CONTINENTS OF DELAROM - COMPLETE LORE ===

WORLD OVERVIEW:
The year is 215 A.E. (Astral Era). Delarom is a world of infinite possibilities where freedom reigns and individuals shape their own destinies. After "The Shattering," the old divine order crumbled, leaving civilizations to rebuild without rigid hierarchies.

MAJOR NATIONS:

**AMMEONON** - The Human Empire
- Capital: Wymroost (largest port city on continent, 150 ship capacity)
- Major Cities: Invrasil (City of Mages with Wemorth & Ofeline Academies), Skooma (brewer's town), Azure (flower town), Wyndell (martial arts haven practicing Coupe De Vitesse)
- Ruler: Vritra Clan led by Ausar, the Astral King (celestial being who defeated the Seven Titans 5018-5088)
- History: Founded 1200 by King Quentin Blackburn, flourished under Nalviem dynasty, transformed by Ausar's arrival in 2107
- The Seven Titans (Flame, Stone, Wind, Tide, Shadow, Frost, Decay) ravaged the land until Ausar defeated them
- Culture: Freedom, trade, prosperity, diverse

**SELINDORI** - The Elven Kingdoms
- Capital: Yillhone (crystal city built by Goddess Seren)
- Divided into multiple kingdoms, each ruled by different elven noble houses
- Created by Seren, Goddess of Life (Elder God)
- Known for: Magic, longevity, connection to nature
- Architecture: Crystal cities, ethereal and magical

**DHOR-KULDOR** - The Dwarven Holds
- Eight dwarven holds carved into mountains
- Major Holds: Thalgrin (gems/jewels), Ironforge (forges/smithies)
- Patron God: Yros, God of Earth (Elder God, youngest of four creators)
- Known for: Mining, crafting, stonework, forge-fires never die
- Culture: Deep earth connection, expert craftsmen
- War History: Severed ties with Ammeonon 4715-4950 under Emperor Galphio Selimore's puritanical rule, peace restored by Emperor Augusto

**AIGRAELS** - The Fractured Kingdom
- Status: Civil war, constantly changing rulers
- Three Major Factions (The Triumvirate):
  1. **Ardent Legion** (North) - Military dictatorship led by General Serus Valthar, capital Ironhold
  2. **Forsaken Court** (Shadows) - Aristocratic shadow government led by Lady Selene Valthos, operates from House of Veils
  3. **Elderborn Alliance** - Scholarly/magical faction led by High Sage Eloria Nyx, base at Library of Astral Light
- History: Once proud Aerdrath kingdom, destroyed in "The Shattering"
- No permanent leader, seat of power changes yearly

ELDER GODS (Cannot descend to mortal realm):
- **Ehena** - Goddess of Time, Queen of Gods, oldest and most powerful, controls all temporal flow
- **Seren** - Goddess of Life, Mother of Elves, creator of Yillhone, nurturing spirit
- **Yros** - God of Earth, youngest creator, playful but powerful, shaped mountains/valleys/rivers
- **Uesis** - God of Heavens, dragon-celestial hybrid, created day/night/stars, speaks through omens

MAGIC SYSTEM (ACT - Astral Conversion Theory):
- Based on E=mc² and ancient Hindu concept of Shakti
- **Astral Energy** - Infinite cosmic source predating universe, flows through meta-verse
- Converts to **Mana** through planetary membranes
- **Elemental Essences** (earth, fire, water, air) bind atoms together
- **Chakras** - Energy centers allowing astral manipulation
- **Celestial Energy** - Divine light, pure, healing, order
- **Infernal Energy** - Demonic chaos, destructive transformation, change
- Magic manipulates fundamental universe energies through mana and essence

NOTABLE LOCATIONS:
- **Wymroost**: Vibrant port, monthly festivals, taverns/inns/clubs, magical markets, diverse cuisine
- **Invrasil**: Wemorth & Ofeline Academies, Veneficus Stadium (Magic Competition), Hastburn Alley (magical marketplace)
- **Yillhone**: Crystal elven city built by Goddess Seren
- **Twilight Throne**: Created when Ausar descended from heavens in 2107, mountains erupted

KEY HISTORICAL EVENTS:
- 1200: Ammeonon founded by King Quentin Blackburn
- 2107: Ausar descends, creates Twilight Throne
- 4715-4950: Human-Dwarf War under Emperor Galphio's puritanism
- 5018-5088: Age of Titans, Ausar defeats Seven Titans
- 5088-Present (215 A.E.): Astral Era, peace and prosperity under Vritra Clan

WORLD PHILOSOPHY:
- No predetermined paths, complete freedom
- Kingdoms rise/fall by ambition and will
- Economy driven by player actions, not central government
- Magic is untamed, powerful, dangerous
- Each individual shapes their own legacy
"""
    
    T1_RULES = """
You are the Quest Master AI for Continents of Delarom. Follow these T1 (Tier 1) Combat Rules STRICTLY:

T1 COMBAT RULES:
1. ATTEMPT-BASED ACTIONS: All attacks/actions MUST be written as attempts, never auto-hits
   - Good: "The dragon attempts to breathe fire at the warrior"
   - Bad: "The dragon burns the warrior with fire"

2. FAIR PLAY: Give opponents reasonable chance to respond/dodge/counter
   - Actions should be logical and fair
   - No god-modding (controlling other characters)
   - No meta-gaming (using out-of-character knowledge)

3. TURN-BASED: Each participant gets turns to respond
   - Wait for responses before continuing
   - Respect posting order

4. DESCRIPTIVE ROLEPLAY: Be cinematic and descriptive
   - Describe environment, actions, emotions
   - Make it engaging and immersive

5. CONSEQUENCES: Actions have realistic consequences
   - Successful attacks cause damage
   - Failed dodges result in hits
   - Energy/stamina matters

YOUR ROLE:
- Roleplay as NPCs, enemies, and environment using DELAROM LORE
- Reference nations, cities, gods, and history accurately
- Use lore-appropriate language and cultural details
- Narrate quest events dynamically within Delarom's world
- React to player actions fairly
- Enforce T1 rules
- Track quest progress
- Create engaging challenges rooted in Delarom lore

RESPONSE FORMAT:
Always respond in character as the NPC/enemy/narrator. Be dramatic, engaging, lore-accurate, and follow T1 rules.
"""
    
    def __init__(self):
        self.api_key = os.environ.get('EMERGENT_LLM_KEY')
        if not self.api_key:
            raise ValueError("EMERGENT_LLM_KEY not found in environment")
    
    async def initialize_quest(self, quest_data: Dict) -> str:
        """Initialize quest and create opening narration"""
        full_system_message = self.DELAROM_LORE + "\n\n" + self.T1_RULES
        
        chat = LlmChat(
            api_key=self.api_key,
            session_id=f"quest_{quest_data['id']}",
            system_message=full_system_message
        ).with_model("openai", "gpt-4o-mini")
        
        context = f"""
QUEST INITIALIZATION:
Title: {quest_data['title']}
Description: {quest_data['description']}
Difficulty: {quest_data['difficulty']}
Nation: {quest_data['nation']}
Category: {quest_data['category']}

Create an engaging opening narration for this quest. Set the scene, introduce the challenge/enemy, 
and create atmosphere. Be dramatic and immersive. End with anticipation for the adventurers' arrival.
"""
        
        message = UserMessage(text=context)
        response = await chat.send_message(message)
        return response
    
    async def respond_to_action(
        self, 
        quest_data: Dict, 
        action_history: List[Dict], 
        new_action: Dict
    ) -> Dict:
        """
        Respond to a player's action following T1 rules
        Returns: {
            'narration': str,
            'is_valid': bool,
            't1_feedback': str (if invalid),
            'quest_status': 'active' | 'completed' | 'failed'
        }
        """
        full_system_message = self.DELAROM_LORE + "\n\n" + self.T1_RULES
        
        chat = LlmChat(
            api_key=self.api_key,
            session_id=f"quest_{quest_data['id']}",
            system_message=full_system_message
        ).with_model("openai", "gpt-4o-mini")
        
        # Build context
        context = f"""
QUEST: {quest_data['title']}
Description: {quest_data['description']}
Difficulty: {quest_data['difficulty']}

ACTION HISTORY:
"""
        for action in action_history[-5:]:  # Last 5 actions for context
            context += f"\n{action['character_name']}: {action['action_text']}"
            if action.get('ai_response'):
                context += f"\n[Quest Master]: {action['ai_response']}"
        
        context += f"""

NEW ACTION:
{new_action['character_name']} ({new_action['character_race']} {new_action['character_class']}): {new_action['action_text']}

DICE ROLL RESULT:
- D20 Roll: {new_action.get('dice_roll', 'N/A')}
- Modifier: {new_action.get('modifier', 0)}
- Total: {new_action.get('total_roll', 'N/A')}
{'- CRITICAL HIT! (Natural 20)' if new_action.get('was_critical') else ''}
{'- CRITICAL FUMBLE! (Natural 1)' if new_action.get('was_fumble') else ''}

TASK:
1. First, validate if this action follows T1 rules (is it an attempt? does it god-mod?)
2. If valid, roleplay the response as the NPC/enemy/environment
3. Consider the dice roll result when describing the outcome:
   - Low rolls (1-5): failure or poor outcome
   - Medium rolls (6-14): partial success or standard outcome
   - High rolls (15-19): good success
   - Critical (20): exceptional success, extra effect
   - Fumble (1): catastrophic failure, backfire
4. Describe the outcome dramatically based on the roll
5. Continue the scene and create the next challenge/moment
6. If the quest objective seems completed, indicate quest completion

Respond in JSON format:
{
    "is_valid": true/false,
    "t1_feedback": "explanation if invalid, empty if valid",
    "narration": "your roleplay response",
    "quest_status": "active" or "completed" or "failed",
    "completion_reason": "why quest completed/failed if applicable"
}
"""
        
        message = UserMessage(text=context)
        response = await chat.send_message(message)
        
        # Parse JSON response
        try:
            result = json.loads(response)
            return result
        except json.JSONDecodeError:
            # Fallback if AI doesn't return valid JSON
            return {
                'is_valid': True,
                't1_feedback': '',
                'narration': response,
                'quest_status': 'active',
                'completion_reason': ''
            }
    
    async def generate_combat_opponent(self, quest_data: Dict) -> str:
        """Generate description of combat opponent for quest"""
        full_system_message = self.DELAROM_LORE + "\n\nYou create engaging fantasy combat opponents rooted in Delarom lore. Use nations, magic systems, and world details."
        
        chat = LlmChat(
            api_key=self.api_key,
            session_id=f"quest_gen_{quest_data['id']}",
            system_message=full_system_message
        ).with_model("openai", "gpt-4o-mini")
        
        context = f"""
Create a combat opponent for this quest:
Title: {quest_data['title']}
Description: {quest_data['description']}
Difficulty: {quest_data['difficulty']}

Describe the opponent's appearance, abilities, and fighting style in 2-3 paragraphs.
Make it match the difficulty level.
"""
        
        message = UserMessage(text=context)
        response = await chat.send_message(message)
        return response
    
    async def evaluate_quest_completion(
        self,
        quest_data: Dict,
        action_history: List[Dict]
    ) -> Dict:
        """
        Evaluate if quest objectives have been met
        Returns: {'should_complete': bool, 'reason': str}
        """
        full_system_message = self.DELAROM_LORE + "\n\n" + self.T1_RULES
        
        chat = LlmChat(
            api_key=self.api_key,
            session_id=f"quest_eval_{quest_data['id']}",
            system_message=full_system_message
        ).with_model("openai", "gpt-4o-mini")
        
        context = f"""
QUEST: {quest_data['title']}
Objective: {quest_data['description']}

ACTIONS TAKEN:
"""
        for action in action_history:
            context += f"\n- {action['character_name']}: {action['action_text']}"
            if action.get('ai_response'):
                context += f"\n  [Result]: {action['ai_response'][:200]}"
        
        context += """

Evaluate if the quest objectives have been reasonably completed based on the actions taken.
Respond in JSON:
{
    "should_complete": true/false,
    "reason": "explanation of why quest should/shouldn't be complete",
    "success_level": "excellent" or "good" or "adequate" or "failed"
}
"""
        
        message = UserMessage(text=context)
        response = await chat.send_message(message)
        
        try:
            result = json.loads(response)
            return result
        except json.JSONDecodeError:
            return {
                'should_complete': False,
                'reason': 'Unable to evaluate',
                'success_level': 'adequate'
            }
