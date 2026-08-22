import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import AnimatedBackground from '../components/AnimatedBackground';
import Navbar from '../components/Navbar';
import { Button } from '../components/ui/button';
import { getCitiesByNation, getCityImage } from '../utils/api';
import { ArrowLeft, Building2, MapPin, Castle, Home } from 'lucide-react';

const NATION_LORE = {
  ammeonon: {
    name: 'Ammeonon',
    description: 'The human empire founded in 1200 by King Quentin Blackburn. Now in the year 215 A.E. (Astral Era), ruled by the Vritra Clan under Astral King Ausar.',
    lore: 'A land of diverse cities and rich history, from the capital Wymroost to the trading hub of Invrasil.',
    image: '/images/ammeonon.jpg',
  },
  'dhor-kuldor': {
    name: 'Dhor-Kuldor',
    description: 'Eight mighty dwarven holds carved deep into the mountains, each specializing in different crafts and magics.',
    lore: 'From the jewel-rich Thalgrin to the fire forges of Emberdeep, the dwarven holds stand as testament to ancient mastery.',
    image: '/images/dhor-kuldor.jpg',
  },
  selindori: {
    name: 'Selindori',
    description: 'The elven kingdom of Yillhone, the Crystal City. Home to six elven races with divine origins.',
    lore: 'An ancient realm where Sun Elves, Forest Elves, Mist Elves, Snow Elves, Mountain Elves, and Shadow Elves coexist in a complex hierarchy.',
    image: '/images/selindori.jpg',
  },
  aigraels: {
    name: 'Aigraels',
    description: 'A land of shifting power where three factions vie for control.',
    lore: 'The throne changes hands like the wind in this tumultuous realm.',
    image: '/images/aigraels.jpg',
  },
};

const CITY_TYPE_ICON = {
  capital: Castle,
  city: Building2,
  town: Home,
  village: Home,
  hold: Castle,
  fortress: Castle,
};

const CityCard = ({ nation, city }) => {
  const [imgUrl, setImgUrl] = useState(null);
  const Icon = CITY_TYPE_ICON[(city.city_type || '').toLowerCase()] || Building2;

  useEffect(() => {
    let cancelled = false;
    if (city.has_image) {
      getCityImage(nation, city.slug)
        .then((res) => { if (!cancelled) setImgUrl(res.data?.image_url || null); })
        .catch(() => {});
    }
    return () => { cancelled = true; };
  }, [nation, city.slug, city.has_image]);

  return (
    <Link to={`/cities/${nation}/${city.slug}`} data-testid={`nation-city-${city.slug}`}>
      <div className="glass p-6 rounded-xl hover:scale-105 transition-transform cursor-pointer h-full flex flex-col">
        <div className="mb-4 rounded-lg overflow-hidden border border-purple-500/30 h-40 bg-gray-800/50 flex items-center justify-center">
          {imgUrl ? (
            <img src={imgUrl} alt={`${city.name} cityscape`} className="w-full h-full object-cover" />
          ) : (
            <MapPin className="w-10 h-10 text-purple-500/50" />
          )}
        </div>
        <div className="flex items-center gap-3 mb-3">
          <Icon className="w-8 h-8 text-purple-400" />
          <div>
            <h3 className="text-xl font-bold text-white">{city.name}</h3>
            {city.city_type && (
              <p className="text-xs text-purple-300 capitalize">{city.city_type}</p>
            )}
          </div>
        </div>
        {city.description && (
          <p className="text-gray-400 text-sm flex-1 line-clamp-3">{city.description}</p>
        )}
        <div className="mt-4">
          <span className="text-purple-400 text-sm font-semibold">View City →</span>
        </div>
      </div>
    </Link>
  );
};

const NationDetail = () => {
  const { nationName } = useParams();
  const [cities, setCities] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    getCitiesByNation(nationName)
      .then((res) => { if (!cancelled) setCities(res.data || []); })
      .catch(() => { if (!cancelled) setError('Failed to load cities'); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [nationName]);

  const nation = NATION_LORE[nationName];

  if (!nation) {
    return (
      <div className="min-h-screen relative">
        <AnimatedBackground />
        <Navbar />
        <div className="relative z-10 container mx-auto px-4 py-20 text-center">
          <h1 className="text-3xl font-bold text-white mb-4">Nation Not Found</h1>
          <Link to="/nations"><Button>Back to Nations</Button></Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen relative" data-testid="nation-detail-page">
      <AnimatedBackground />
      <Navbar />

      <div className="relative z-10 container mx-auto px-4 py-8">
        <Link to="/nations">
          <Button variant="ghost" className="mb-6 text-purple-400">
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Nations
          </Button>
        </Link>

        <div className="glass-dark p-8 rounded-2xl mb-8 grid lg:grid-cols-[2fr,3fr] gap-6 items-start">
          <div className="rounded-xl overflow-hidden border border-purple-500/40 max-h-72">
            <img src={nation.image} alt={`${nation.name} landscape`} className="w-full h-full object-cover" />
          </div>
          <div>
            <h1 className="text-5xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-pink-600 mb-4">
              {nation.name}
            </h1>
            <p className="text-xl text-gray-300 mb-4">{nation.description}</p>
            <p className="text-gray-400 italic">{nation.lore}</p>
          </div>
        </div>

        <div className="flex items-end justify-between mb-6 flex-wrap gap-3">
          <div>
            <h2 className="text-3xl font-bold text-purple-300">Cities of {nation.name}</h2>
            <p className="text-sm text-gray-500 mt-1">Choose a city to view its districts, taverns, and roleplay venues.</p>
          </div>
          <Link to={`/cities/${nationName}`}>
            <Button variant="outline" className="border-purple-500/40 text-purple-300" data-testid="view-all-cities-btn">
              View all cities →
            </Button>
          </Link>
        </div>

        {loading ? (
          <p className="text-gray-400">Loading cities...</p>
        ) : error ? (
          <p className="text-red-400 text-sm">{error}</p>
        ) : cities.length === 0 ? (
          <div className="glass-dark p-8 rounded-2xl text-center border border-purple-500/20">
            <MapPin className="w-10 h-10 text-purple-400 mx-auto mb-3" />
            <p className="text-gray-300">No cities defined for {nation.name} yet.</p>
            <p className="text-gray-500 text-sm mt-1">An admin can seed cities from the Admin Dashboard.</p>
          </div>
        ) : (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {cities.map((city) => (
              <CityCard key={city.slug} nation={nationName} city={city} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default NationDetail;
