"""
Test suite for locations API endpoints.
Tests that all nations have locations with images as per the requirement.
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://npc-economy-preview.preview.emergentagent.com').rstrip('/')

# Test credentials
ADMIN_EMAIL = "craftnn1222@gmail.com"
ADMIN_PASSWORD = "admin123"

# All nations to test
NATIONS = ["ammeonon", "dhor-kuldor", "selindori", "aigraels", "veiled-realms"]


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for admin user"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    assert response.status_code == 200, f"Login failed: {response.text}"
    return response.json()["access_token"]


@pytest.fixture(scope="module")
def admin_headers(auth_token):
    """Headers with auth token"""
    return {"Authorization": f"Bearer {auth_token}"}


class TestLocationsStatus:
    """Test /api/admin/locations-status endpoint"""
    
    def test_locations_status_endpoint(self, admin_headers):
        """Test that locations-status endpoint returns data for all nations"""
        response = requests.get(
            f"{BASE_URL}/api/admin/locations-status",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify all nations are present
        for nation in NATIONS:
            assert nation in data, f"Nation {nation} missing from locations-status"
    
    def test_ammeonon_zero_missing_images(self, admin_headers):
        """Test Ammeonon has 0 missing images"""
        response = requests.get(
            f"{BASE_URL}/api/admin/locations-status",
            headers=admin_headers
        )
        data = response.json()
        assert data["ammeonon"]["missing_images"] == 0, f"Ammeonon has {data['ammeonon']['missing_images']} missing images"
        assert data["ammeonon"]["total"] > 0, "Ammeonon should have locations"
    
    def test_dhor_kuldor_zero_missing_images(self, admin_headers):
        """Test Dhor-Kuldor has 0 missing images"""
        response = requests.get(
            f"{BASE_URL}/api/admin/locations-status",
            headers=admin_headers
        )
        data = response.json()
        assert data["dhor-kuldor"]["missing_images"] == 0, f"Dhor-Kuldor has {data['dhor-kuldor']['missing_images']} missing images"
        assert data["dhor-kuldor"]["total"] > 0, "Dhor-Kuldor should have locations"
    
    def test_selindori_zero_missing_images(self, admin_headers):
        """Test Selindori has 0 missing images"""
        response = requests.get(
            f"{BASE_URL}/api/admin/locations-status",
            headers=admin_headers
        )
        data = response.json()
        assert data["selindori"]["missing_images"] == 0, f"Selindori has {data['selindori']['missing_images']} missing images"
        assert data["selindori"]["total"] > 0, "Selindori should have locations"
    
    def test_aigraels_zero_missing_images(self, admin_headers):
        """Test Aigraels has 0 missing images"""
        response = requests.get(
            f"{BASE_URL}/api/admin/locations-status",
            headers=admin_headers
        )
        data = response.json()
        assert data["aigraels"]["missing_images"] == 0, f"Aigraels has {data['aigraels']['missing_images']} missing images"
        assert data["aigraels"]["total"] > 0, "Aigraels should have locations"
    
    def test_veiled_realms_zero_missing_images(self, admin_headers):
        """Test Veiled Realms has 0 missing images"""
        response = requests.get(
            f"{BASE_URL}/api/admin/locations-status",
            headers=admin_headers
        )
        data = response.json()
        assert data["veiled-realms"]["missing_images"] == 0, f"Veiled Realms has {data['veiled-realms']['missing_images']} missing images"
        assert data["veiled-realms"]["total"] > 0, "Veiled Realms should have locations"


class TestLocationsByNation:
    """Test /api/locations/{nation} endpoint"""
    
    def test_ammeonon_locations_have_images(self):
        """Test Ammeonon locations have image_url"""
        response = requests.get(f"{BASE_URL}/api/locations/ammeonon")
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0, "Ammeonon should have locations"
        
        # Check all locations have images
        for loc in data:
            assert loc.get("image_url"), f"Location {loc.get('name')} missing image_url"
    
    def test_dhor_kuldor_locations_have_images(self):
        """Test Dhor-Kuldor locations have image_url"""
        response = requests.get(f"{BASE_URL}/api/locations/dhor-kuldor")
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0, "Dhor-Kuldor should have locations"
        
        # Sample check - verify at least 90% have images
        with_images = sum(1 for loc in data if loc.get("image_url"))
        assert with_images == len(data), f"Dhor-Kuldor: {len(data) - with_images} locations missing images"
    
    def test_selindori_locations_have_images(self):
        """Test Selindori locations have image_url"""
        response = requests.get(f"{BASE_URL}/api/locations/selindori")
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0, "Selindori should have locations"
        
        with_images = sum(1 for loc in data if loc.get("image_url"))
        assert with_images == len(data), f"Selindori: {len(data) - with_images} locations missing images"
    
    def test_aigraels_locations_have_images(self):
        """Test Aigraels locations have image_url"""
        response = requests.get(f"{BASE_URL}/api/locations/aigraels")
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0, "Aigraels should have locations"
        
        with_images = sum(1 for loc in data if loc.get("image_url"))
        assert with_images == len(data), f"Aigraels: {len(data) - with_images} locations missing images"
    
    def test_veiled_realms_locations_have_images(self):
        """Test Veiled Realms locations have image_url"""
        response = requests.get(f"{BASE_URL}/api/locations/veiled-realms")
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0, "Veiled Realms should have locations"
        
        with_images = sum(1 for loc in data if loc.get("image_url"))
        assert with_images == len(data), f"Veiled Realms: {len(data) - with_images} locations missing images"


class TestLocationsByCity:
    """Test /api/locations/{nation}/{city}/locations endpoint"""
    
    def test_ammeonon_city_locations(self):
        """Test locations for a city in Ammeonon"""
        # First get a city
        cities_response = requests.get(f"{BASE_URL}/api/cities/ammeonon")
        assert cities_response.status_code == 200
        cities = cities_response.json()
        assert len(cities) > 0, "Ammeonon should have cities"
        
        city_slug = cities[0]["slug"]
        
        # Get locations for that city
        response = requests.get(f"{BASE_URL}/api/locations/ammeonon/{city_slug}/locations")
        assert response.status_code == 200
        data = response.json()
        
        # Verify locations have images
        for loc in data:
            assert loc.get("image_url"), f"Location {loc.get('name')} in {city_slug} missing image_url"
    
    def test_dhor_kuldor_city_locations(self):
        """Test locations for a city in Dhor-Kuldor"""
        cities_response = requests.get(f"{BASE_URL}/api/cities/dhor-kuldor")
        assert cities_response.status_code == 200
        cities = cities_response.json()
        assert len(cities) > 0, "Dhor-Kuldor should have cities"
        
        city_slug = cities[0]["slug"]
        
        response = requests.get(f"{BASE_URL}/api/locations/dhor-kuldor/{city_slug}/locations")
        assert response.status_code == 200
        data = response.json()
        
        for loc in data:
            assert loc.get("image_url"), f"Location {loc.get('name')} in {city_slug} missing image_url"


class TestCitiesLazyLoading:
    """Test cities lazy loading for Dhor-Kuldor (80 cities)"""
    
    def test_dhor_kuldor_cities_count(self):
        """Test Dhor-Kuldor has 80 cities"""
        response = requests.get(f"{BASE_URL}/api/cities/dhor-kuldor")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 80, f"Dhor-Kuldor should have at least 80 cities, got {len(data)}"
    
    def test_cities_response_has_has_image_flag(self):
        """Test cities response has has_image flag instead of image_url"""
        response = requests.get(f"{BASE_URL}/api/cities/dhor-kuldor")
        assert response.status_code == 200
        data = response.json()
        
        # Check first city has has_image flag
        if data:
            city = data[0]
            assert "has_image" in city, "City should have has_image flag"
            # image_url should NOT be in the list response (lazy loading)
            assert "image_url" not in city, "City list should not include image_url (lazy loading)"
    
    def test_city_image_endpoint(self):
        """Test individual city image endpoint works"""
        # Get a city first
        cities_response = requests.get(f"{BASE_URL}/api/cities/dhor-kuldor")
        cities = cities_response.json()
        
        if cities and cities[0].get("has_image"):
            city_slug = cities[0]["slug"]
            response = requests.get(f"{BASE_URL}/api/city-image/dhor-kuldor/{city_slug}")
            assert response.status_code == 200
            data = response.json()
            assert "image_url" in data, "City image endpoint should return image_url"


class TestDatabaseStatus:
    """Test database status endpoint"""
    
    def test_db_status(self):
        """Test /api/db-status returns correct counts"""
        response = requests.get(f"{BASE_URL}/api/db-status")
        assert response.status_code == 200
        data = response.json()
        
        counts = data["counts"]
        assert counts["nations"] == 5, f"Expected 5 nations, got {counts['nations']}"
        assert counts["locations"] > 700, f"Expected 700+ locations, got {counts['locations']}"
