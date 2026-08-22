#!/usr/bin/env python3
"""
Bug Demonstration: Quest Completion Implementation Issue

This test demonstrates the critical bug in the quest completion implementation.
The current code looks for quest acceptances where user_id = current_user.id (quest creator),
but quest creators don't accept their own quests - participants do!
"""

import asyncio
import aiohttp
import json
import time
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv('/app/frontend/.env')

# Get backend URL from frontend env
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'http://localhost:8001')
API_BASE = f"{BACKEND_URL}/api"

async def demonstrate_bug():
    """Demonstrate the quest completion bug"""
    print("🐛 DEMONSTRATING QUEST COMPLETION BUG")
    print("=" * 60)
    
    async with aiohttp.ClientSession() as session:
        # Login as admin (quest creator)
        admin_credentials = {
            "email": "craftnn1222@gmail.com",
            "password": "admin123"
        }
        
        async with session.post(f"{API_BASE}/auth/login", json=admin_credentials) as response:
            if response.status != 200:
                print("❌ Admin login failed")
                return
            
            admin_data = await response.json()
            admin_token = admin_data["access_token"]
            admin_user_id = admin_data["user"]["id"]
            print(f"✅ Admin logged in: {admin_data['user']['username']}")
        
        # Check if admin has any quest acceptances (they shouldn't!)
        headers = {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}
        
        async with session.get(f"{API_BASE}/quests/my-quests/accepted", headers=headers) as response:
            if response.status == 200:
                acceptances = await response.json()
                print(f"🔍 Admin's quest acceptances: {len(acceptances)}")
                
                if len(acceptances) == 0:
                    print("✅ CORRECT: Admin (quest creator) has no quest acceptances")
                    print("   Quest creators don't accept their own quests!")
                else:
                    print("⚠️  Admin has quest acceptances (unusual)")
                    for acc in acceptances:
                        print(f"   - Quest: {acc['quest']['title']}")
            else:
                print("❌ Failed to get admin's acceptances")
        
        # Now demonstrate the bug in the code
        print("\n🔍 ANALYZING THE BUG:")
        print("Current implementation (lines 1126-1130 in server.py):")
        print("```python")
        print("acceptance_doc = await db.quest_acceptances.find_one({")
        print("    'quest_id': quest_id,")
        print("    'user_id': current_user.id,  # ← BUG: This is the quest creator!")
        print("    'status': 'accepted'")
        print("})")
        print("```")
        print()
        print("❌ PROBLEM: Quest creators don't accept their own quests!")
        print("❌ This query will almost always return None")
        print("❌ The acceptance_id parameter is completely ignored!")
        print()
        print("✅ CORRECT implementation should be:")
        print("```python")
        print("acceptance_doc = await db.quest_acceptances.find_one({")
        print("    'id': acceptance_id,  # ← Use the acceptance_id parameter")
        print("    'quest_id': quest_id,")
        print("    'status': 'accepted'")
        print("})")
        print("```")
        print()
        print("🔧 IMPACT:")
        print("- Quest completion may fail in many cases")
        print("- The acceptance_id parameter is ignored")
        print("- Only works if quest creator somehow has acceptances")

if __name__ == "__main__":
    asyncio.run(demonstrate_bug())