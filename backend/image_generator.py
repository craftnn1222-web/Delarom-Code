"""
AI Image Generator for Continents of Delarom
Uses OpenAI gpt-image-1 via Emergent LLM key
"""
import os
import base64
from dotenv import load_dotenv
from emergentintegrations.llm.openai.image_generation import OpenAIImageGeneration

load_dotenv()

class ImageGenerator:
    """Generate images for quests, characters, and locations"""
    
    def __init__(self):
        self.api_key = os.environ.get('EMERGENT_LLM_KEY')
        if not self.api_key:
            raise ValueError("EMERGENT_LLM_KEY not found")
        self.image_gen = OpenAIImageGeneration(api_key=self.api_key)
    
    async def generate_quest_image(self, quest_data: dict) -> str:
        """Generate an opening scene image for a quest - returns base64 encoded image"""
        prompt = f"""
Fantasy RPG scene: {quest_data['title']}. 
{quest_data['description']}
Setting: {quest_data['nation']}, {quest_data['category']} quest.
Difficulty: {quest_data['difficulty']}.

Style: Epic fantasy illustration, cinematic, detailed, atmospheric lighting.
High quality digital art.
"""
        
        try:
            images = await self.image_gen.generate_images(
                prompt=prompt,
                model="gpt-image-1",
                number_of_images=1
            )
            
            if images and len(images) > 0:
                # Convert to base64 for easy storage and display
                image_base64 = base64.b64encode(images[0]).decode('utf-8')
                return f"data:image/png;base64,{image_base64}"
            else:
                print("No image was generated")
                return None
        except Exception as e:
            print(f"Image generation error: {e}")
            return None
    
    async def generate_character_portrait(self, character_data: dict) -> str:
        """Generate a portrait for a character - returns base64 encoded image"""
        prompt = f"""
Fantasy character portrait: {character_data['name']}, a {character_data['race']} {character_data['character_class']}.
Appearance: {character_data['appearance']}
Powers: {character_data['powers']}

Style: Character portrait, detailed face, fantasy art, digital painting, high quality.
From the shoulders up, facing forward, dramatic lighting.
"""
        
        try:
            images = await self.image_gen.generate_images(
                prompt=prompt,
                model="gpt-image-1",
                number_of_images=1
            )
            
            if images and len(images) > 0:
                # Convert to base64 for easy storage and display
                image_base64 = base64.b64encode(images[0]).decode('utf-8')
                return f"data:image/png;base64,{image_base64}"
            else:
                print("No image was generated")
                return None
        except Exception as e:
            print(f"Image generation error: {e}")
            return None
    
    async def generate_location_image(self, nation: str, location: str) -> str:
        """Generate an image for a location - returns base64 encoded image"""
        location_descriptions = {
            'wymroost': 'Grand capital city with towering spires and the Astral King\'s palace',
            'invrasil': 'Bustling trading city with markets and merchant ships',
            'thalgrin': 'Dwarven hold filled with gems and jewels, crystal caverns',
            'ironforge': 'Massive forges and smithies, molten metal flowing',
            'yillhone': 'Crystal city of elves, ethereal and magical'
        }
        
        desc = location_descriptions.get(location.lower(), f'{location} in {nation}')
        
        prompt = f"""
Fantasy location: {location} in {nation}.
{desc}

Style: Epic fantasy landscape, cinematic wide shot, atmospheric, detailed architecture.
High quality digital art, immersive fantasy scene.
"""
        
        try:
            images = await self.image_gen.generate_images(
                prompt=prompt,
                model="gpt-image-1",
                number_of_images=1
            )
            
            if images and len(images) > 0:
                # Convert to base64 for easy storage and display
                image_base64 = base64.b64encode(images[0]).decode('utf-8')
                return f"data:image/png;base64,{image_base64}"
            else:
                print("No image was generated")
                return None
        except Exception as e:
            print(f"Image generation error: {e}")
            return None
