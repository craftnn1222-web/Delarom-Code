import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import AnimatedBackground from '../components/AnimatedBackground';
import Navbar from '../components/Navbar';
import { MapPin, Castle, Mountain, Swords, Sparkles, Eye, X, ChevronRight, Compass } from 'lucide-react';
import { Button } from '../components/ui/button';

// Map image URL
const MAP_IMAGE_URL = "https://static.prod-images.emergentagent.com/jobs/a2050c21-a8da-4aba-9b1a-83d0b2bd384b/images/0c1b1c5396cb442ab41b1579925e8f2c24548dcdface9b2abb664d4517a1ad70.png";

// Nation data with map positions (percentages for responsive positioning)
const NATIONS = [
  {
    id: 'ammeonon',
    name: 'Ammeonon',
    slug: 'ammeonon',
    description: 'The Northern Kingdom of Humans, ruled by the mighty Vritra Clan. A land of rolling green hills, ancient forests, and bustling trade routes.',
    icon: Castle,
    color: '#4ade80',
    glowColor: 'rgba(74, 222, 128, 0.5)',
    position: { x: 38, y: 42 },
    labelPosition: { x: 38, y: 36 },
    features: ['6 Major Cities', '12 Towns', '72 Locations'],
    race: 'Humans',
    ruler: 'Vritra Clan'
  },
  {
    id: 'selindori',
    name: 'Selindori',
    slug: 'selindori',
    description: 'Kingdom of the First Elves, a mystical realm of crystal spires, ancient magic, and the legendary city of Yillhone.',
    icon: Sparkles,
    color: '#60a5fa',
    glowColor: 'rgba(96, 165, 250, 0.5)',
    position: { x: 52, y: 52 },
    labelPosition: { x: 52, y: 46 },
    features: ['21 Districts/Cities', '10 Towns', '84 Locations'],
    race: 'Elves',
    ruler: 'Elder Council'
  },
  {
    id: 'dhor-kuldor',
    name: 'Dhor-Kuldor',
    slug: 'dhor-kuldor',
    description: 'The ancient Dwarven Mountain Kingdom, home to 8000+ years of civilization carved into the very mountains themselves.',
    icon: Mountain,
    color: '#a78bfa',
    glowColor: 'rgba(167, 139, 250, 0.5)',
    position: { x: 68, y: 62 },
    labelPosition: { x: 68, y: 56 },
    features: ['8 Great Holds', '24 Cities', '307 Locations'],
    race: 'Dwarves',
    ruler: 'High King'
  },
  {
    id: 'aigraels',
    name: 'Aigraels',
    slug: 'aigraels',
    description: 'A wartorn nation divided by three factions: the Ardent Legion, the Forsaken Court, and the Elderborn Alliance.',
    icon: Swords,
    color: '#f97316',
    glowColor: 'rgba(249, 115, 22, 0.5)',
    position: { x: 52, y: 75 },
    labelPosition: { x: 52, y: 69 },
    features: ['4 Faction Cities', '17 Locations', 'Active Conflict'],
    race: 'Mixed',
    ruler: 'Contested'
  },
  {
    id: 'veiled-realms',
    name: 'The Veiled Realms',
    slug: 'veiled-realms',
    description: 'Hidden ancient kingdoms protected by powerful barrier magic. Home to Moon Elves, Shadow Elves, and Crystal Elves.',
    icon: Eye,
    color: '#ec4899',
    glowColor: 'rgba(236, 72, 153, 0.5)',
    position: { x: 28, y: 68 },
    labelPosition: { x: 28, y: 62 },
    features: ['3 Hidden Kingdoms', '18 Cities/Towns', '66 Locations'],
    race: 'Ancient Elves',
    ruler: 'Hidden Councils'
  }
];

// Landmark markers
const LANDMARKS = [
  { id: 'shaaldier', name: "Shaaldier's Pass", type: 'mountain', position: { x: 22, y: 18 }, description: 'Massive mountain range separating Ammeonon from the Northern Wastes' },
  { id: 'northern-wastes', name: 'Northern Wastes', type: 'wilderness', position: { x: 12, y: 8 }, description: 'Frozen tundra beyond the mountains, home to ancient terrors' },
  { id: 'yillhone', name: 'Yillhone', type: 'capital', position: { x: 52, y: 50 }, description: 'The Crystal City, capital of Selindori' },
];

const InteractiveMap = () => {
  const navigate = useNavigate();
  const mapRef = useRef(null);
  const containerRef = useRef(null);
  
  const [hoveredNation, setHoveredNation] = useState(null);
  const [selectedNation, setSelectedNation] = useState(null);
  const [revealedNations, setRevealedNations] = useState([]);
  const [mapLoaded, setMapLoaded] = useState(false);
  const [showIntro, setShowIntro] = useState(true);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });

  // Fog of war reveal animation
  useEffect(() => {
    if (mapLoaded && !showIntro) {
      const timer = setTimeout(() => {
        NATIONS.forEach((nation, index) => {
          setTimeout(() => {
            setRevealedNations(prev => [...prev, nation.id]);
          }, index * 400);
        });
      }, 500);
      return () => clearTimeout(timer);
    }
  }, [mapLoaded, showIntro]);

  // Handle mouse wheel zoom
  const handleWheel = useCallback((e) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? -0.1 : 0.1;
    setZoom(prev => Math.min(Math.max(prev + delta, 0.5), 3));
  }, []);

  // Pan handlers
  const handleMouseDown = (e) => {
    if (e.button === 0) {
      setIsDragging(true);
      setDragStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
    }
  };

  const handleMouseMove = (e) => {
    if (isDragging) {
      setPan({
        x: e.clientX - dragStart.x,
        y: e.clientY - dragStart.y
      });
    }
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  // Reset view
  const resetView = () => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
  };

  // Navigate to nation
  const handleNationClick = (nation) => {
    setSelectedNation(nation);
  };

  const goToNation = () => {
    if (selectedNation) {
      navigate(`/nations/${selectedNation.slug}/cities`);
    }
  };

  // Start exploring (dismiss intro)
  const startExploring = () => {
    setShowIntro(false);
  };

  return (
    <div className="min-h-screen relative overflow-hidden">
      <AnimatedBackground />
      <Navbar />
      
      {/* Intro Overlay */}
      <AnimatePresence>
        {showIntro && (
          <motion.div 
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/90"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <motion.div 
              className="text-center max-w-2xl px-6"
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ delay: 0.3 }}
            >
              <motion.div
                initial={{ y: -20, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                transition={{ delay: 0.5 }}
              >
                <Compass className="w-20 h-20 mx-auto mb-6 text-amber-400" />
              </motion.div>
              <motion.h1 
                className="text-5xl font-bold mb-4 text-transparent bg-clip-text bg-gradient-to-r from-amber-400 via-yellow-300 to-amber-400"
                initial={{ y: 20, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                transition={{ delay: 0.7 }}
              >
                The Continent of Tyrandria
              </motion.h1>
              <motion.p 
                className="text-gray-300 text-lg mb-8"
                initial={{ y: 20, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                transition={{ delay: 0.9 }}
              >
                A land of ancient magic, warring kingdoms, and untold mysteries. 
                Explore the nations, discover their secrets, and forge your own legend.
              </motion.p>
              <motion.div
                initial={{ y: 20, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                transition={{ delay: 1.1 }}
              >
                <Button 
                  onClick={startExploring}
                  className="bg-gradient-to-r from-amber-600 to-yellow-600 hover:from-amber-500 hover:to-yellow-500 text-white px-8 py-6 text-lg font-semibold"
                  data-testid="start-exploring-btn"
                >
                  Begin Your Journey
                  <ChevronRight className="ml-2 w-5 h-5" />
                </Button>
              </motion.div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Map Container */}
      <div 
        ref={containerRef}
        className="relative z-10 w-full h-[calc(100vh-64px)] mt-16 overflow-hidden cursor-grab active:cursor-grabbing"
        onWheel={handleWheel}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
      >
        {/* Map Controls */}
        <div className="absolute top-4 right-4 z-30 flex flex-col gap-2">
          <Button 
            onClick={() => setZoom(prev => Math.min(prev + 0.2, 3))}
            className="bg-black/60 hover:bg-black/80 w-10 h-10 p-0"
            data-testid="zoom-in-btn"
          >
            +
          </Button>
          <Button 
            onClick={() => setZoom(prev => Math.max(prev - 0.2, 0.5))}
            className="bg-black/60 hover:bg-black/80 w-10 h-10 p-0"
            data-testid="zoom-out-btn"
          >
            -
          </Button>
          <Button 
            onClick={resetView}
            className="bg-black/60 hover:bg-black/80 w-10 h-10 p-0"
            title="Reset View"
            data-testid="reset-view-btn"
          >
            <Compass className="w-4 h-4" />
          </Button>
        </div>

        {/* Zoom Level Indicator */}
        <div className="absolute top-4 left-4 z-30 bg-black/60 px-3 py-1 rounded-full text-sm text-gray-300">
          {Math.round(zoom * 100)}%
        </div>

        {/* Map Image with Transform */}
        <motion.div
          ref={mapRef}
          className="relative w-full h-full"
          style={{
            transform: `scale(${zoom}) translate(${pan.x / zoom}px, ${pan.y / zoom}px)`,
            transformOrigin: 'center center'
          }}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 1 }}
        >
          {/* Background Map Image */}
          <img 
            src={MAP_IMAGE_URL}
            alt="Map of Tyrandria"
            className="w-full h-full object-contain"
            onLoad={() => setMapLoaded(true)}
            draggable={false}
          />

          {/* Fog of War Overlay */}
          {!showIntro && (
            <div className="absolute inset-0 pointer-events-none">
              <svg className="w-full h-full" viewBox="0 0 100 100" preserveAspectRatio="none">
                <defs>
                  {NATIONS.map(nation => (
                    <radialGradient key={`gradient-${nation.id}`} id={`fog-${nation.id}`}>
                      <stop offset="0%" stopColor="transparent" />
                      <stop offset="70%" stopColor="transparent" />
                      <stop offset="100%" stopColor="rgba(0,0,0,0.7)" />
                    </radialGradient>
                  ))}
                </defs>
              </svg>
            </div>
          )}

          {/* Nation Markers */}
          {!showIntro && NATIONS.map((nation) => {
            const isRevealed = revealedNations.includes(nation.id);
            const isHovered = hoveredNation === nation.id;
            const Icon = nation.icon;

            return (
              <motion.div
                key={nation.id}
                className="absolute cursor-pointer"
                style={{
                  left: `${nation.position.x}%`,
                  top: `${nation.position.y}%`,
                  transform: 'translate(-50%, -50%)'
                }}
                initial={{ opacity: 0, scale: 0 }}
                animate={{ 
                  opacity: isRevealed ? 1 : 0, 
                  scale: isRevealed ? 1 : 0 
                }}
                transition={{ 
                  duration: 0.5,
                  type: 'spring',
                  stiffness: 200
                }}
                onMouseEnter={() => setHoveredNation(nation.id)}
                onMouseLeave={() => setHoveredNation(null)}
                onClick={() => handleNationClick(nation)}
                data-testid={`nation-marker-${nation.id}`}
              >
                {/* Glow Effect */}
                <motion.div
                  className="absolute inset-0 rounded-full blur-xl"
                  style={{ backgroundColor: nation.glowColor }}
                  animate={{
                    scale: isHovered ? 2 : 1.5,
                    opacity: isHovered ? 0.8 : 0.4
                  }}
                  transition={{ duration: 0.3 }}
                />
                
                {/* Marker Icon */}
                <motion.div
                  className="relative z-10 w-12 h-12 rounded-full flex items-center justify-center border-2"
                  style={{ 
                    backgroundColor: `${nation.color}20`,
                    borderColor: nation.color
                  }}
                  animate={{
                    scale: isHovered ? 1.2 : 1,
                    boxShadow: isHovered 
                      ? `0 0 30px ${nation.glowColor}` 
                      : `0 0 10px ${nation.glowColor}`
                  }}
                  whileHover={{ scale: 1.2 }}
                  whileTap={{ scale: 0.95 }}
                >
                  <Icon className="w-6 h-6" style={{ color: nation.color }} />
                </motion.div>

                {/* Nation Label */}
                <motion.div
                  className="absolute whitespace-nowrap text-center"
                  style={{
                    top: '100%',
                    left: '50%',
                    transform: 'translateX(-50%)',
                    marginTop: '8px'
                  }}
                  animate={{
                    opacity: isHovered ? 1 : 0.8,
                    y: isHovered ? -2 : 0
                  }}
                >
                  <span 
                    className="font-bold text-sm px-2 py-1 rounded"
                    style={{ 
                      color: nation.color,
                      textShadow: '0 0 10px rgba(0,0,0,0.8), 0 0 20px rgba(0,0,0,0.6)'
                    }}
                  >
                    {nation.name}
                  </span>
                </motion.div>

                {/* Pulse Ring Animation */}
                <motion.div
                  className="absolute inset-0 rounded-full border-2"
                  style={{ borderColor: nation.color }}
                  animate={{
                    scale: [1, 2, 2],
                    opacity: [0.6, 0, 0]
                  }}
                  transition={{
                    duration: 2,
                    repeat: Infinity,
                    repeatDelay: 1
                  }}
                />
              </motion.div>
            );
          })}

          {/* Landmark Markers */}
          {!showIntro && LANDMARKS.map((landmark) => (
            <motion.div
              key={landmark.id}
              className="absolute"
              style={{
                left: `${landmark.position.x}%`,
                top: `${landmark.position.y}%`,
                transform: 'translate(-50%, -50%)'
              }}
              initial={{ opacity: 0 }}
              animate={{ opacity: revealedNations.length >= 3 ? 0.7 : 0 }}
              transition={{ duration: 0.5, delay: 2 }}
            >
              <div className="relative group">
                <MapPin className="w-4 h-4 text-amber-400" />
                <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
                  <div className="bg-black/90 text-white text-xs px-2 py-1 rounded whitespace-nowrap">
                    {landmark.name}
                  </div>
                </div>
              </div>
            </motion.div>
          ))}
        </motion.div>
      </div>

      {/* Nation Info Panel */}
      <AnimatePresence>
        {selectedNation && (
          <motion.div
            className="fixed right-0 top-16 bottom-0 w-96 bg-gray-900/95 border-l border-purple-500/30 z-40 overflow-y-auto"
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 25 }}
          >
            <div className="p-6">
              {/* Close Button */}
              <button
                onClick={() => setSelectedNation(null)}
                className="absolute top-4 right-4 text-gray-400 hover:text-white"
                data-testid="close-panel-btn"
              >
                <X className="w-6 h-6" />
              </button>

              {/* Nation Header */}
              <div className="mb-6">
                <div 
                  className="w-16 h-16 rounded-full flex items-center justify-center mb-4"
                  style={{ 
                    backgroundColor: `${selectedNation.color}20`,
                    border: `2px solid ${selectedNation.color}`
                  }}
                >
                  <selectedNation.icon className="w-8 h-8" style={{ color: selectedNation.color }} />
                </div>
                <h2 
                  className="text-3xl font-bold mb-2"
                  style={{ color: selectedNation.color }}
                >
                  {selectedNation.name}
                </h2>
                <p className="text-gray-400">{selectedNation.description}</p>
              </div>

              {/* Nation Stats */}
              <div className="space-y-4 mb-6">
                <div className="glass p-4 rounded-lg">
                  <h3 className="text-sm text-gray-400 mb-2">Dominant Race</h3>
                  <p className="text-white font-semibold">{selectedNation.race}</p>
                </div>
                <div className="glass p-4 rounded-lg">
                  <h3 className="text-sm text-gray-400 mb-2">Ruling Power</h3>
                  <p className="text-white font-semibold">{selectedNation.ruler}</p>
                </div>
                <div className="glass p-4 rounded-lg">
                  <h3 className="text-sm text-gray-400 mb-2">Features</h3>
                  <ul className="space-y-1">
                    {selectedNation.features.map((feature) => (
                      <li key={feature} className="text-white flex items-center gap-2">
                        <span style={{ color: selectedNation.color }}>•</span>
                        {feature}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>

              {/* Action Button */}
              <Button
                onClick={goToNation}
                className="w-full py-6 text-lg font-semibold"
                style={{ 
                  background: `linear-gradient(135deg, ${selectedNation.color}, ${selectedNation.color}88)` 
                }}
                data-testid="explore-nation-btn"
              >
                Explore {selectedNation.name}
                <ChevronRight className="ml-2 w-5 h-5" />
              </Button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Bottom Legend */}
      {!showIntro && (
        <motion.div 
          className="fixed bottom-4 left-1/2 transform -translate-x-1/2 z-30"
          initial={{ y: 50, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 3 }}
        >
          <div className="glass-dark px-6 py-3 rounded-full flex items-center gap-6">
            <span className="text-gray-400 text-sm">Click a nation to explore</span>
            <div className="h-4 w-px bg-gray-600" />
            <span className="text-gray-400 text-sm">Scroll to zoom • Drag to pan</span>
          </div>
        </motion.div>
      )}
    </div>
  );
};

export default InteractiveMap;
