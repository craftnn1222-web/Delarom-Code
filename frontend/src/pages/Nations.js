import React, { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import AnimatedBackground from '../components/AnimatedBackground';
import Navbar from '../components/Navbar';
import { Button } from '../components/ui/button';
import { Castle, Mountain, Sparkles, Zap, Moon } from 'lucide-react';
import api from '../utils/api';

const Nations = () => {
  const [nationImages, setNationImages] = useState({});
  const [loadingImages, setLoadingImages] = useState(true);
  const fetchedRef = useRef(false);

  const nations = [
    {
      name: 'Ammeonon',
      slug: 'ammeonon',
      icon: <Castle className="w-16 h-16" />,
      description: 'The human empire, founded 1200 years ago by King Quentin Blackburn. Now ruled by the Vritra Clan under Astral King Ausar in the year 215 A.E.',
      color: 'from-blue-600 to-cyan-600',
      cities: ['Wymroost', 'Invrasil', 'Khastead', 'Plia', 'Folis', 'Crares', 'Yhule'],
    },
    {
      name: 'Dhor-Kuldor',
      slug: 'dhor-kuldor',
      icon: <Mountain className="w-16 h-16" />,
      description: 'Eight mighty dwarven holds carved into the mountains. Masters of smithing, mining, and ancient runecraft.',
      color: 'from-orange-600 to-red-600',
      cities: ['Karak Vorn', 'Kazad Drung', 'Barak Varr', 'Zhufbar', 'Karak Azul', 'Karak Kadrin', 'Karaz-a-Karak', 'Karak Norn'],
    },
    {
      name: 'Selindori',
      slug: 'selindori',
      icon: <Sparkles className="w-16 h-16" />,
      description: 'Kingdom of the First Elves, where Seren\'s divine touch blessed the earth. Six elven races dwell within Yillhone, the Crystal City, bound by hierarchy and ancient pride.',
      color: 'from-purple-600 to-pink-600',
      cities: ['Yillhone', 'Solarath', 'Thalenroot', 'Nal\'Theris', 'Isenfell', 'Aer\'Cyr'],
    },
    {
      name: 'Aigraels',
      slug: 'aigraels',
      icon: <Zap className="w-16 h-16" />,
      description: 'A land of shifting power where three factions vie for control. The throne changes hands like the wind.',
      color: 'from-green-600 to-teal-600',
      cities: ['Vaeloria', 'Thornwick', 'Misthollow', 'Ravencrest'],
    },
    {
      name: 'Veiled-Realms',
      slug: 'veiled-realms',
      icon: <Moon className="w-16 h-16" />,
      description: 'The Hidden Ancient Kingdoms—protected by powerful barrier magic. Rakesh of the Moon Elves, Yaksha-Shi of the Shadow Elves, and Serant-Kresh of the Crystalborn await those who can pierce the veil.',
      color: 'from-indigo-600 to-violet-600',
      cities: ['Niratha', 'Twilight Citadel', 'Kreshmar', 'Moonfall', 'Blackgrove'],
    }
  ];

  useEffect(() => {
    // Prevent double fetch in strict mode
    if (fetchedRef.current) return;
    fetchedRef.current = true;

    const fetchNationImages = async () => {
      try {
        // Fetch from dedicated nations endpoint
        const response = await api.get('/nations/images');
        const images = {};
        response.data.forEach(nation => {
          if (nation.image_url) {
            images[nation.slug] = nation.image_url;
          }
        });
        setNationImages(images);
      } catch (error) {
        console.error('Failed to fetch nation images:', error);
      } finally {
        setLoadingImages(false);
      }
    };

    fetchNationImages();
    // Empty deps: we only fetch once on mount; `fetchedRef` guards strict-mode double-invocation.
    // `api` is a stable module-level import, so it does not belong in deps.
  }, []);

  return (
    <div className="min-h-screen relative">
      <AnimatedBackground />
      <Navbar />
      
      <div className="relative z-10 container mx-auto px-4 py-8">
        <div className="text-center mb-12">
          <h1 className="text-5xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-pink-600 mb-4">
            Nations of Tyrandria
          </h1>
          <p className="text-gray-300 text-lg">
            Choose a nation to explore and begin your roleplay adventures
          </p>
        </div>

        <div className="grid md:grid-cols-2 gap-8">
          {nations.map((nation) => (
            <div key={nation.name} className="glass-dark p-8 rounded-2xl hover:scale-105 transition-transform duration-300" data-testid={`nation-card-${nation.slug}`}>
              {/* Nation Image */}
              <div className="mb-6 rounded-xl overflow-hidden border border-purple-500/40 h-48 bg-gray-800">
                {loadingImages ? (
                  <div className="w-full h-full animate-pulse bg-gray-700" />
                ) : nationImages[nation.slug] ? (
                  <img
                    src={nationImages[nation.slug]}
                    alt={`${nation.name} landscape`}
                    className="w-full h-full object-cover"
                    loading="lazy"
                  />
                ) : (
                  <div className={`w-full h-full flex items-center justify-center bg-gradient-to-br ${nation.color}`}>
                    {nation.icon}
                  </div>
                )}
              </div>

              <div className="flex items-center gap-4 mb-4">
                <div className={`p-4 rounded-xl bg-gradient-to-br ${nation.color}`}>
                  {nation.icon}
                </div>
                <h2 className="text-3xl font-bold text-white">{nation.name}</h2>
              </div>
              
              <p className="text-gray-300 mb-6">{nation.description}</p>
              
              <div className="mb-6">
                <h3 className="text-sm font-semibold text-purple-300 mb-2">KEY LOCATIONS:</h3>
                <div className="flex flex-wrap gap-2">
                  {nation.cities.map((city) => (
                    <span key={city} className="px-3 py-1 bg-purple-600/20 text-purple-300 rounded-full text-xs">
                      {city}
                    </span>
                  ))}
                </div>
              </div>
              
              <Link to={`/nations/${nation.slug}/cities`}>
                <Button className={`w-full bg-gradient-to-r ${nation.color}`} data-testid={`explore-${nation.slug}-btn`}>
                  Explore {nation.name} →
                </Button>
              </Link>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default Nations;
