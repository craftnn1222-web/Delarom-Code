"""
Backend API tests for Cities endpoints - Testing lazy loading fix for Dhor-Kuldor cities page.

Tests:
1. /api/cities/{nation} - Returns city data WITHOUT image_url field (has has_image flag instead)
2. /api/city-image/{nation}/{city_slug} - Returns the image for a specific city
3. Verify response size is reasonable (not 200MB+)
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestCitiesAPI:
    """Test the cities API endpoints for lazy loading fix"""
    
    def test_health_check(self):
        """Verify backend is running via API endpoint"""
        # Use /api/db-status instead of /health since /health returns HTML from frontend
        response = requests.get(f"{BASE_URL}/api/db-status")
        assert response.status_code == 200
        data = response.json()
        assert "counts" in data, "Response should have 'counts' field"
        print(f"✓ Health check passed - DB has {data['counts']} records")
    
    def test_dhor_kuldor_cities_list_no_image_url(self):
        """Test /api/cities/dhor-kuldor returns cities WITHOUT image_url field"""
        response = requests.get(f"{BASE_URL}/api/cities/dhor-kuldor")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        cities = response.json()
        assert isinstance(cities, list), "Response should be a list"
        
        # Check response size is reasonable (should be < 1MB, not 200MB)
        response_size = len(response.content)
        print(f"Response size for dhor-kuldor cities: {response_size / 1024:.2f} KB")
        assert response_size < 1024 * 1024, f"Response too large: {response_size / 1024 / 1024:.2f} MB"
        
        # Check that cities have expected fields but NOT image_url
        if len(cities) > 0:
            first_city = cities[0]
            
            # Should have these fields
            assert "id" in first_city, "City should have 'id' field"
            assert "name" in first_city, "City should have 'name' field"
            assert "slug" in first_city, "City should have 'slug' field"
            assert "nation" in first_city, "City should have 'nation' field"
            assert "description" in first_city, "City should have 'description' field"
            assert "has_image" in first_city, "City should have 'has_image' flag"
            
            # Should NOT have image_url field
            assert "image_url" not in first_city, "City should NOT have 'image_url' field in list response"
            
            print(f"✓ Found {len(cities)} cities for dhor-kuldor")
            print(f"✓ First city: {first_city.get('name')} (has_image: {first_city.get('has_image')})")
        else:
            print("⚠ No cities found for dhor-kuldor")
    
    def test_dhor_kuldor_has_80_plus_cities(self):
        """Verify Dhor-Kuldor has 80+ cities as mentioned in the problem statement"""
        response = requests.get(f"{BASE_URL}/api/cities/dhor-kuldor")
        assert response.status_code == 200
        
        cities = response.json()
        city_count = len(cities)
        print(f"✓ Dhor-Kuldor has {city_count} cities")
        
        # Should have 80+ cities
        assert city_count >= 80, f"Expected 80+ cities, got {city_count}"
    
    def test_city_image_endpoint(self):
        """Test /api/city-image/{nation}/{city_slug} returns image for a specific city"""
        # First get a city slug from the list
        list_response = requests.get(f"{BASE_URL}/api/cities/dhor-kuldor")
        assert list_response.status_code == 200
        
        cities = list_response.json()
        assert len(cities) > 0, "Need at least one city to test"
        
        # Find a city with an image
        city_with_image = None
        for city in cities:
            if city.get("has_image"):
                city_with_image = city
                break
        
        if city_with_image:
            city_slug = city_with_image["slug"]
            print(f"Testing image endpoint for city: {city_with_image['name']} ({city_slug})")
            
            # Test the image endpoint
            image_response = requests.get(f"{BASE_URL}/api/city-image/dhor-kuldor/{city_slug}")
            assert image_response.status_code == 200, f"Expected 200, got {image_response.status_code}"
            
            image_data = image_response.json()
            assert "image_url" in image_data, "Response should have 'image_url' field"
            
            # Image URL should be a base64 data URL or a regular URL
            image_url = image_data.get("image_url")
            if image_url:
                assert isinstance(image_url, str), "image_url should be a string"
                print(f"✓ Image URL length: {len(image_url)} chars")
                # Check if it's a base64 image
                if image_url.startswith("data:image"):
                    print("✓ Image is base64 encoded")
                else:
                    print(f"✓ Image URL: {image_url[:100]}...")
            else:
                print("⚠ City has_image=True but image_url is empty")
        else:
            print("⚠ No cities with images found to test image endpoint")
    
    def test_city_image_endpoint_404_for_invalid_city(self):
        """Test /api/city-image returns 404 for non-existent city"""
        response = requests.get(f"{BASE_URL}/api/city-image/dhor-kuldor/non-existent-city-12345")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ 404 returned for non-existent city")
    
    def test_ammeonon_cities_list(self):
        """Test cities endpoint works for other nations too (ammeonon)"""
        response = requests.get(f"{BASE_URL}/api/cities/ammeonon")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        cities = response.json()
        assert isinstance(cities, list), "Response should be a list"
        
        # Check response size
        response_size = len(response.content)
        print(f"Response size for ammeonon cities: {response_size / 1024:.2f} KB")
        
        if len(cities) > 0:
            first_city = cities[0]
            assert "has_image" in first_city, "City should have 'has_image' flag"
            assert "image_url" not in first_city, "City should NOT have 'image_url' field"
            print(f"✓ Found {len(cities)} cities for ammeonon")
        else:
            print("⚠ No cities found for ammeonon")
    
    def test_response_time_is_fast(self):
        """Test that the cities list endpoint responds quickly (< 5 seconds)"""
        start_time = time.time()
        response = requests.get(f"{BASE_URL}/api/cities/dhor-kuldor")
        end_time = time.time()
        
        response_time = end_time - start_time
        print(f"Response time for dhor-kuldor cities: {response_time:.2f} seconds")
        
        assert response.status_code == 200
        assert response_time < 5, f"Response too slow: {response_time:.2f} seconds"
        print(f"✓ Response time is acceptable: {response_time:.2f}s")


class TestCityListItemModel:
    """Test that CityListItem model is correctly structured"""
    
    def test_city_list_item_fields(self):
        """Verify CityListItem has correct fields"""
        response = requests.get(f"{BASE_URL}/api/cities/dhor-kuldor")
        assert response.status_code == 200
        
        cities = response.json()
        if len(cities) > 0:
            city = cities[0]
            
            # Expected fields from CityListItem model
            expected_fields = ["id", "nation", "slug", "name", "description", "has_image"]
            optional_fields = ["region", "lore", "faction", "entity_type", "is_active"]
            
            for field in expected_fields:
                assert field in city, f"Missing required field: {field}"
            
            # has_image should be a boolean
            assert isinstance(city["has_image"], bool), "has_image should be boolean"
            
            print(f"✓ CityListItem has all required fields")
            print(f"  Fields present: {list(city.keys())}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
