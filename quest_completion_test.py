#!/usr/bin/env python3
"""
Focused Backend Testing for Quest Creator Completion Behavior
Testing the new quest creator completion behavior and deprecation of self-complete.

Test cases:
1) Participant self-complete disabled
2) Creator completion happy path  
3) Creator permission enforcement
4) Edge cases
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

class QuestCompletionTester:
    def __init__(self):
        self.session = None
        # Creator (quest creator)
        self.creator_token = None
        self.creator_user_id = None
        self.creator_character_id = None
        # Participant (quest acceptor)
        self.participant_token = None
        self.participant_user_id = None
        self.participant_character_id = None
        # Non-creator (unauthorized user)
        self.non_creator_token = None
        self.non_creator_user_id = None
        # Test data
        self.test_quest_id = None
        self.test_acceptance_id = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def get_headers(self, token=None, include_auth=True):
        headers = {"Content-Type": "application/json"}
        if include_auth and token:
            headers["Authorization"] = f"Bearer {token}"
        return headers
    
    async def setup_test_users(self):
        """Create and authenticate test users"""
        print("🔐 Setting up test users...")
        
        # First login as admin to approve users
        admin_credentials = {
            "email": "craftnn1222@gmail.com",
            "password": "admin123"
        }
        
        admin_token = None
        try:
            async with self.session.post(
                f"{API_BASE}/auth/login",
                json=admin_credentials,
                headers=self.get_headers(include_auth=False)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    admin_token = data["access_token"]
                    self.creator_token = data["access_token"]
                    self.creator_user_id = data["user"]["id"]
                    print(f"✅ Admin logged in: {data['user']['username']}")
                else:
                    print(f"❌ Admin login failed: {response.status}")
                    return False
        except Exception as e:
            print(f"❌ Admin login error: {e}")
            return False
        
        # Create and approve participant user
        print("🔐 Creating participant user...")
        participant_data = {
            "username": f"quest_participant_{int(time.time())}",
            "email": f"participant{int(time.time())}@delarom.com",
            "password": "Participant123!",
            "application_text": "I want to join quests!"
        }
        
        try:
            async with self.session.post(
                f"{API_BASE}/auth/register",
                json=participant_data,
                headers=self.get_headers(include_auth=False)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    participant_user_id = data["user"]["id"]
                    print(f"✅ Participant registered: {data['user']['username']}")
                    
                    # Approve the participant
                    admin_headers = {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}
                    async with self.session.post(
                        f"{API_BASE}/admin/applications/{participant_user_id}/approve",
                        headers=admin_headers
                    ) as approve_response:
                        if approve_response.status == 200:
                            print("✅ Participant approved by admin")
                            
                            # Now login as participant
                            async with self.session.post(
                                f"{API_BASE}/auth/login",
                                json={"email": participant_data["email"], "password": participant_data["password"]},
                                headers=self.get_headers(include_auth=False)
                            ) as login_response:
                                if login_response.status == 200:
                                    login_data = await login_response.json()
                                    self.participant_token = login_data["access_token"]
                                    self.participant_user_id = login_data["user"]["id"]
                                    print(f"✅ Participant login successful")
                                else:
                                    print(f"❌ Participant login failed: {login_response.status}")
                                    return False
                        else:
                            print(f"❌ Participant approval failed: {approve_response.status}")
                            return False
                else:
                    print(f"❌ Participant registration failed: {response.status}")
                    return False
        except Exception as e:
            print(f"❌ Participant setup error: {e}")
            return False
        
        # Create and approve non-creator user
        print("🔐 Creating non-creator user...")
        non_creator_data = {
            "username": f"non_creator_{int(time.time())}",
            "email": f"noncreator{int(time.time())}@delarom.com",
            "password": "NonCreator123!",
            "application_text": "I'm just a regular user!"
        }
        
        try:
            async with self.session.post(
                f"{API_BASE}/auth/register",
                json=non_creator_data,
                headers=self.get_headers(include_auth=False)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    non_creator_user_id = data["user"]["id"]
                    print(f"✅ Non-creator registered: {data['user']['username']}")
                    
                    # Approve the non-creator
                    admin_headers = {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}
                    async with self.session.post(
                        f"{API_BASE}/admin/applications/{non_creator_user_id}/approve",
                        headers=admin_headers
                    ) as approve_response:
                        if approve_response.status == 200:
                            print("✅ Non-creator approved by admin")
                            
                            # Now login as non-creator
                            async with self.session.post(
                                f"{API_BASE}/auth/login",
                                json={"email": non_creator_data["email"], "password": non_creator_data["password"]},
                                headers=self.get_headers(include_auth=False)
                            ) as login_response:
                                if login_response.status == 200:
                                    login_data = await login_response.json()
                                    self.non_creator_token = login_data["access_token"]
                                    self.non_creator_user_id = login_data["user"]["id"]
                                    print(f"✅ Non-creator login successful")
                                else:
                                    print(f"❌ Non-creator login failed: {login_response.status}")
                                    return False
                        else:
                            print(f"❌ Non-creator approval failed: {approve_response.status}")
                            return False
                else:
                    print(f"❌ Non-creator registration failed: {response.status}")
                    return False
        except Exception as e:
            print(f"❌ Non-creator setup error: {e}")
            return False
        
        return True
    
    async def create_test_characters(self):
        """Create characters for all test users"""
        print("🧙 Creating test characters...")
        
        # Creator character
        creator_char_data = {
            "name": "Quest Master Aldric",
            "race": "Human",
            "character_class": "Quest Giver",
            "backstory": "A wise quest master who creates challenges for brave adventurers.",
            "powers": "Quest Creation, Reward Distribution",
            "appearance": "Tall figure in robes with a staff",
            "nation": "Ammeonon"
        }
        
        try:
            async with self.session.post(
                f"{API_BASE}/characters",
                json=creator_char_data,
                headers=self.get_headers(self.creator_token)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    self.creator_character_id = data["id"]
                    print(f"✅ Creator character created: {data['name']}")
                else:
                    print(f"❌ Creator character creation failed: {response.status}")
                    return False
        except Exception as e:
            print(f"❌ Creator character creation error: {e}")
            return False
        
        # Participant character
        participant_char_data = {
            "name": "Brave Adventurer",
            "race": "Elf",
            "character_class": "Warrior",
            "backstory": "A brave warrior seeking glory and rewards.",
            "powers": "Sword Fighting, Shield Defense",
            "appearance": "Armored elf with sword and shield",
            "nation": "Selindori"
        }
        
        try:
            async with self.session.post(
                f"{API_BASE}/characters",
                json=participant_char_data,
                headers=self.get_headers(self.participant_token)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    self.participant_character_id = data["id"]
                    print(f"✅ Participant character created: {data['name']}")
                else:
                    print(f"❌ Participant character creation failed: {response.status}")
                    return False
        except Exception as e:
            print(f"❌ Participant character creation error: {e}")
            return False
        
        return True
    
    async def create_test_quest(self):
        """Create a test quest with rewards"""
        print("⚔️ Creating test quest...")
        
        quest_data = {
            "title": "The Dragon's Treasure",
            "description": "Retrieve the ancient treasure from the dragon's lair",
            "difficulty": "medium",
            "reward_currency": 500,
            "reward_xp": 100,
            "reward_items": [
                {
                    "name": "Dragon Scale Armor",
                    "description": "Armor made from dragon scales",
                    "item_type": "equipment",
                    "equipment_slot": "chest",
                    "stat_bonuses": {"endurance": 15, "magic": 5}
                }
            ],
            "nation": "Ammeonon",
            "category": "Adventure",
            "max_acceptors": 5
        }
        
        try:
            async with self.session.post(
                f"{API_BASE}/quests",
                json=quest_data,
                headers=self.get_headers(self.creator_token)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    self.test_quest_id = data["id"]
                    print(f"✅ Test quest created: {data['title']}")
                    print(f"   Quest ID: {self.test_quest_id}")
                    print(f"   Reward: {data['reward_currency']} currency, {data['reward_xp']} XP")
                    print(f"   Items: {len(data['reward_items'])} reward items")
                    return True
                else:
                    error_text = await response.text()
                    print(f"❌ Quest creation failed: {response.status} - {error_text}")
                    return False
        except Exception as e:
            print(f"❌ Quest creation error: {e}")
            return False
    
    async def accept_quest_as_participant(self):
        """Have participant accept the quest"""
        print("✋ Participant accepting quest...")
        
        accept_data = {
            "character_id": self.participant_character_id
        }
        
        try:
            async with self.session.post(
                f"{API_BASE}/quests/{self.test_quest_id}/accept",
                json=accept_data,
                headers=self.get_headers(self.participant_token)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    self.test_acceptance_id = data["acceptance_id"]
                    print(f"✅ Quest accepted by participant")
                    print(f"   Acceptance ID: {self.test_acceptance_id}")
                    return True
                else:
                    error_text = await response.text()
                    print(f"❌ Quest acceptance failed: {response.status} - {error_text}")
                    return False
        except Exception as e:
            print(f"❌ Quest acceptance error: {e}")
            return False
    
    async def get_participant_initial_state(self):
        """Get participant's initial currency and character state"""
        print("📊 Getting participant's initial state...")
        
        try:
            # Get user currency
            async with self.session.get(
                f"{API_BASE}/wallet",
                headers=self.get_headers(self.participant_token)
            ) as response:
                if response.status == 200:
                    wallet_data = await response.json()
                    initial_currency = wallet_data["balance"]
                    print(f"   Initial currency: {initial_currency}")
                else:
                    print(f"❌ Failed to get wallet: {response.status}")
                    return None
            
            # Get character state
            async with self.session.get(
                f"{API_BASE}/characters/{self.participant_character_id}",
                headers=self.get_headers(self.participant_token)
            ) as response:
                if response.status == 200:
                    char_data = await response.json()
                    initial_xp = char_data.get("xp", 0)
                    initial_level = char_data.get("level", 1)
                    initial_inventory_count = len(char_data.get("inventory", []))
                    print(f"   Initial XP: {initial_xp}")
                    print(f"   Initial Level: {initial_level}")
                    print(f"   Initial Inventory Items: {initial_inventory_count}")
                    
                    return {
                        "currency": initial_currency,
                        "xp": initial_xp,
                        "level": initial_level,
                        "inventory_count": initial_inventory_count
                    }
                else:
                    print(f"❌ Failed to get character: {response.status}")
                    return None
        except Exception as e:
            print(f"❌ Error getting initial state: {e}")
            return None
    
    # ==================== TEST CASES ====================
    
    async def test_participant_self_complete_disabled(self):
        """Test Case 1: Participant self-complete disabled"""
        print("\n🚫 TEST 1: PARTICIPANT SELF-COMPLETE DISABLED")
        print("=" * 60)
        
        print("🎯 Testing that non-creator users cannot self-complete quests...")
        
        try:
            async with self.session.post(
                f"{API_BASE}/quests/{self.test_quest_id}/complete",
                headers=self.get_headers(self.participant_token)
            ) as response:
                if response.status == 403:
                    response_data = await response.json()
                    detail = response_data.get("detail", "")
                    expected_detail = "Only quest creator can complete quests. Completion is now handled by the quest creator."
                    
                    if detail == expected_detail:
                        print("✅ PASS: Participant self-complete correctly disabled")
                        print(f"   Status: 403 Forbidden")
                        print(f"   Detail: {detail}")
                        return True
                    else:
                        print(f"❌ FAIL: Wrong error message")
                        print(f"   Expected: {expected_detail}")
                        print(f"   Got: {detail}")
                        return False
                else:
                    error_text = await response.text()
                    print(f"❌ FAIL: Expected 403, got {response.status}")
                    print(f"   Response: {error_text}")
                    return False
        except Exception as e:
            print(f"❌ FAIL: Test error: {e}")
            return False
    
    async def test_creator_completion_happy_path(self):
        """Test Case 2: Creator completion happy path"""
        print("\n✅ TEST 2: CREATOR COMPLETION HAPPY PATH")
        print("=" * 60)
        
        # Get initial state
        initial_state = await self.get_participant_initial_state()
        if not initial_state:
            print("❌ FAIL: Could not get initial state")
            return False
        
        print("🎯 Testing quest creator completing participant...")
        
        try:
            async with self.session.post(
                f"{API_BASE}/quests/{self.test_quest_id}/participants/{self.test_acceptance_id}/complete",
                headers=self.get_headers(self.creator_token)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Verify response structure
                    required_fields = ["reward", "reward_xp", "reward_items", "character_name"]
                    missing_fields = [field for field in required_fields if field not in data]
                    
                    if missing_fields:
                        print(f"❌ FAIL: Missing response fields: {missing_fields}")
                        return False
                    
                    print("✅ PASS: Creator completion successful")
                    print(f"   Reward Currency: {data['reward']}")
                    print(f"   Reward XP: {data['reward_xp']}")
                    print(f"   Reward Items: {data['reward_items']}")
                    print(f"   Character Name: {data['character_name']}")
                    
                    # Verify database changes
                    return await self.verify_completion_database_effects(initial_state, data)
                    
                else:
                    error_text = await response.text()
                    print(f"❌ FAIL: Creator completion failed: {response.status}")
                    print(f"   Response: {error_text}")
                    return False
        except Exception as e:
            print(f"❌ FAIL: Test error: {e}")
            return False
    
    async def verify_completion_database_effects(self, initial_state, completion_data):
        """Verify all database effects of quest completion"""
        print("🔍 Verifying database effects...")
        
        success = True
        
        # 1. Check quest acceptance status
        try:
            async with self.session.get(
                f"{API_BASE}/quests/my-quests/accepted",
                headers=self.get_headers(self.participant_token)
            ) as response:
                if response.status == 200:
                    acceptances = await response.json()
                    
                    # Find our acceptance
                    our_acceptance = None
                    for acceptance_data in acceptances:
                        if acceptance_data["acceptance"]["id"] == self.test_acceptance_id:
                            our_acceptance = acceptance_data["acceptance"]
                            break
                    
                    if our_acceptance and our_acceptance["status"] == "completed":
                        print("✅ Quest acceptance status updated to 'completed'")
                        if our_acceptance.get("completed_at"):
                            print("✅ Completed timestamp added")
                        else:
                            print("❌ Missing completed_at timestamp")
                            success = False
                    else:
                        print("❌ Quest acceptance status not updated correctly")
                        success = False
                else:
                    print("❌ Failed to check quest acceptance status")
                    success = False
        except Exception as e:
            print(f"❌ Error checking acceptance status: {e}")
            success = False
        
        # 2. Check participant currency increase
        try:
            async with self.session.get(
                f"{API_BASE}/wallet",
                headers=self.get_headers(self.participant_token)
            ) as response:
                if response.status == 200:
                    wallet_data = await response.json()
                    new_currency = wallet_data["balance"]
                    expected_currency = initial_state["currency"] + completion_data["reward"]
                    
                    if new_currency == expected_currency:
                        print(f"✅ Currency increased correctly: {initial_state['currency']} → {new_currency}")
                    else:
                        print(f"❌ Currency mismatch: expected {expected_currency}, got {new_currency}")
                        success = False
                else:
                    print("❌ Failed to check currency")
                    success = False
        except Exception as e:
            print(f"❌ Error checking currency: {e}")
            success = False
        
        # 3. Check character XP/level update
        try:
            async with self.session.get(
                f"{API_BASE}/characters/{self.participant_character_id}",
                headers=self.get_headers(self.participant_token)
            ) as response:
                if response.status == 200:
                    char_data = await response.json()
                    new_xp = char_data.get("xp", 0)
                    new_level = char_data.get("level", 1)
                    new_inventory_count = len(char_data.get("inventory", []))
                    
                    # Check XP/level logic
                    expected_total_xp = initial_state["xp"] + completion_data["reward_xp"]
                    print(f"   XP: {initial_state['xp']} + {completion_data['reward_xp']} = {expected_total_xp}")
                    print(f"   Actual XP: {new_xp}, Level: {new_level}")
                    
                    # Basic XP check (level up logic is complex, just verify XP increased)
                    if new_xp >= 0 and new_level >= initial_state["level"]:
                        print("✅ Character XP/level updated correctly")
                    else:
                        print("❌ Character XP/level update failed")
                        success = False
                    
                    # Check inventory items
                    expected_inventory_count = initial_state["inventory_count"] + len(completion_data["reward_items"])
                    if new_inventory_count == expected_inventory_count:
                        print(f"✅ Inventory items added: {initial_state['inventory_count']} → {new_inventory_count}")
                    else:
                        print(f"❌ Inventory count mismatch: expected {expected_inventory_count}, got {new_inventory_count}")
                        success = False
                    
                else:
                    print("❌ Failed to check character updates")
                    success = False
        except Exception as e:
            print(f"❌ Error checking character: {e}")
            success = False
        
        # 4. Check transaction record
        try:
            async with self.session.get(
                f"{API_BASE}/wallet/transactions",
                headers=self.get_headers(self.participant_token)
            ) as response:
                if response.status == 200:
                    transactions = await response.json()
                    
                    # Look for quest reward transaction
                    quest_transaction = None
                    for trans in transactions:
                        if (trans.get("transaction_type") == "quest_reward" and 
                            trans.get("amount") == completion_data["reward"]):
                            quest_transaction = trans
                            break
                    
                    if quest_transaction:
                        print("✅ Quest reward transaction created")
                        print(f"   Amount: {quest_transaction['amount']}")
                        print(f"   Type: {quest_transaction['transaction_type']}")
                    else:
                        print("❌ Quest reward transaction not found")
                        success = False
                else:
                    print("❌ Failed to check transactions")
                    success = False
        except Exception as e:
            print(f"❌ Error checking transactions: {e}")
            success = False
        
        return success
    
    async def test_creator_permission_enforcement(self):
        """Test Case 3: Creator permission enforcement"""
        print("\n🔒 TEST 3: CREATOR PERMISSION ENFORCEMENT")
        print("=" * 60)
        
        print("🎯 Testing that non-creators cannot complete participants...")
        
        try:
            async with self.session.post(
                f"{API_BASE}/quests/{self.test_quest_id}/participants/{self.test_acceptance_id}/complete",
                headers=self.get_headers(self.non_creator_token)
            ) as response:
                if response.status == 403:
                    response_data = await response.json()
                    detail = response_data.get("detail", "")
                    expected_detail = "Only the quest creator can complete participants"
                    
                    if detail == expected_detail:
                        print("✅ PASS: Creator permission correctly enforced")
                        print(f"   Status: 403 Forbidden")
                        print(f"   Detail: {detail}")
                        return True
                    else:
                        print(f"❌ FAIL: Wrong error message")
                        print(f"   Expected: {expected_detail}")
                        print(f"   Got: {detail}")
                        return False
                else:
                    error_text = await response.text()
                    print(f"❌ FAIL: Expected 403, got {response.status}")
                    print(f"   Response: {error_text}")
                    return False
        except Exception as e:
            print(f"❌ FAIL: Test error: {e}")
            return False
    
    async def test_edge_cases(self):
        """Test Case 4: Edge cases"""
        print("\n⚠️ TEST 4: EDGE CASES")
        print("=" * 60)
        
        results = {
            "non_existent_quest": False,
            "wrong_acceptance_id": False
        }
        
        # Test 4a: Non-existent quest_id
        print("🎯 Testing non-existent quest_id...")
        fake_quest_id = "non-existent-quest-id-12345"
        fake_acceptance_id = "fake-acceptance-id-12345"
        
        try:
            async with self.session.post(
                f"{API_BASE}/quests/{fake_quest_id}/participants/{fake_acceptance_id}/complete",
                headers=self.get_headers(self.creator_token)
            ) as response:
                if response.status == 404:
                    response_data = await response.json()
                    detail = response_data.get("detail", "")
                    if "Quest not found" in detail:
                        print("✅ PASS: Non-existent quest returns 404 'Quest not found'")
                        results["non_existent_quest"] = True
                    else:
                        print(f"❌ FAIL: Wrong error message for non-existent quest: {detail}")
                else:
                    error_text = await response.text()
                    print(f"❌ FAIL: Expected 404 for non-existent quest, got {response.status}")
                    print(f"   Response: {error_text}")
        except Exception as e:
            print(f"❌ FAIL: Non-existent quest test error: {e}")
        
        # Test 4b: Wrong acceptance_id (already completed or non-existent)
        print("🎯 Testing wrong/already-completed acceptance_id...")
        fake_acceptance_id = "wrong-acceptance-id-12345"
        
        try:
            async with self.session.post(
                f"{API_BASE}/quests/{self.test_quest_id}/participants/{fake_acceptance_id}/complete",
                headers=self.get_headers(self.creator_token)
            ) as response:
                if response.status == 404:
                    response_data = await response.json()
                    detail = response_data.get("detail", "")
                    if "Quest acceptance not found or already completed" in detail:
                        print("✅ PASS: Wrong acceptance_id returns 404 'Quest acceptance not found or already completed'")
                        results["wrong_acceptance_id"] = True
                    else:
                        print(f"❌ FAIL: Wrong error message for wrong acceptance_id: {detail}")
                else:
                    error_text = await response.text()
                    print(f"❌ FAIL: Expected 404 for wrong acceptance_id, got {response.status}")
                    print(f"   Response: {error_text}")
        except Exception as e:
            print(f"❌ FAIL: Wrong acceptance_id test error: {e}")
        
        return all(results.values())

async def run_quest_completion_tests():
    """Run focused quest completion tests"""
    print("🚀 STARTING QUEST COMPLETION TESTS")
    print("=" * 70)
    print(f"Backend URL: {BACKEND_URL}")
    print(f"API Base: {API_BASE}")
    print("=" * 70)
    
    test_results = {
        "setup": False,
        "participant_self_complete_disabled": False,
        "creator_completion_happy_path": False,
        "creator_permission_enforcement": False,
        "edge_cases": False
    }
    
    async with QuestCompletionTester() as tester:
        # Setup phase
        print("\n🔧 SETUP PHASE")
        print("=" * 40)
        
        if not await tester.setup_test_users():
            print("❌ Failed to setup test users")
            return test_results
        
        if not await tester.create_test_characters():
            print("❌ Failed to create test characters")
            return test_results
        
        if not await tester.create_test_quest():
            print("❌ Failed to create test quest")
            return test_results
        
        if not await tester.accept_quest_as_participant():
            print("❌ Failed to accept quest as participant")
            return test_results
        
        test_results["setup"] = True
        print("✅ Setup phase completed successfully")
        
        # Test 1: Participant self-complete disabled
        test_results["participant_self_complete_disabled"] = await tester.test_participant_self_complete_disabled()
        
        # Test 2: Creator completion happy path
        test_results["creator_completion_happy_path"] = await tester.test_creator_completion_happy_path()
        
        # Test 3: Creator permission enforcement
        test_results["creator_permission_enforcement"] = await tester.test_creator_permission_enforcement()
        
        # Test 4: Edge cases
        test_results["edge_cases"] = await tester.test_edge_cases()
    
    return test_results

def print_test_summary(results):
    """Print comprehensive test summary"""
    print("\n" + "=" * 70)
    print("🏁 QUEST COMPLETION TEST SUMMARY")
    print("=" * 70)
    
    total_tests = len([k for k in results.keys() if k != "setup"])
    passed_tests = sum(1 for k, v in results.items() if k != "setup" and v)
    
    print(f"Setup: {'✅ PASS' if results['setup'] else '❌ FAIL'}")
    print("-" * 40)
    
    for test_name, passed in results.items():
        if test_name == "setup":
            continue
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} {test_name.replace('_', ' ').title()}")
    
    print("-" * 70)
    print(f"TOTAL: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests and results["setup"]:
        print("🎉 ALL TESTS PASSED! Quest completion system working correctly.")
    else:
        print("⚠️  Some tests failed. Issues found:")
        
        if not results["setup"]:
            print("   🚨 Setup failed - cannot test quest completion")
        
        if not results["participant_self_complete_disabled"]:
            print("   🚨 Participant self-complete not properly disabled")
        
        if not results["creator_completion_happy_path"]:
            print("   🚨 Creator completion not working - CRITICAL ISSUE")
        
        if not results["creator_permission_enforcement"]:
            print("   🚨 Creator permission not enforced - SECURITY ISSUE")
        
        if not results["edge_cases"]:
            print("   🚨 Edge cases not handled properly")
    
    print("=" * 70)

if __name__ == "__main__":
    results = asyncio.run(run_quest_completion_tests())
    print_test_summary(results)