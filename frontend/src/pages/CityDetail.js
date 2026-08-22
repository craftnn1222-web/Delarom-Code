import React, { useEffect, useState, useRef, useCallback } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { getCity, getLocationsByCity, getLocationImage } from '../utils/api';
import { toast } from 'sonner';
import AnimatedBackground from '../components/AnimatedBackground';
import Navbar from '../components/Navbar';
import { Button } from '../components/ui/button';
import { ArrowLeft, MapPin, Scroll, Flag, Swords } from 'lucide-react';
import CityProducersPanel from '../components/CityProducersPanel';

// Skeleton component for location cards
const LocationCardSkeleton = () => (
  <div className="glass-dark p-6 rounded-xl border border-transparent animate-pulse">
    <div className="mb-4 rounded-lg overflow-hidden border-2 border-purple-500/30">
      <div className="w-full h-40 bg-gray-700/50" />
    </div>
    <div className="h-6 bg-gray-700/50 rounded w-3/4 mb-2" />
    <div className="h-4 bg-gray-700/50 rounded w-1/2 mb-2" />
    <div className="space-y-2 mb-4">
      <div className="h-3 bg-gray-700/50 rounded w-full" />
      <div className="h-3 bg-gray-700/50 rounded w-5/6" />
    </div>
    <div className="h-8 bg-gray-700/50 rounded w-full" />
  </div>
);

// Lazy loaded image component
const LazyImage = ({ src, alt, className, height = "h-40" }) => {
  const [isLoaded, setIsLoaded] = useState(false);
  const [isInView, setIsInView] = useState(false);
  const imgRef = useRef(null);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsInView(true);
          observer.disconnect();
        }
      },
      { rootMargin: '100px', threshold: 0.1 }
    );

    if (imgRef.current) {
      observer.observe(imgRef.current);
    }

    return () => observer.disconnect();
  }, []);

  return (
    <div ref={imgRef} className={`relative w-full ${height}`}>
      {!isLoaded && (
        <div className="absolute inset-0 bg-gray-700/50 animate-pulse flex items-center justify-center">
          <MapPin className="w-6 h-6 text-gray-600" />
        </div>
      )}
      {isInView && (
        <img
          src={src}
          alt={alt}
          className={`${className} transition-opacity duration-300 ${isLoaded ? 'opacity-100' : 'opacity-0'}`}
          onLoad={() => setIsLoaded(true)}
          loading="lazy"
        />
      )}
    </div>
  );
};

// Location card with lazy loading
const LocationCard = ({ location, nation, onClick }) => {
  const [isVisible, setIsVisible] = useState(false);
  const [imageUrl, setImageUrl] = useState(null);
  const cardRef = useRef(null);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsVisible(true);
          observer.disconnect();
        }
      },
      { rootMargin: '50px', threshold: 0.1 }
    );

    if (cardRef.current) {
      observer.observe(cardRef.current);
    }

    return () => observer.disconnect();
  }, []);

  // Lazy-fetch the image only after the card is in view AND backend reports has_image
  useEffect(() => {
    if (!isVisible || !location.has_image || imageUrl) return;
    let cancelled = false;
    getLocationImage(nation, location.slug)
      .then((res) => {
        if (!cancelled && res.data?.image_url) setImageUrl(res.data.image_url);
      })
      .catch((err) => {
        console.error('Failed to fetch location image:', err);
      });
    return () => { cancelled = true; };
  }, [isVisible, location.has_image, location.slug, nation, imageUrl]);

  if (!isVisible) {
    return (
      <div ref={cardRef}>
        <LocationCardSkeleton />
      </div>
    );
  }

  return (
    <div
      ref={cardRef}
      onClick={onClick}
      className="glass-dark p-6 rounded-xl cursor-pointer hover:border-purple-500/50 border border-transparent transition-all transform hover:scale-105"
      data-testid={`location-card-${location.slug}`}
    >
      {location.has_image && (
        <div className="mb-4 rounded-lg overflow-hidden border-2 border-purple-500/30">
          {imageUrl ? (
            <LazyImage
              src={imageUrl}
              alt={location.name}
              className="w-full h-40 object-cover"
              height="h-40"
            />
          ) : (
            <div className="w-full h-40 bg-gray-700/40 animate-pulse flex items-center justify-center">
              <MapPin className="w-6 h-6 text-gray-600" />
            </div>
          )}
        </div>
      )}
      
      <h3 className="text-xl font-bold text-purple-300 mb-2">{location.name}</h3>
      
      {location.location_type && (
        <p className="text-sm text-gray-400 mb-2">{location.location_type}</p>
      )}

      {location.siege_state && (
        <div className="mb-3 flex items-center gap-2 rounded-md border border-rose-700/50 bg-rose-950/40 px-2 py-1.5 text-xs text-rose-200" data-testid={`siege-banner-${location.slug}`}>
          <Swords className="w-3.5 h-3.5 text-rose-300 flex-shrink-0" />
          <span className="line-clamp-1">Under siege by {location.siege_state.attacker_faction_name}</span>
        </div>
      )}
      {!location.siege_state && location.controlling_faction_slug && (
        <div className="mb-3 flex items-center gap-2 rounded-md border border-amber-700/40 bg-amber-950/30 px-2 py-1.5 text-xs text-amber-200" data-testid={`held-banner-${location.slug}`}>
          <Flag className="w-3.5 h-3.5 text-amber-300 flex-shrink-0" />
          <span className="line-clamp-1">Held by {location.controlling_faction_name || location.controlling_faction_slug}</span>
        </div>
      )}

      <p className="text-gray-300 text-sm mb-4 line-clamp-3">
        {location.description}
      </p>
      
      <Button className="w-full bg-gradient-to-r from-purple-600 to-pink-600" size="sm">
        Enter Location →
      </Button>
    </div>
  );
};

const CityDetail = () => {
  const { nation, citySlug } = useParams();
  const navigate = useNavigate();
  const [city, setCity] = useState(null);
  const [locations, setLocations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [cityImageLoaded, setCityImageLoaded] = useState(false);

  const fetchCityData = useCallback(async () => {
    setLoading(true);
    setCityImageLoaded(false);
    // allSettled so a transient locations fetch failure doesn't also blank
    // out the city header (same robustness pattern applied elsewhere).
    const [cityResponse, locationsResponse] = await Promise.allSettled([
      getCity(nation, citySlug),
      getLocationsByCity(nation, citySlug),
    ]);
    if (cityResponse.status === 'fulfilled') {
      setCity(cityResponse.value.data);
    } else {
      console.error('Error fetching city:', cityResponse.reason);
      toast.error('Failed to load city information');
    }
    if (locationsResponse.status === 'fulfilled') {
      setLocations(locationsResponse.value.data || []);
    } else {
      console.error('Error fetching locations:', locationsResponse.reason);
    }
    setLoading(false);
  }, [nation, citySlug]);

  useEffect(() => {
    fetchCityData();
  }, [fetchCityData]);

  const handleLocationClick = useCallback((locationSlug) => {
    navigate(`/roleplay/${nation}/${locationSlug}`);
  }, [navigate, nation]);

  if (loading) {
    return (
      <div className="min-h-screen relative">
        <AnimatedBackground />
        <Navbar />
        <div className="relative z-10 container mx-auto px-4 py-8">
          <div className="h-10 bg-gray-700/30 rounded w-32 mb-6 animate-pulse" />
          <div className="glass-dark p-8 rounded-2xl mb-8 animate-pulse">
            <div className="w-full h-96 bg-gray-700/50 rounded-xl mb-6" />
            <div className="h-12 bg-gray-700/50 rounded w-1/2 mb-4" />
            <div className="h-6 bg-gray-700/50 rounded w-1/3 mb-4" />
            <div className="space-y-2">
              <div className="h-4 bg-gray-700/50 rounded w-full" />
              <div className="h-4 bg-gray-700/50 rounded w-5/6" />
            </div>
          </div>
          <div className="h-8 bg-gray-700/30 rounded w-48 mb-6 animate-pulse" />
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[...Array(6)].map((_, i) => (
              <LocationCardSkeleton key={`loc-skel-${i}`} />
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (!city) {
    return (
      <div className="min-h-screen relative">
        <AnimatedBackground />
        <Navbar />
        <div className="relative z-10 container mx-auto px-4 py-20 text-center">
          <h1 className="text-3xl font-bold text-white mb-4">City Not Found</h1>
          <Link to={`/nations/${nation}/cities`}>
            <Button>Back to Cities</Button>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen relative">
      <AnimatedBackground />
      <Navbar />
      
      <div className="relative z-10 container mx-auto px-4 py-8">
        <Link to={`/nations/${nation}/cities`}>
          <Button variant="ghost" className="mb-6 text-purple-400" data-testid="back-to-cities-btn">
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Cities
          </Button>
        </Link>

        {/* City Header */}
        <div className="glass-dark p-8 rounded-2xl mb-8">
          {city.image_url && (
            <div className="mb-6 rounded-xl overflow-hidden border border-purple-500/40 relative">
              {!cityImageLoaded && (
                <div className="absolute inset-0 bg-gray-700/50 animate-pulse flex items-center justify-center">
                  <MapPin className="w-12 h-12 text-gray-600" />
                </div>
              )}
              <img
                src={city.image_url}
                alt={city.name}
                className={`w-full h-96 object-cover transition-opacity duration-300 ${cityImageLoaded ? 'opacity-100' : 'opacity-0'}`}
                onLoad={() => setCityImageLoaded(true)}
                loading="eager"
              />
            </div>
          )}
          
          <div className="flex items-start justify-between mb-4">
            <div>
              <h1 className="text-4xl sm:text-5xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-pink-600 mb-2">
                {city.name}
              </h1>
              {city.region && (
                <p className="text-gray-400 text-lg mb-2">{city.region}</p>
              )}
              {city.faction && (
                <div className="inline-block px-4 py-2 rounded-full bg-purple-500/20 text-purple-300 text-sm font-semibold">
                  {city.faction}
                </div>
              )}
            </div>
          </div>
          
          <p className="text-gray-300 text-lg mb-4">{city.description}</p>
          
          {city.lore && (
            <div className="mt-6 p-4 bg-black/30 rounded-lg border border-purple-500/20">
              <h3 className="text-xl font-semibold text-purple-300 mb-2 flex items-center">
                <Scroll className="w-5 h-5 mr-2" />
                Lore
              </h3>
              <p className="text-gray-300 whitespace-pre-line">{city.lore}</p>
            </div>
          )}
        </div>

        {/* Produced Here — real economy panel (renders only if city has producers) */}
        <CityProducersPanel nation={nation} citySlug={citySlug} className="mb-8" />

        {/* Locations */}
        <div className="mb-8">
          <h2 className="text-3xl font-bold text-white mb-2">
            Locations in {city.name}
          </h2>
          <p className="text-gray-400 mb-6">{locations.length} locations to explore</p>
          
          {locations.length === 0 ? (
            <div className="glass-dark p-12 rounded-2xl text-center">
              <MapPin className="w-16 h-16 mx-auto mb-4 text-purple-400" />
              <h3 className="text-2xl font-bold mb-2 text-white">No Locations Yet</h3>
              <p className="text-gray-400 mb-6">Locations for this city are being prepared.</p>
            </div>
          ) : (
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
              {locations.map((location) => (
                <LocationCard
                  key={location.id}
                  location={location}
                  nation={nation}
                  onClick={() => handleLocationClick(location.slug)}
                />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default CityDetail;
