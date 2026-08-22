#!/usr/bin/env python3
"""
Location Management Testing for Continents of Delarom
Focus: Dynamic RP location management changes validation

Testing Requirements from Review Request:
1) Permissions - admin/moderator can create/update/toggle locations, members get 403
2) Location data contract - verify LocationArea model response structure
3) Toggle & update functionality - test active status and field updates
4) Location RP still works - verify roleplay endpoints function after changes
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

class LocationManagementTester:
    def __init__(self):
        self.session = None
        self.admin_token = None
        self.moderator_token = None
        self.member_token = None
        self.admin_user_id = None
        self.moderator_user_id = None
        self.member_user_id = None
        self.test_location_id = None
        self.test_character_id = None
        
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
        """Setup admin, moderator, and member users for testing"""
        print("🔐 Setting up test users...")
        
        # Login as admin (existing user)
        admin_credentials = {
            "email": "craftnn1222@gmail.com",
            "password": "admin123"
        }
        
        try:
            async with self.session.post(
                f"{API_BASE}/auth/login",
                json=admin_credentials,
                headers=self.get_headers(include_auth=False)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    self.admin_token = data["access_token"]
                    self.admin_user_id = data["user"]["id"]
                    print(f"✅ Admin login successful: {data['user']['username']} (role: {data['user']['role']})")
                else:
                    error_text = await response.text()
                    print(f"❌ Admin login failed: {response.status} - {error_text}")
                    return False
        except Exception as e:
            print(f"❌ Admin login error: {e}")
            return False
        
        # Create/login moderator user
        moderator_data = {
            "username": "location_moderator",
            "email": "location.moderator@delarom.com",
            "password": "ModeratorTest123!",
            "application_text": "Testing moderator permissions for location management"
        }
        
        # Try to register moderator
        try:
            async with self.session.post(
                f"{API_BASE}/auth/register",
                json=moderator_data,
                headers=self.get_headers(include_auth=False)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    self.moderator_user_id = data["user"]["id"]
                    print(f"✅ Moderator user registered: {data['user']['username']}")
                    
                    # Approve the moderator application
                    await self.approve_user(self.moderator_user_id)
                    
                    # Promote to moderator
                    await self.promote_to_moderator(self.moderator_user_id)
                    
                elif response.status == 400:
                    print("⚠️  Moderator user already exists, attempting login...")
                    # User exists, try login
                    async with self.session.post(
                        f"{API_BASE}/auth/login",
                        json={"email": moderator_data["email"], "password": moderator_data["password"]},
                        headers=self.get_headers(include_auth=False)
                    ) as login_response:
                        if login_response.status == 200:
                            data = await login_response.json()
                            self.moderator_token = data["access_token"]
                            self.moderator_user_id = data["user"]["id"]
                            print(f"✅ Moderator login successful: {data['user']['username']} (role: {data['user']['role']})")
                        else:
                            print("❌ Moderator login failed")
                            return False
                else:
                    error_text = await response.text()
                    print(f"❌ Moderator registration failed: {response.status} - {error_text}")
                    return False
        except Exception as e:
            print(f"❌ Moderator setup error: {e}")
            return False
        
        # If we registered a new moderator, login after promotion
        if not self.moderator_token:
            try:
                async with self.session.post(
                    f"{API_BASE}/auth/login",
                    json={"email": moderator_data["email"], "password": moderator_data["password"]},
                    headers=self.get_headers(include_auth=False)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        self.moderator_token = data["access_token"]
                        print(f"✅ Moderator login after promotion: {data['user']['username']} (role: {data['user']['role']})")
                    else:
                        print("❌ Moderator login after promotion failed")
                        return False
            except Exception as e:
                print(f"❌ Moderator login error: {e}")
                return False
        
        # Create/login member user
        member_data = {
            "username": "location_member",
            "email": "location.member@delarom.com",
            "password": "MemberTest123!",
            "application_text": "Testing member permissions for location management"
        }
        
        try:
            async with self.session.post(
                f"{API_BASE}/auth/register",
                json=member_data,
                headers=self.get_headers(include_auth=False)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    self.member_user_id = data["user"]["id"]
                    print(f"✅ Member user registered: {data['user']['username']}")
                    
                    # Approve the member application
                    await self.approve_user(self.member_user_id)
                    
                elif response.status == 400:
                    print("⚠️  Member user already exists, attempting login...")
                else:
                    error_text = await response.text()
                    print(f"❌ Member registration failed: {response.status} - {error_text}")
                    return False
        except Exception as e:
            print(f"❌ Member setup error: {e}")
            return False
        
        # Login as member
        try:
            async with self.session.post(
                f"{API_BASE}/auth/login",
                json={"email": member_data["email"], "password": member_data["password"]},
                headers=self.get_headers(include_auth=False)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    self.member_token = data["access_token"]
                    self.member_user_id = data["user"]["id"]
                    print(f"✅ Member login successful: {data['user']['username']} (role: {data['user']['role']})")
                else:
                    error_text = await response.text()
                    print(f"❌ Member login failed: {response.status} - {error_text}")
                    return False
        except Exception as e:
            print(f"❌ Member login error: {e}")
            return False
        
        return True
    
    async def approve_user(self, user_id):
        """Approve a pending user application"""
        try:
            async with self.session.post(
                f"{API_BASE}/admin/applications/{user_id}/approve",
                headers=self.get_headers(self.admin_token)
            ) as response:
                if response.status == 200:
                    print(f"✅ User {user_id} approved")
                    return True
                else:
                    print(f"⚠️  User approval failed or user already approved")
                    return False
        except Exception as e:
            print(f"⚠️  User approval error: {e}")
            return False
    
    async def promote_to_moderator(self, user_id):
        """Promote user to moderator role"""
        try:
            async with self.session.post(
                f"{API_BASE}/admin/users/{user_id}/promote-moderator",
                headers=self.get_headers(self.admin_token)
            ) as response:
                if response.status == 200:
                    print(f"✅ User {user_id} promoted to moderator")
                    return True
                else:
                    print(f"⚠️  User promotion failed or user already moderator")
                    return False
        except Exception as e:
            print(f"⚠️  User promotion error: {e}")
            return False
    
    async def create_test_character(self):
        """Create a character for RP testing"""
        print("🧙 Creating test character for RP testing...")
        
        character_data = {
            "name": "Tavern Visitor",
            "race": "Human",
            "character_class": "Wanderer",
            "backstory": "A curious traveler who enjoys visiting taverns and meeting new people.",
            "powers": "Keen observation and storytelling abilities",
            "appearance": "A friendly-looking person with travel-worn clothes and a warm smile.",
            "nation": "Ammeonon",
            "strength": 10,
            "magic": 10,
            "agility": 12,
            "endurance": 11,
            "charisma": 15,
            "luck": 12
        }
        
        try:
            async with self.session.post(
                f"{API_BASE}/characters",
                json=character_data,
                headers=self.get_headers(self.member_token)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    self.test_character_id = data["id"]
                    print(f"✅ Character created: {data['name']} (ID: {self.test_character_id})")
                    return True
                else:
                    error_text = await response.text()
                    print(f"❌ Character creation failed: {response.status} - {error_text}")
                    return False
        except Exception as e:
            print(f"❌ Character creation error: {e}")
            return False
    
    async def test_permissions(self):
        """Test 1: Permissions - admin/moderator can manage locations, members get 403"""
        print("\n🔒 TESTING PERMISSIONS")
        print("=" * 60)
        
        results = {
            "admin_create_location": False,
            "moderator_create_location": False,
            "member_create_location_denied": False,
            "admin_update_location": False,
            "moderator_update_location": False,
            "member_update_location_denied": False,
            "admin_toggle_location": False,
            "moderator_toggle_location": False,
            "member_toggle_location_denied": False
        }
        
        # Test location data as specified in review request
        location_data = {
            "nation": "ammeonon",
            "slug": "dragon-lament-tavern",
            "name": "Dragon's Lament Tavern",
            "location_type": "Tavern",
            "description": "A warm, smoky tavern in Wymroost where sailors and adventurers mingle.",
            "is_active": True,
            "is_rp_enabled": True
        }
        
        # 1. Test admin can create location
        print("\n1️⃣ Testing admin can create location...")
        try:
            async with self.session.post(
                f"{API_BASE}/admin/locations",
                json=location_data,
                headers=self.get_headers(self.admin_token)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    self.test_location_id = data["id"]
                    print(f"✅ Admin created location successfully: {data['name']}")
                    print(f"   Location ID: {self.test_location_id}")
                    results["admin_create_location"] = True
                else:
                    error_text = await response.text()
                    print(f"❌ Admin create location failed: {response.status} - {error_text}")
        except Exception as e:
            print(f"❌ Admin create location error: {e}")
        
        # 2. Test moderator can create location (create another one)
        print("\n2️⃣ Testing moderator can create location...")
        moderator_location_data = {
            "nation": "ammeonon",
            "slug": "silver-moon-inn",
            "name": "Silver Moon Inn",
            "location_type": "Inn",
            "description": "A cozy inn with comfortable rooms and hearty meals.",
            "is_active": True,
            "is_rp_enabled": True
        }
        
        try:
            async with self.session.post(
                f"{API_BASE}/admin/locations",
                json=moderator_location_data,
                headers=self.get_headers(self.moderator_token)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Moderator created location successfully: {data['name']}")
                    results["moderator_create_location"] = True
                else:
                    error_text = await response.text()
                    print(f"❌ Moderator create location failed: {response.status} - {error_text}")
        except Exception as e:
            print(f"❌ Moderator create location error: {e}")
        
        # 3. Test member cannot create location (should get 403)
        print("\n3️⃣ Testing member cannot create location (should get 403)...")
        member_location_data = {
            "nation": "ammeonon",
            "slug": "forbidden-location",
            "name": "Forbidden Location",
            "location_type": "Test",
            "description": "This should not be created by a member.",
            "is_active": True,
            "is_rp_enabled": True
        }
        
        try:
            async with self.session.post(
                f"{API_BASE}/admin/locations",
                json=member_location_data,
                headers=self.get_headers(self.member_token)
            ) as response:
                if response.status == 403:
                    print("✅ Member correctly denied access (403 Forbidden)")
                    results["member_create_location_denied"] = True
                else:
                    error_text = await response.text()
                    print(f"❌ Member should get 403, got {response.status}: {error_text}")
        except Exception as e:
            print(f"❌ Member create location test error: {e}")
        
        if not self.test_location_id:
            print("❌ Cannot continue with update/toggle tests - no location created")
            return results
        
        # 4. Test admin can update location
        print("\n4️⃣ Testing admin can update location...")
        update_data = {
            "name": "Dragon's Lament Tavern (Updated)",
            "location_type": "Tavern & Inn",
            "description": "A warm, smoky tavern and inn in Wymroost where sailors and adventurers mingle and rest."
        }
        
        try:
            async with self.session.put(
                f"{API_BASE}/admin/locations/{self.test_location_id}",
                json=update_data,
                headers=self.get_headers(self.admin_token)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Admin updated location successfully: {data['name']}")
                    results["admin_update_location"] = True
                else:
                    error_text = await response.text()
                    print(f"❌ Admin update location failed: {response.status} - {error_text}")
        except Exception as e:
            print(f"❌ Admin update location error: {e}")
        
        # 5. Test moderator can update location
        print("\n5️⃣ Testing moderator can update location...")
        moderator_update_data = {
            "description": "A warm, smoky tavern and inn in Wymroost where sailors and adventurers mingle, rest, and share tales of their journeys."
        }
        
        try:
            async with self.session.put(
                f"{API_BASE}/admin/locations/{self.test_location_id}",
                json=moderator_update_data,
                headers=self.get_headers(self.moderator_token)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Moderator updated location successfully")
                    results["moderator_update_location"] = True
                else:
                    error_text = await response.text()
                    print(f"❌ Moderator update location failed: {response.status} - {error_text}")
        except Exception as e:
            print(f"❌ Moderator update location error: {e}")
        
        # 6. Test member cannot update location (should get 403)
        print("\n6️⃣ Testing member cannot update location (should get 403)...")
        try:
            async with self.session.put(
                f"{API_BASE}/admin/locations/{self.test_location_id}",
                json={"description": "This should not work"},
                headers=self.get_headers(self.member_token)
            ) as response:
                if response.status == 403:
                    print("✅ Member correctly denied access (403 Forbidden)")
                    results["member_update_location_denied"] = True
                else:
                    error_text = await response.text()
                    print(f"❌ Member should get 403, got {response.status}: {error_text}")
        except Exception as e:
            print(f"❌ Member update location test error: {e}")
        
        # 7. Test admin can toggle location active status
        print("\n7️⃣ Testing admin can toggle location active status...")
        try:
            async with self.session.post(
                f"{API_BASE}/admin/locations/{self.test_location_id}/toggle-active",
                headers=self.get_headers(self.admin_token)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Admin toggled location successfully: {data.get('message', 'Success')}")
                    results["admin_toggle_location"] = True
                else:
                    error_text = await response.text()
                    print(f"❌ Admin toggle location failed: {response.status} - {error_text}")
        except Exception as e:
            print(f"❌ Admin toggle location error: {e}")
        
        # 8. Test moderator can toggle location active status
        print("\n8️⃣ Testing moderator can toggle location active status...")
        try:
            async with self.session.post(
                f"{API_BASE}/admin/locations/{self.test_location_id}/toggle-active",
                headers=self.get_headers(self.moderator_token)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Moderator toggled location successfully: {data.get('message', 'Success')}")
                    results["moderator_toggle_location"] = True
                else:
                    error_text = await response.text()
                    print(f"❌ Moderator toggle location failed: {response.status} - {error_text}")
        except Exception as e:
            print(f"❌ Moderator toggle location error: {e}")
        
        # 9. Test member cannot toggle location (should get 403)
        print("\n9️⃣ Testing member cannot toggle location (should get 403)...")
        try:
            async with self.session.post(
                f"{API_BASE}/admin/locations/{self.test_location_id}/toggle-active",
                headers=self.get_headers(self.member_token)
            ) as response:
                if response.status == 403:
                    print("✅ Member correctly denied access (403 Forbidden)")
                    results["member_toggle_location_denied"] = True
                else:
                    error_text = await response.text()
                    print(f"❌ Member should get 403, got {response.status}: {error_text}")
        except Exception as e:
            print(f"❌ Member toggle location test error: {e}")
        
        return results
    
    async def test_location_data_contract(self):
        """Test 2: Location data contract - verify LocationArea model response"""
        print("\n📋 TESTING LOCATION DATA CONTRACT")
        print("=" * 60)
        
        results = {
            "location_response_structure": False,
            "no_mongo_id": False,
            "get_locations_includes_new": False,
            "get_locations_by_nation": False,
            "get_location_meta": False
        }
        
        if not self.test_location_id:
            print("❌ No test location available for data contract testing")
            return results
        
        # 1. Verify the created location has correct response structure
        print("\n1️⃣ Verifying location response structure...")
        try:
            async with self.session.get(
                f"{API_BASE}/locations",
                headers=self.get_headers(self.admin_token, include_auth=False)
            ) as response:
                if response.status == 200:
                    locations = await response.json()
                    
                    # Find our test location
                    test_location = None
                    for loc in locations:
                        if loc.get("id") == self.test_location_id:
                            test_location = loc
                            break
                    
                    if test_location:
                        print(f"✅ Found test location in response")
                        
                        # Verify LocationArea model fields
                        expected_fields = ["id", "nation", "slug", "name", "location_type", "description", "is_active", "is_rp_enabled", "created_at"]
                        actual_fields = list(test_location.keys())
                        
                        print(f"   Expected fields: {expected_fields}")
                        print(f"   Actual fields: {actual_fields}")
                        
                        missing_fields = [f for f in expected_fields if f not in actual_fields]
                        extra_fields = [f for f in actual_fields if f not in expected_fields and f != "_id"]
                        
                        if not missing_fields:
                            print("✅ All expected fields present")
                            
                            # Check for Mongo _id (should not be present)
                            if "_id" not in actual_fields:
                                print("✅ No Mongo _id field in response")
                                results["no_mongo_id"] = True
                            else:
                                print("❌ Mongo _id field present in response")
                            
                            # Verify field values match what we created
                            if (test_location.get("nation") == "ammeonon" and
                                test_location.get("slug") == "dragon-lament-tavern" and
                                "Dragon's Lament Tavern" in test_location.get("name", "") and
                                test_location.get("location_type") in ["Tavern", "Tavern & Inn"] and
                                "warm, smoky tavern" in test_location.get("description", "") and
                                isinstance(test_location.get("is_active"), bool) and
                                isinstance(test_location.get("is_rp_enabled"), bool)):
                                print("✅ Field values match expected data")
                                results["location_response_structure"] = True
                            else:
                                print("❌ Field values don't match expected data")
                                print(f"   Nation: {test_location.get('nation')}")
                                print(f"   Slug: {test_location.get('slug')}")
                                print(f"   Name: {test_location.get('name')}")
                                print(f"   Type: {test_location.get('location_type')}")
                                print(f"   Active: {test_location.get('is_active')}")
                                print(f"   RP Enabled: {test_location.get('is_rp_enabled')}")
                        else:
                            print(f"❌ Missing fields: {missing_fields}")
                        
                        if extra_fields:
                            print(f"ℹ️  Extra fields: {extra_fields}")
                    else:
                        print("❌ Test location not found in locations response")
                else:
                    error_text = await response.text()
                    print(f"❌ Get locations failed: {response.status} - {error_text}")
        except Exception as e:
            print(f"❌ Location response structure test error: {e}")
        
        # 2. Test GET /api/locations includes the new location
        print("\n2️⃣ Testing GET /api/locations includes new location...")
        try:
            async with self.session.get(
                f"{API_BASE}/locations",
                headers=self.get_headers(include_auth=False)
            ) as response:
                if response.status == 200:
                    locations = await response.json()
                    location_ids = [loc.get("id") for loc in locations]
                    
                    if self.test_location_id in location_ids:
                        print(f"✅ New location appears in GET /api/locations")
                        results["get_locations_includes_new"] = True
                    else:
                        print(f"❌ New location not found in GET /api/locations")
                        print(f"   Looking for ID: {self.test_location_id}")
                        print(f"   Found IDs: {location_ids[:5]}...")  # Show first 5
                else:
                    error_text = await response.text()
                    print(f"❌ GET /api/locations failed: {response.status} - {error_text}")
        except Exception as e:
            print(f"❌ GET locations test error: {e}")
        
        # 3. Test GET /api/locations/ammeonon includes the new location
        print("\n3️⃣ Testing GET /api/locations/ammeonon includes new location...")
        try:
            async with self.session.get(
                f"{API_BASE}/locations/ammeonon",
                headers=self.get_headers(include_auth=False)
            ) as response:
                if response.status == 200:
                    locations = await response.json()
                    location_ids = [loc.get("id") for loc in locations]
                    
                    if self.test_location_id in location_ids:
                        print(f"✅ New location appears in GET /api/locations/ammeonon")
                        results["get_locations_by_nation"] = True
                    else:
                        print(f"❌ New location not found in GET /api/locations/ammeonon")
                else:
                    error_text = await response.text()
                    print(f"❌ GET /api/locations/ammeonon failed: {response.status} - {error_text}")
        except Exception as e:
            print(f"❌ GET locations by nation test error: {e}")
        
        # 4. Test GET /api/locations/ammeonon/dragon-lament-tavern/meta
        print("\n4️⃣ Testing GET /api/locations/ammeonon/dragon-lament-tavern/meta...")
        try:
            async with self.session.get(
                f"{API_BASE}/locations/ammeonon/dragon-lament-tavern/meta",
                headers=self.get_headers(include_auth=False)
            ) as response:
                if response.status == 200:
                    meta_data = await response.json()
                    print(f"✅ Location metadata retrieved successfully")
                    print(f"   Metadata keys: {list(meta_data.keys())}")
                    
                    # Verify metadata matches our location
                    if (meta_data.get("nation") == "ammeonon" and
                        meta_data.get("slug") == "dragon-lament-tavern"):
                        print("✅ Metadata matches location data")
                        results["get_location_meta"] = True
                    else:
                        print("❌ Metadata doesn't match location data")
                        print(f"   Meta nation: {meta_data.get('nation')}")
                        print(f"   Meta slug: {meta_data.get('slug')}")
                else:
                    error_text = await response.text()
                    print(f"❌ GET location meta failed: {response.status} - {error_text}")
        except Exception as e:
            print(f"❌ GET location meta test error: {e}")
        
        return results
    
    async def test_toggle_and_update(self):
        """Test 3: Toggle & update functionality"""
        print("\n🔄 TESTING TOGGLE & UPDATE FUNCTIONALITY")
        print("=" * 60)
        
        results = {
            "toggle_active_changes_status": False,
            "toggle_reflected_in_get": False,
            "update_name_persists": False,
            "update_type_persists": False,
            "update_description_persists": False
        }
        
        if not self.test_location_id:
            print("❌ No test location available for toggle/update testing")
            return results
        
        # 1. Get current active status
        print("\n1️⃣ Getting current location status...")
        current_active_status = None
        try:
            async with self.session.get(
                f"{API_BASE}/locations",
                headers=self.get_headers(include_auth=False)
            ) as response:
                if response.status == 200:
                    locations = await response.json()
                    for loc in locations:
                        if loc.get("id") == self.test_location_id:
                            current_active_status = loc.get("is_active")
                            print(f"✅ Current active status: {current_active_status}")
                            break
        except Exception as e:
            print(f"❌ Error getting current status: {e}")
        
        if current_active_status is None:
            print("❌ Could not determine current active status")
            return results
        
        # 2. Toggle active status
        print("\n2️⃣ Toggling active status...")
        try:
            async with self.session.post(
                f"{API_BASE}/admin/locations/{self.test_location_id}/toggle-active",
                headers=self.get_headers(self.admin_token)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    new_status = data.get("is_active")
                    print(f"✅ Toggle successful - new status: {new_status}")
                    
                    if new_status != current_active_status:
                        print("✅ Active status changed as expected")
                        results["toggle_active_changes_status"] = True
                    else:
                        print("❌ Active status did not change")
                else:
                    error_text = await response.text()
                    print(f"❌ Toggle failed: {response.status} - {error_text}")
        except Exception as e:
            print(f"❌ Toggle error: {e}")
        
        # 3. Verify toggle is reflected in GET calls
        print("\n3️⃣ Verifying toggle is reflected in GET calls...")
        try:
            async with self.session.get(
                f"{API_BASE}/locations",
                headers=self.get_headers(include_auth=False)
            ) as response:
                if response.status == 200:
                    locations = await response.json()
                    for loc in locations:
                        if loc.get("id") == self.test_location_id:
                            updated_status = loc.get("is_active")
                            print(f"✅ Status in GET response: {updated_status}")
                            
                            if updated_status != current_active_status:
                                print("✅ Toggle reflected in GET calls")
                                results["toggle_reflected_in_get"] = True
                            else:
                                print("❌ Toggle not reflected in GET calls")
                            break
        except Exception as e:
            print(f"❌ GET verification error: {e}")
        
        # 4. Test PUT update with name, location_type, and description changes
        print("\n4️⃣ Testing PUT update with field changes...")
        update_data = {
            "name": "Dragon's Lament Tavern (Final Update)",
            "location_type": "Legendary Tavern",
            "description": "The most famous tavern in all of Ammeonon, where legendary heroes gather to share tales and plan epic adventures."
        }
        
        try:
            async with self.session.put(
                f"{API_BASE}/admin/locations/{self.test_location_id}",
                json=update_data,
                headers=self.get_headers(self.admin_token)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Update successful")
                    
                    # Verify each field was updated
                    if data.get("name") == update_data["name"]:
                        print("✅ Name update persisted")
                        results["update_name_persists"] = True
                    else:
                        print(f"❌ Name not updated: expected '{update_data['name']}', got '{data.get('name')}'")
                    
                    if data.get("location_type") == update_data["location_type"]:
                        print("✅ Location type update persisted")
                        results["update_type_persists"] = True
                    else:
                        print(f"❌ Location type not updated: expected '{update_data['location_type']}', got '{data.get('location_type')}'")
                    
                    if data.get("description") == update_data["description"]:
                        print("✅ Description update persisted")
                        results["update_description_persists"] = True
                    else:
                        print(f"❌ Description not updated")
                        print(f"   Expected: {update_data['description']}")
                        print(f"   Got: {data.get('description')}")
                else:
                    error_text = await response.text()
                    print(f"❌ Update failed: {response.status} - {error_text}")
        except Exception as e:
            print(f"❌ Update error: {e}")
        
        return results
    
    async def test_location_rp_still_works(self):
        """Test 4: Location RP still works after changes"""
        print("\n🎭 TESTING LOCATION RP FUNCTIONALITY")
        print("=" * 60)
        
        results = {
            "rp_post_successful": False,
            "rp_get_includes_entry": False,
            "ai_response_present": False
        }
        
        if not self.test_character_id:
            print("❌ No test character available for RP testing")
            return results
        
        # 1. Test POST /api/locations/ammeonon/dragon-lament-tavern/roleplay
        print("\n1️⃣ Testing POST roleplay action...")
        rp_data = {
            "action_text": "I push open the heavy wooden door of the Dragon's Lament Tavern and step inside, looking around at the warm, smoky atmosphere. The scent of ale and roasted meat fills my nostrils as I approach the bar, nodding to the other patrons."
        }
        
        try:
            async with self.session.post(
                f"{API_BASE}/locations/ammeonon/dragon-lament-tavern/roleplay",
                json=rp_data,
                headers=self.get_headers(self.member_token)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    rp_id = data.get("rp_id")
                    ai_response = data.get("ai_response")
                    
                    print(f"✅ RP action posted successfully")
                    print(f"   RP ID: {rp_id}")
                    print(f"   AI Response length: {len(ai_response) if ai_response else 0} characters")
                    
                    if ai_response and len(ai_response) > 10:
                        print("✅ AI response generated")
                        print(f"   AI Response preview: {ai_response[:100]}...")
                        results["ai_response_present"] = True
                        results["rp_post_successful"] = True
                    else:
                        print("❌ No AI response or response too short")
                        results["rp_post_successful"] = True  # Post worked, just no AI
                else:
                    error_text = await response.text()
                    print(f"❌ RP post failed: {response.status} - {error_text}")
        except Exception as e:
            print(f"❌ RP post error: {e}")
        
        # 2. Test GET /api/locations/ammeonon/dragon-lament-tavern/roleplay
        print("\n2️⃣ Testing GET roleplay history...")
        try:
            async with self.session.get(
                f"{API_BASE}/locations/ammeonon/dragon-lament-tavern/roleplay",
                headers=self.get_headers(self.member_token, include_auth=False)
            ) as response:
                if response.status == 200:
                    rp_history = await response.json()
                    print(f"✅ RP history retrieved successfully")
                    print(f"   Number of RP entries: {len(rp_history)}")
                    
                    # Look for our entry
                    our_entry = None
                    for entry in rp_history:
                        if (entry.get("character_id") == self.test_character_id and
                            "Dragon's Lament Tavern" in entry.get("action_text", "")):
                            our_entry = entry
                            break
                    
                    if our_entry:
                        print("✅ Our RP entry found in history")
                        print(f"   Character: {our_entry.get('character_name')}")
                        print(f"   Action: {our_entry.get('action_text')[:50]}...")
                        if our_entry.get('ai_response'):
                            print(f"   AI Response: {our_entry.get('ai_response')[:50]}...")
                        results["rp_get_includes_entry"] = True
                    else:
                        print("❌ Our RP entry not found in history")
                        if rp_history:
                            print(f"   Sample entry: {rp_history[0].get('character_name')} - {rp_history[0].get('action_text')[:30]}...")
                else:
                    error_text = await response.text()
                    print(f"❌ RP history retrieval failed: {response.status} - {error_text}")
        except Exception as e:
            print(f"❌ RP history error: {e}")
        
        return results

async def run_location_management_tests():
    """Run comprehensive location management tests"""
    print("🚀 STARTING LOCATION MANAGEMENT TESTS")
    print("=" * 80)
    print(f"Backend URL: {BACKEND_URL}")
    print(f"API Base: {API_BASE}")
    print("=" * 80)
    
    all_results = {
        "setup": False,
        "permissions": {},
        "data_contract": {},
        "toggle_update": {},
        "location_rp": {}
    }
    
    async with LocationManagementTester() as tester:
        # Setup test users
        print("\n🔧 SETUP PHASE")
        print("=" * 60)
        setup_success = await tester.setup_test_users()
        all_results["setup"] = setup_success
        
        if not setup_success:
            print("❌ Setup failed - cannot continue with tests")
            return all_results
        
        # Create test character for RP testing
        await tester.create_test_character()
        
        # Test 1: Permissions
        all_results["permissions"] = await tester.test_permissions()
        
        # Test 2: Location Data Contract
        all_results["data_contract"] = await tester.test_location_data_contract()
        
        # Test 3: Toggle & Update
        all_results["toggle_update"] = await tester.test_toggle_and_update()
        
        # Test 4: Location RP Still Works
        all_results["location_rp"] = await tester.test_location_rp_still_works()
    
    return all_results

def print_test_summary(results):
    """Print comprehensive test summary"""
    print("\n" + "=" * 80)
    print("🏁 LOCATION MANAGEMENT TEST SUMMARY")
    print("=" * 80)
    
    # Setup
    setup_status = "✅ PASS" if results["setup"] else "❌ FAIL"
    print(f"{setup_status} Setup (User Authentication & Character Creation)")
    
    # Permissions
    permissions = results["permissions"]
    if permissions:
        perm_passed = sum(1 for v in permissions.values() if v)
        perm_total = len(permissions)
        perm_status = "✅ PASS" if perm_passed == perm_total else f"⚠️  PARTIAL ({perm_passed}/{perm_total})"
        print(f"{perm_status} Permissions Testing")
        
        if perm_passed < perm_total:
            failed_perms = [k for k, v in permissions.items() if not v]
            print(f"   Failed: {', '.join(failed_perms)}")
    else:
        print("❌ FAIL Permissions Testing (not run)")
    
    # Data Contract
    data_contract = results["data_contract"]
    if data_contract:
        dc_passed = sum(1 for v in data_contract.values() if v)
        dc_total = len(data_contract)
        dc_status = "✅ PASS" if dc_passed == dc_total else f"⚠️  PARTIAL ({dc_passed}/{dc_total})"
        print(f"{dc_status} Location Data Contract")
        
        if dc_passed < dc_total:
            failed_dc = [k for k, v in data_contract.items() if not v]
            print(f"   Failed: {', '.join(failed_dc)}")
    else:
        print("❌ FAIL Location Data Contract (not run)")
    
    # Toggle & Update
    toggle_update = results["toggle_update"]
    if toggle_update:
        tu_passed = sum(1 for v in toggle_update.values() if v)
        tu_total = len(toggle_update)
        tu_status = "✅ PASS" if tu_passed == tu_total else f"⚠️  PARTIAL ({tu_passed}/{tu_total})"
        print(f"{tu_status} Toggle & Update Functionality")
        
        if tu_passed < tu_total:
            failed_tu = [k for k, v in toggle_update.items() if not v]
            print(f"   Failed: {', '.join(failed_tu)}")
    else:
        print("❌ FAIL Toggle & Update Functionality (not run)")
    
    # Location RP
    location_rp = results["location_rp"]
    if location_rp:
        rp_passed = sum(1 for v in location_rp.values() if v)
        rp_total = len(location_rp)
        rp_status = "✅ PASS" if rp_passed == rp_total else f"⚠️  PARTIAL ({rp_passed}/{rp_total})"
        print(f"{rp_status} Location RP Functionality")
        
        if rp_passed < rp_total:
            failed_rp = [k for k, v in location_rp.items() if not v]
            print(f"   Failed: {', '.join(failed_rp)}")
    else:
        print("❌ FAIL Location RP Functionality (not run)")
    
    # Overall summary
    print("-" * 80)
    
    # Count total tests
    total_tests = 1  # setup
    total_passed = 1 if results["setup"] else 0
    
    for category in ["permissions", "data_contract", "toggle_update", "location_rp"]:
        if results[category]:
            category_total = len(results[category])
            category_passed = sum(1 for v in results[category].values() if v)
            total_tests += category_total
            total_passed += category_passed
    
    print(f"OVERALL: {total_passed}/{total_tests} tests passed ({total_passed/total_tests*100:.1f}%)")
    
    if total_passed == total_tests:
        print("🎉 ALL TESTS PASSED! Location management system is working correctly.")
        print("✅ Admin and moderator permissions working")
        print("✅ Location data contract validated")
        print("✅ Toggle and update functionality working")
        print("✅ Location RP integration working")
    else:
        print("⚠️  Some tests failed. Check detailed output above.")
        
        # Critical issues
        if not results["setup"]:
            print("\n🚨 CRITICAL: Setup failed - check user authentication")
        
        if results["permissions"]:
            failed_perms = [k for k, v in results["permissions"].items() if not v and "denied" in k]
            if len(failed_perms) < 3:  # Should have 3 "denied" tests
                print("\n🚨 SECURITY ISSUE: Member access not properly restricted")
    
    print("=" * 80)

if __name__ == "__main__":
    results = asyncio.run(run_location_management_tests())
    print_test_summary(results)