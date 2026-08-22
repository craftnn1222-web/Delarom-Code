import React, { useEffect, useState, useMemo, useRef, useCallback } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { getCitiesByNation, getCityImage } from '../utils/api';
import { toast } from 'sonner';
import AnimatedBackground from '../components/AnimatedBackground';
import Navbar from '../components/Navbar';
import { Button } from '../components/ui/button';
import { ArrowLeft, MapPin, Search, Filter, X, Building2, Home, Castle } from 'lucide-react';
import { useMusic } from '../contexts/MusicContext';

// Skeleton component for loading state
const CityCardSkeleton = () => (
  <div className="glass-dark p-6 rounded-xl border border-transparent animate-pulse">
    <div className="mb-4 rounded-lg overflow-hidden border-2 border-purple-500/30">
      <div className="w-full h-48 bg-gray-700/50" />
    </div>
    <div className="h-7 bg-gray-700/50 rounded w-3/4 mb-2" />
    <div className="h-4 bg-gray-700/50 rounded w-1/2 mb-2" />
    <div className="h-6 bg-gray-700/50 rounded w-1/3 mb-3" />
    <div className="space-y-2 mb-4">
      <div className="h-3 bg-gray-700/50 rounded w-full" />
      <div className="h-3 bg-gray-700/50 rounded w-5/6" />
    </div>
    <div className="h-10 bg-gray-700/50 rounded w-full" />
  </div>
);

// Lazy loaded image component that fetches from API when in view
const LazyImage = ({ nation, citySlug, alt, className, hasImage }) => {
  const [imageUrl, setImageUrl] = useState(null);
  const [isLoaded, setIsLoaded] = useState(false);
  const [isInView, setIsInView] = useState(false);
  const [fetchAttempted, setFetchAttempted] = useState(false);
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

  // Fetch image when in view and has_image is true
  useEffect(() => {
    if (isInView && hasImage && !fetchAttempted) {
      setFetchAttempted(true);
      getCityImage(nation, citySlug)
        .then(res => {
          if (res.data.image_url) {
            setImageUrl(res.data.image_url);
          }
        })
        .catch(err => {
          console.error(`Failed to load image for ${citySlug}:`, err);
        });
    }
  }, [isInView, hasImage, nation, citySlug, fetchAttempted]);

  // Don't render if no image
  if (!hasImage) {
    return null;
  }

  return (
    <div ref={imgRef} className="relative w-full h-48">
      {/* Skeleton placeholder */}
      {!isLoaded && (
        <div className="absolute inset-0 bg-gray-700/50 animate-pulse flex items-center justify-center">
          <MapPin className="w-8 h-8 text-gray-600" />
        </div>
      )}
      {/* Actual image - only load when we have the URL */}
      {imageUrl && (
        <img
          src={imageUrl}
          alt={alt}
          className={`${className} transition-opacity duration-300 ${isLoaded ? 'opacity-100' : 'opacity-0'}`}
          onLoad={() => setIsLoaded(true)}
          loading="lazy"
        />
      )}
    </div>
  );
};

// City card component with lazy loading
const CityCard = ({ city, nation, onClick, getEntityIcon }) => {
  const [isVisible, setIsVisible] = useState(false);
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

  return (
    <div
      ref={cardRef}
      onClick={onClick}
      className="glass-dark p-6 rounded-xl cursor-pointer hover:border-purple-500/50 border border-transparent transition-all transform hover:scale-105"
      data-testid={`city-card-${city.slug}`}
    >
      {isVisible ? (
        <>
          {city.has_image && (
            <div className="mb-4 rounded-lg overflow-hidden border-2 border-purple-500/30">
              <LazyImage
                nation={nation}
                citySlug={city.slug}
                alt={city.name}
                className="w-full h-48 object-cover"
                hasImage={city.has_image}
              />
            </div>
          )}
          
          <div className="flex items-center gap-2 mb-2">
            <h2 className="text-2xl font-bold text-purple-300">{city.name}</h2>
            {city.entity_type && (
              <span className="text-gray-400" title={city.entity_type}>
                {getEntityIcon(city.entity_type)}
              </span>
            )}
          </div>
          
          {city.region && (
            <p className="text-sm text-gray-400 mb-2">{city.region}</p>
          )}
          
          {city.faction && (
            <div className="inline-block px-3 py-1 rounded-full bg-purple-500/20 text-purple-300 text-xs font-semibold mb-3">
              {city.faction}
            </div>
          )}
          
          <p className="text-gray-300 text-sm mb-4 line-clamp-3">
            {city.description}
          </p>
          
          <Button className="w-full bg-gradient-to-r from-purple-600 to-pink-600">
            <MapPin className="w-4 h-4 mr-2" />
            Explore {city.entity_type || 'Location'}
          </Button>
        </>
      ) : (
        <CityCardSkeleton />
      )}
    </div>
  );
};

const Cities = () => {
  const { nation } = useParams();
  const navigate = useNavigate();
  const [cities, setCities] = useState([]);
  const [loading, setLoading] = useState(true);
  const { changeTrack } = useMusic();
  
  // Filter states
  const [searchTerm, setSearchTerm] = useState('');
  const [entityTypeFilter, setEntityTypeFilter] = useState('all');
  const [factionFilter, setFactionFilter] = useState('all');
  const [regionFilter, setRegionFilter] = useState('all');
  const [showFilters, setShowFilters] = useState(false);

  const nationNames = {
    'ammeonon': 'Ammeonon',
    'selindori': 'Selindori',
    'dhor-kuldor': 'Dhor-Kuldor',
    'aigraels': 'Aigraels',
    'veiled-realms': 'The Veiled Realms'
  };

  const nationName = nationNames[nation] || nation;

  // Auto-switch music when entering a nation
  useEffect(() => {
    if (nation) {
      changeTrack(nation);
    }
  }, [nation, changeTrack]);

  const fetchCities = useCallback(async () => {
    setLoading(true);
    try {
      const response = await getCitiesByNation(nation);
      setCities(response.data);
    } catch (error) {
      console.error('Error fetching cities:', error);
      toast.error('Failed to load cities');
    } finally {
      setLoading(false);
    }
  }, [nation]);

  useEffect(() => {
    fetchCities();
  }, [fetchCities]);

  // Extract unique factions and regions for filter dropdowns
  const { uniqueFactions, uniqueRegions, uniqueEntityTypes } = useMemo(() => {
    const factions = [...new Set(cities.map(c => c.faction).filter(Boolean))].sort();
    const regions = [...new Set(cities.map(c => c.region).filter(Boolean))].sort();
    const entityTypes = [...new Set(cities.map(c => c.entity_type).filter(Boolean))].sort();
    return { 
      uniqueFactions: factions, 
      uniqueRegions: regions,
      uniqueEntityTypes: entityTypes
    };
  }, [cities]);

  // Filter cities based on all criteria
  const filteredCities = useMemo(() => {
    return cities.filter(city => {
      const searchLower = searchTerm.toLowerCase();
      const matchesSearch = !searchTerm || 
        city.name.toLowerCase().includes(searchLower) ||
        (city.description && city.description.toLowerCase().includes(searchLower)) ||
        (city.faction && city.faction.toLowerCase().includes(searchLower)) ||
        (city.region && city.region.toLowerCase().includes(searchLower));
      
      const matchesEntityType = entityTypeFilter === 'all' || city.entity_type === entityTypeFilter;
      const matchesFaction = factionFilter === 'all' || city.faction === factionFilter;
      const matchesRegion = regionFilter === 'all' || city.region === regionFilter;
      
      return matchesSearch && matchesEntityType && matchesFaction && matchesRegion;
    });
  }, [cities, searchTerm, entityTypeFilter, factionFilter, regionFilter]);

  const handleCityClick = useCallback((citySlug) => {
    navigate(`/nations/${nation}/${citySlug}`);
  }, [navigate, nation]);

  const clearFilters = () => {
    setSearchTerm('');
    setEntityTypeFilter('all');
    setFactionFilter('all');
    setRegionFilter('all');
  };

  const activeFilterCount = [
    searchTerm,
    entityTypeFilter !== 'all' ? entityTypeFilter : null,
    factionFilter !== 'all' ? factionFilter : null,
    regionFilter !== 'all' ? regionFilter : null
  ].filter(Boolean).length;

  const getEntityIcon = useCallback((entityType) => {
    switch(entityType) {
      case 'City':
        return <Building2 className="w-4 h-4" />;
      case 'Town':
        return <Home className="w-4 h-4" />;
      default:
        return <Castle className="w-4 h-4" />;
    }
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen relative">
        <AnimatedBackground />
        <Navbar />
        <div className="relative z-10 container mx-auto px-4 py-8">
          <div className="mb-8">
            <div className="h-12 bg-gray-700/30 rounded w-64 mb-4 animate-pulse" />
            <div className="h-6 bg-gray-700/30 rounded w-48 animate-pulse" />
          </div>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[...Array(6)].map((_, i) => (
              <CityCardSkeleton key={`city-skel-${i}`} />
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen relative">
      <AnimatedBackground />
      <Navbar />
      
      <div className="relative z-10 container mx-auto px-4 py-8">
        <Link to="/nations">
          <Button variant="ghost" className="mb-6 text-purple-400" data-testid="back-to-nations-btn">
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Nations
          </Button>
        </Link>

        <div className="mb-8">
          <h1 className="text-4xl sm:text-5xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-pink-600 mb-4">
            Cities of {nationName}
          </h1>
          <p className="text-gray-300 text-lg">
            Choose a city to explore its locations
          </p>
        </div>

        {/* Search and Filter Bar */}
        {cities.length > 0 && (
          <div className="mb-6 space-y-4">
            {/* Search Bar */}
            <div className="flex gap-4 flex-wrap">
              <div className="relative flex-1 min-w-[250px]">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
                <input
                  type="text"
                  placeholder="Search cities, towns, factions..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="w-full pl-10 pr-4 py-3 bg-gray-800/50 border border-purple-500/30 rounded-xl text-white placeholder-gray-400 focus:outline-none focus:border-purple-500 transition-colors"
                  data-testid="city-search-input"
                />
                {searchTerm && (
                  <button 
                    onClick={() => setSearchTerm('')}
                    className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-white"
                  >
                    <X className="w-4 h-4" />
                  </button>
                )}
              </div>
              
              <Button 
                variant="outline" 
                onClick={() => setShowFilters(!showFilters)}
                className={`border-purple-500/30 ${showFilters ? 'bg-purple-500/20 text-purple-300' : 'text-gray-300'}`}
                data-testid="toggle-filters-btn"
              >
                <Filter className="w-4 h-4 mr-2" />
                Filters
                {activeFilterCount > 0 && (
                  <span className="ml-2 px-2 py-0.5 bg-purple-500 text-white text-xs rounded-full">
                    {activeFilterCount}
                  </span>
                )}
              </Button>
            </div>

            {/* Filter Dropdowns */}
            {showFilters && (
              <div className="glass-dark p-4 rounded-xl border border-purple-500/30 animate-in slide-in-from-top-2">
                <div className="flex flex-wrap gap-4 items-end">
                  {uniqueEntityTypes.length > 0 && (
                    <div className="flex-1 min-w-[150px]">
                      <label className="block text-sm text-gray-400 mb-2">Type</label>
                      <select
                        value={entityTypeFilter}
                        onChange={(e) => setEntityTypeFilter(e.target.value)}
                        className="w-full px-3 py-2 bg-gray-800/50 border border-purple-500/30 rounded-lg text-white focus:outline-none focus:border-purple-500"
                        data-testid="entity-type-filter"
                      >
                        <option value="all">All Types</option>
                        {uniqueEntityTypes.map(type => (
                          <option key={type} value={type}>{type}</option>
                        ))}
                      </select>
                    </div>
                  )}

                  {uniqueFactions.length > 0 && (
                    <div className="flex-1 min-w-[200px]">
                      <label className="block text-sm text-gray-400 mb-2">Faction</label>
                      <select
                        value={factionFilter}
                        onChange={(e) => setFactionFilter(e.target.value)}
                        className="w-full px-3 py-2 bg-gray-800/50 border border-purple-500/30 rounded-lg text-white focus:outline-none focus:border-purple-500"
                        data-testid="faction-filter"
                      >
                        <option value="all">All Factions</option>
                        {uniqueFactions.map(faction => (
                          <option key={faction} value={faction}>{faction}</option>
                        ))}
                      </select>
                    </div>
                  )}

                  {uniqueRegions.length > 0 && (
                    <div className="flex-1 min-w-[200px]">
                      <label className="block text-sm text-gray-400 mb-2">Region</label>
                      <select
                        value={regionFilter}
                        onChange={(e) => setRegionFilter(e.target.value)}
                        className="w-full px-3 py-2 bg-gray-800/50 border border-purple-500/30 rounded-lg text-white focus:outline-none focus:border-purple-500"
                        data-testid="region-filter"
                      >
                        <option value="all">All Regions</option>
                        {uniqueRegions.map(region => (
                          <option key={region} value={region}>{region}</option>
                        ))}
                      </select>
                    </div>
                  )}

                  {activeFilterCount > 0 && (
                    <Button 
                      variant="ghost" 
                      onClick={clearFilters}
                      className="text-purple-400 hover:text-purple-300"
                      data-testid="clear-filters-btn"
                    >
                      <X className="w-4 h-4 mr-2" />
                      Clear All
                    </Button>
                  )}
                </div>
              </div>
            )}

            {/* Results Count */}
            <div className="text-gray-400 text-sm">
              Showing {filteredCities.length} of {cities.length} locations
              {activeFilterCount > 0 && (
                <button 
                  onClick={clearFilters}
                  className="ml-2 text-purple-400 hover:text-purple-300 underline"
                >
                  (clear filters)
                </button>
              )}
            </div>
          </div>
        )}

        {cities.length === 0 ? (
          <div className="glass-dark p-12 rounded-2xl text-center">
            <MapPin className="w-16 h-16 mx-auto mb-4 text-purple-400" />
            <h2 className="text-2xl font-bold mb-2 text-white">No Cities Yet</h2>
            <p className="text-gray-400 mb-6">Cities for this nation are being prepared.</p>
          </div>
        ) : filteredCities.length === 0 ? (
          <div className="glass-dark p-12 rounded-2xl text-center">
            <Search className="w-16 h-16 mx-auto mb-4 text-purple-400" />
            <h2 className="text-2xl font-bold mb-2 text-white">No Results Found</h2>
            <p className="text-gray-400 mb-6">Try adjusting your search or filters.</p>
            <Button 
              onClick={clearFilters}
              className="bg-gradient-to-r from-purple-600 to-pink-600"
            >
              Clear All Filters
            </Button>
          </div>
        ) : (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredCities.map((city) => (
              <CityCard
                key={city.id}
                city={city}
                nation={nation}
                onClick={() => handleCityClick(city.slug)}
                getEntityIcon={getEntityIcon}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default Cities;
