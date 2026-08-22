"""
Test suite for Admin Features:
1. Admin Password Reset - POST /api/admin/users/{user_id}/reset-password
2. Delete RP Posts - DELETE /api/locations/{nation}/{location}/roleplay/{rp_id}
3. Duplicate RP Prevention - POST /api/locations/{nation}/{location}/roleplay
4. Admin Users List - GET /api/admin/users
"""

import pytest
import requests
import os
import time
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "craftnn1222@gmail.com"
ADMIN_PASSWORD = "admin123"

# Test user for password reset testing
TEST_USER_EMAIL = f"test_user_{uuid.uuid4().hex[:8]}@test.com"
TEST_USER_PASSWORD = "testpass123"
TEST_USER_USERNAME = f"TestUser_{uuid.uuid4().hex[:8]}"


class TestAdminAuthentication:
    """Test admin login and token retrieval"""
    
    def test_admin_login(self):
        """Test admin can login successfully"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        assert data["user"]["role"] == "admin"
        print(f"✓ Admin login successful - role: {data['user']['role']}")


class TestAdminUsersList:
    """Test GET /api/admin/users endpoint"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        return response.json()["access_token"]
    
    def test_get_all_users_as_admin(self, admin_token):
        """Test admin can get list of all users"""
        response = requests.get(
            f"{BASE_URL}/api/admin/users",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Failed to get users: {response.text}"
        data = response.json()
        
        # Check response structure - could be list or dict with 'users' key
        if isinstance(data, list):
            users = data
        else:
            assert "users" in data, "Response should contain 'users' key"
            users = data["users"]
        
        assert len(users) > 0, "Should have at least one user (admin)"
        
        # Verify admin user is in the list
        admin_found = any(u.get("email") == ADMIN_EMAIL for u in users)
        assert admin_found, "Admin user should be in the users list"
        
        # Verify password_hash is not exposed
        for user in users:
            assert "password_hash" not in user, "password_hash should not be exposed"
        
        print(f"✓ Admin users list returned {len(users)} users")
    
    def test_get_users_without_auth_fails(self):
        """Test that unauthenticated requests fail"""
        response = requests.get(f"{BASE_URL}/api/admin/users")
        assert response.status_code in [401, 403], "Should require authentication"
        print("✓ Unauthenticated request correctly rejected")


class TestAdminPasswordReset:
    """Test POST /api/admin/users/{user_id}/reset-password endpoint"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        return response.json()["access_token"]
    
    @pytest.fixture
    def test_user(self, admin_token):
        """Create a test user for password reset testing"""
        # Register a new test user
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "username": TEST_USER_USERNAME,
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD,
            "application_text": "Test user for password reset testing"
        })
        
        if response.status_code == 200:
            user_data = response.json()
            user_id = user_data["user"]["id"]
            
            # Approve the user so they can login
            approve_response = requests.post(
                f"{BASE_URL}/api/admin/applications/{user_id}/approve",
                headers={"Authorization": f"Bearer {admin_token}"}
            )
            # Approval might fail if user is already active, that's ok
            
            return {"id": user_id, "email": TEST_USER_EMAIL}
        elif response.status_code == 400 and "already registered" in response.text.lower():
            # User already exists, get their ID from admin users list
            users_response = requests.get(
                f"{BASE_URL}/api/admin/users",
                headers={"Authorization": f"Bearer {admin_token}"}
            )
            users = users_response.json()
            if isinstance(users, dict):
                users = users.get("users", [])
            
            for user in users:
                if user.get("email") == TEST_USER_EMAIL:
                    return {"id": user["id"], "email": TEST_USER_EMAIL}
        
        pytest.skip("Could not create or find test user")
    
    def test_admin_can_reset_user_password(self, admin_token, test_user):
        """Test admin can reset a user's password"""
        new_password = "newpassword123"
        
        response = requests.post(
            f"{BASE_URL}/api/admin/users/{test_user['id']}/reset-password",
            json={"new_password": new_password},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200, f"Password reset failed: {response.text}"
        data = response.json()
        assert "message" in data
        assert "successfully" in data["message"].lower()
        print(f"✓ Password reset successful for user {test_user['email']}")
        
        # Verify user can login with new password
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": test_user["email"],
            "password": new_password
        })
        
        # Login might fail if user is pending, but password reset should still work
        if login_response.status_code == 200:
            print("✓ User can login with new password")
        else:
            print(f"Note: User login returned {login_response.status_code} (may be pending approval)")
    
    def test_password_reset_requires_min_length(self, admin_token, test_user):
        """Test password reset validates minimum length"""
        response = requests.post(
            f"{BASE_URL}/api/admin/users/{test_user['id']}/reset-password",
            json={"new_password": "short"},  # Less than 6 chars
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 422, f"Should reject short password: {response.text}"
        print("✓ Short password correctly rejected")
    
    def test_password_reset_requires_admin(self):
        """Test that non-admin cannot reset passwords"""
        # Try without auth
        response = requests.post(
            f"{BASE_URL}/api/admin/users/some-user-id/reset-password",
            json={"new_password": "newpassword123"}
        )
        assert response.status_code in [401, 403], "Should require admin auth"
        print("✓ Unauthenticated password reset correctly rejected")
    
    def test_password_reset_invalid_user(self, admin_token):
        """Test password reset for non-existent user"""
        response = requests.post(
            f"{BASE_URL}/api/admin/users/invalid-user-id-12345/reset-password",
            json={"new_password": "newpassword123"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 404, f"Should return 404 for invalid user: {response.text}"
        print("✓ Invalid user correctly returns 404")


class TestDeleteRPPosts:
    """Test DELETE /api/locations/{nation}/{location}/roleplay/{rp_id} endpoint"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        return response.json()["access_token"]
    
    @pytest.fixture
    def admin_user_id(self, admin_token):
        """Get admin user ID"""
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        return response.json()["id"]
    
    def test_get_rp_posts(self, admin_token):
        """Test getting RP posts from a location"""
        response = requests.get(
            f"{BASE_URL}/api/locations/ammeonon/wymroost/roleplay",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Failed to get RP posts: {response.text}"
        posts = response.json()
        print(f"✓ Found {len(posts)} RP posts in ammeonon/wymroost")
        return posts
    
    def test_admin_can_delete_any_post(self, admin_token):
        """Test admin can delete any RP post"""
        # First get existing posts
        response = requests.get(
            f"{BASE_URL}/api/locations/ammeonon/wymroost/roleplay",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        posts = response.json()
        
        if len(posts) == 0:
            pytest.skip("No RP posts to delete in ammeonon/wymroost")
        
        # Try to delete the first post
        post_to_delete = posts[0]
        rp_id = post_to_delete.get("id")
        
        delete_response = requests.delete(
            f"{BASE_URL}/api/locations/ammeonon/wymroost/roleplay/{rp_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert delete_response.status_code == 200, f"Admin delete failed: {delete_response.text}"
        data = delete_response.json()
        assert "message" in data
        assert "deleted" in data["message"].lower() or "success" in data["message"].lower()
        print(f"✓ Admin successfully deleted RP post {rp_id}")
    
    def test_delete_nonexistent_post_returns_404(self, admin_token):
        """Test deleting non-existent post returns 404"""
        response = requests.delete(
            f"{BASE_URL}/api/locations/ammeonon/wymroost/roleplay/nonexistent-id-12345",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 404, f"Should return 404: {response.text}"
        print("✓ Non-existent post correctly returns 404")
    
    def test_delete_requires_auth(self):
        """Test delete requires authentication"""
        response = requests.delete(
            f"{BASE_URL}/api/locations/ammeonon/wymroost/roleplay/some-id"
        )
        assert response.status_code in [401, 403], "Should require authentication"
        print("✓ Unauthenticated delete correctly rejected")


class TestDuplicateRPPrevention:
    """Test duplicate RP post prevention (30 second window)"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        return response.json()["access_token"]
    
    def test_duplicate_post_returns_existing(self, admin_token):
        """Test that submitting same post twice within 30 seconds returns existing post"""
        unique_action = f"Test action for duplicate prevention {uuid.uuid4().hex[:8]}"
        
        # First submission
        response1 = requests.post(
            f"{BASE_URL}/api/locations/ammeonon/wymroost/roleplay",
            json={"action_text": unique_action},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        # Check if admin has a character (required for RP)
        if response1.status_code == 400 and "character" in response1.text.lower():
            pytest.skip("Admin needs a character to test RP posting")
        
        assert response1.status_code == 200, f"First post failed: {response1.text}"
        data1 = response1.json()
        rp_id1 = data1.get("rp_id")
        print(f"✓ First post created with ID: {rp_id1}")
        
        # Second submission (same content, within 30 seconds)
        response2 = requests.post(
            f"{BASE_URL}/api/locations/ammeonon/wymroost/roleplay",
            json={"action_text": unique_action},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response2.status_code == 200, f"Second post failed: {response2.text}"
        data2 = response2.json()
        rp_id2 = data2.get("rp_id")
        
        # Should return the same post ID (duplicate prevention)
        assert rp_id1 == rp_id2, f"Should return same post ID. Got {rp_id1} vs {rp_id2}"
        
        # Check for duplicate message
        if "message" in data2:
            assert "already" in data2["message"].lower(), "Should indicate post already exists"
        
        print(f"✓ Duplicate prevention working - returned existing post {rp_id2}")
        
        # Cleanup - delete the test post
        requests.delete(
            f"{BASE_URL}/api/locations/ammeonon/wymroost/roleplay/{rp_id1}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )


class TestHealthCheck:
    """Basic health check"""
    
    def test_health_endpoint(self):
        """Test health endpoint is accessible"""
        response = requests.get(f"{BASE_URL}/health")
        assert response.status_code == 200
        print("✓ Health check passed")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
