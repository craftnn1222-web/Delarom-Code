import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import AnimatedBackground from '../components/AnimatedBackground';
import Navbar from '../components/Navbar';
import { MapPin, Castle, Mountain, Swords, Sparkles, Eye, X, ChevronRight, Compass } from 'lucide-react';
import { Button } from '../components/ui/button';
import './mapEffects.css';

// Map image (bundled in /public for production reliability)
const MAP_IMAGE_URL = "/tyrandria-map.png";

// Nation data with map positions (percentages for responsive positioning)
const NATIONS = [
  {
    id: 'ammeonon',
    name: 'Ammeonon',
    slug: 'ammeonon',
    emblem: '/emblems/ammeonon.png',
    cinematic: 'https://customer-assets-7cd3h4nn.emergentagent.net/wingman/1fc0f0d8-b8b5-4b5b-9e04-048953a767c4/attachments/71d1c58725d24b3e825c10f777ef4eba_ammeonon_purged.mp4',
    description: 'The Northern Kingdom of Humans, ruled by the mighty Vritra Clan. A land of rolling green hills, ancient forests, and bustling trade routes.',
    icon: Castle,
    color: '#4ade80',
    glowColor: 'rgba(74, 222, 128, 0.5)',
    position: { x: 31, y: 50 },
    labelPosition: { x: 31, y: 43 },
    features: ['6 Major Cities', '12 Towns', '72 Locations'],
    race: 'Humans',
    ruler: 'Vritra Clan'
  },
  {
    id: 'selindori',
    name: 'Selindori',
    slug: 'selindori',
    emblem: '/emblems/selindori.png',
    cinematic: 'https://customer-assets-7cd3h4nn.emergentagent.net/wingman/1fc0f0d8-b8b5-4b5b-9e04-048953a767c4/attachments/a79e10fd114a456cabd6b8ecdd31d7a7_selindori_purged.mp4',
    description: 'Kingdom of the First Elves, a mystical realm of crystal spires, ancient magic, and the legendary city of Yillhone.',
    icon: Sparkles,
    color: '#60a5fa',
    glowColor: 'rgba(96, 165, 250, 0.5)',
    position: { x: 58, y: 47 },
    labelPosition: { x: 58, y: 40 },
    features: ['21 Districts/Cities', '10 Towns', '84 Locations'],
    race: 'Elves',
    ruler: 'Elder Council'
  },
  {
    id: 'dhor-kuldor',
    name: 'Dhor-Kuldor',
    slug: 'dhor-kuldor',
    emblem: '/emblems/dhor-kuldor.png',
    cinematic: 'https://customer-assets-7cd3h4nn.emergentagent.net/wingman/1fc0f0d8-b8b5-4b5b-9e04-048953a767c4/attachments/0725e79d77614bbda679e69c0b28c398_dhor_kuldor_purged.mp4',
    description: 'The ancient Dwarven Mountain Kingdom, home to 8000+ years of civilization carved into the very mountains themselves.',
    icon: Mountain,
    color: '#a78bfa',
    glowColor: 'rgba(167, 139, 250, 0.5)',
    position: { x: 78, y: 58 },
    labelPosition: { x: 78, y: 52 },
    features: ['8 Great Holds', '24 Cities', '307 Locations'],
    race: 'Dwarves',
    ruler: 'High King'
  },
  {
    id: 'aigraels',
    name: 'Aigraels',
    slug: 'aigraels',
    emblem: '/emblems/aigraels.png',
    cinematic: 'https://customer-assets-7cd3h4nn.emergentagent.net/wingman/1fc0f0d8-b8b5-4b5b-9e04-048953a767c4/attachments/464d1a7ca6c44df486409cfcbe2c075c_aigraels_purged.mp4',
    description: 'A wartorn nation divided by three factions: the Ardent Legion, the Forsaken Court, and the Elderborn Alliance.',
    icon: Swords,
    color: '#f97316',
    glowColor: 'rgba(249, 115, 22, 0.5)',
    position: { x: 57, y: 80 },
    labelPosition: { x: 57, y: 74 },
    features: ['4 Faction Cities', '17 Locations', 'Active Conflict'],
    race: 'Mixed',
    ruler: 'Contested'
  },
  {
    id: 'veiled-realms',
    name: 'The Veiled Realms',
    slug: 'veiled-realms',
    emblem: '/emblems/veiled-realms.png',
    cinematic: null,
    description: 'Hidden ancient kingdoms protected by powerful barrier magic. Home to Moon Elves, Shadow Elves, and Crystal Elves.',
    icon: Eye,
    color: '#ec4899',
    glowColor: 'rgba(236, 72, 153, 0.5)',
    position: { x: 66, y: 22 },
    labelPosition: { x: 66, y: 16 },
    features: ['3 Hidden Kingdoms', '18 Cities/Towns', '66 Locations'],
    race: 'Ancient Elves',
    ruler: 'Hidden Councils'
  }
];

// Landmark markers
const LANDMARKS = [
  { id: 'shaaldier', name: "Shaaldieer's Pass", subtitle: 'The Sleeping Zenith Emperor', type: 'mountain', position: { x: 24, y: 23 }, description: "Shaaldieer's Pass is a mountain range that spans the breadth of the northern part of Ammeonon, separating Ammeonon from the Northern Wastes. Legend has it that Shaaldieer's Pass is the body of a dragon \u2014 one of the Epochal Six: a Zenith Emperor whose body and power can shake the very foundations of the world. There are six such powers. In the year 215 A.E., the Epochal Six are separated by oceans, each continent being home to one\u2026 as well as the ocean housing one. Due to this, Shaaldieer is believed to be a legend, a myth, a story told to scare children into behaving. Little do they know, he is very real, and very much alive. Merely\u2026 sleeping." },
  { id: 'northern-wastes', name: 'Northern Wastes', subtitle: 'Realm of Eternal Frost', type: 'wilderness', position: { x: 15, y: 9 }, description: 'A frozen tundra beyond the mountains where aurora light dances over endless ice, and ancient terrors are said to slumber beneath the frost.' },
  { id: 'wondfaln', name: 'Wondfaln Deobono Das', subtitle: 'The Spine of Tyrandria', type: 'mountain', position: { x: 51, y: 24 }, description: 'The towering mountain range that forms the backbone of the realm, dividing north from south with jagged, cloud-wreathed peaks.' },
  { id: 'noritorn', name: 'Noritorn', subtitle: 'The Verdant North', type: 'forest', position: { x: 26, y: 40 }, description: 'Rolling green wilds and old-growth forest north of Ammeonon, thick with game, hidden groves, and quiet woodland roads.' },
  { id: 'elon-forest', name: 'Elon Forest Farms', subtitle: 'The Emerald Heart', type: 'forest', position: { x: 69, y: 27 }, description: 'The lush farmlands and deep forest at the realm\u2019s green heart, feeding the eastern kingdoms.' },
  { id: 'wrare-seacenes', name: 'Wrare Seacenes', subtitle: 'Waters of Mystery', type: 'sea', position: { x: 18, y: 66 }, description: 'Uncharted western seas said to hide sunken wonders, sea-beasts, and the wrecks of ships that never returned.' },
  { id: 'yillhone', name: 'Yillhone', subtitle: 'City of Crystal and Light', type: 'capital', position: { x: 58, y: 44 }, description: 'The radiant Crystal City, capital of Selindori, where spires of living crystal channel the realm\u2019s deepest magic.' },
];

const InteractiveMap = () => {
  const navigate = useNavigate();
  const mapRef = useRef(null);
  const containerRef = useRef(null);
  
  const [hoveredNation, setHoveredNation] = useState(null);
  const [cinematicNation, setCinematicNation] = useState(null);
  const cinematicRef = useRef(null);
  const [selectedLandmark, setSelectedLandmark] = useState(null);
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

  // Click a nation → play its cinematic, then head to the city chooser.
  const handleNationClick = (nation) => {
    setHoveredNation(null);
    if (nation.cinematic) {
      setCinematicNation(nation);
    } else {
      // Veiled Realms has no clip (it is part of Selindori) → go straight in.
      navigate(`/nations/${nation.slug}/cities`);
    }
  };

  const finishCinematic = () => {
    if (cinematicNation) {
      navigate(`/nations/${cinematicNation.slug}/cities`);
      setCinematicNation(null);
    }
  };

  // Autoplay the cinematic with sound (the click is a user gesture); fall back
  // to muted if the browser still blocks it.
  useEffect(() => {
    if (!cinematicNation) return;
    const v = cinematicRef.current;
    if (!v) return;
    v.muted = false;
    const p = v.play();
    if (p && typeof p.catch === 'function') {
      p.catch(() => { v.muted = true; v.play().catch(() => {}); });
    }
  }, [cinematicNation]);

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
        className="relative z-10 w-full h-[calc(100vh-64px)] mt-16 overflow-hidden cursor-grab active:cursor-grabbing flex items-center justify-center"
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
          className="relative h-full max-w-full aspect-[3/2]"
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

          {/* Ambient region effects — ley-lines, Selindori pulse, Dhor-Kuldor smoke, Northern Wastes fog */}
          <div className="map-fx-root" data-testid="map-ambient-effects" aria-hidden="true">
            <svg className="map-fx-leylines" viewBox="0 0 150 100" preserveAspectRatio="none" data-testid="fx-leylines">
              <line className="ley-line" x1="87" y1="61" x2="46.5" y2="50" />
              <line className="ley-line" x1="87" y1="61" x2="117" y2="58" />
              <line className="ley-line" x1="87" y1="61" x2="85.5" y2="80" />
              <line className="ley-line" x1="87" y1="61" x2="99" y2="22" />
              <line className="ley-line" x1="87" y1="61" x2="22.5" y2="9" />
              <line className="ley-line" x1="87" y1="61" x2="87" y2="47" />
            </svg>
            <div className="map-fx-el map-fx-selindori" data-testid="fx-selindori-pulse" />
            <div className="map-fx-el map-fx-volcano" data-testid="fx-dhorkuldor-smoke">
              <div className="map-fx-smoke" />
              <div className="map-fx-smoke" />
              <div className="map-fx-smoke" />
              <div className="map-fx-smoke" />
              <div className="map-fx-ember" />
            </div>
            <div className="map-fx-el map-fx-fog-region" data-testid="fx-northern-fog">
              <div className="map-fx-fog" />
              <div className="map-fx-fog" />
              <div className="map-fx-fog" />
              <div className="map-fx-fog" />
            </div>
          </div>

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
                
                {/* Marker Emblem */}
                <motion.div
                  className="relative z-10 w-16 h-16 flex items-center justify-center"
                  animate={{
                    scale: isHovered ? 1.2 : 1,
                    filter: isHovered
                      ? `drop-shadow(0 0 16px ${nation.glowColor})`
                      : `drop-shadow(0 0 8px ${nation.glowColor})`
                  }}
                  whileHover={{ scale: 1.2 }}
                  whileTap={{ scale: 0.95 }}
                >
                  <img
                    src={nation.emblem}
                    alt={`${nation.name} emblem`}
                    className="w-full h-full object-contain drop-shadow-[0_2px_6px_rgba(0,0,0,0.7)]"
                    draggable={false}
                  />
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

          {/* Landmark Markers (clickable lore) */}
          {!showIntro && LANDMARKS.map((landmark) => (
            <motion.button
              key={landmark.id}
              type="button"
              className="absolute cursor-pointer"
              style={{
                left: `${landmark.position.x}%`,
                top: `${landmark.position.y}%`,
                transform: 'translate(-50%, -50%)'
              }}
              initial={{ opacity: 0 }}
              animate={{ opacity: revealedNations.length >= 3 ? 1 : 0 }}
              transition={{ duration: 0.5, delay: 2 }}
              onMouseDown={(e) => e.stopPropagation()}
              onClick={(e) => { e.stopPropagation(); setSelectedLandmark(landmark); }}
              data-testid={`landmark-marker-${landmark.id}`}
            >
              <div className="relative group flex items-center justify-center">
                <span className="absolute w-6 h-6 rounded-full bg-amber-400/40 blur-md animate-pulse" />
                <MapPin className="relative w-5 h-5 text-amber-300 drop-shadow-[0_0_6px_rgba(251,191,36,0.95)]" />
                <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
                  <div className="bg-black/90 text-amber-200 text-xs px-2 py-1 rounded whitespace-nowrap border border-amber-500/40">
                    {landmark.name}
                  </div>
                </div>
              </div>
            </motion.button>
          ))}
        </motion.div>
      </div>

      {/* Nation Info Panel */}
      <AnimatePresence>
        {cinematicNation && (
          <motion.div
            className="fixed inset-0 z-50 bg-black flex items-center justify-center"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            data-testid="nation-cinematic"
          >
            <video
              ref={cinematicRef}
              src={cinematicNation.cinematic}
              autoPlay
              playsInline
              onEnded={finishCinematic}
              className="w-full h-full object-contain"
              data-testid="nation-cinematic-video"
            />
            <div
              className="absolute top-5 left-6 text-white/90 text-lg font-semibold tracking-wide drop-shadow"
              data-testid="cinematic-nation-name"
            >
              {cinematicNation.name}
            </div>
            <button
              onClick={finishCinematic}
              className="absolute top-5 right-6 flex items-center gap-2 px-5 py-2 rounded-full bg-white/10 hover:bg-white/20 border border-white/30 text-white backdrop-blur-md transition-colors"
              data-testid="skip-cinematic-btn"
            >
              Enter {cinematicNation.name}
              <ChevronRight className="w-5 h-5" />
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Landmark Lore Popup */}
      <AnimatePresence>
        {selectedLandmark && (
          <motion.div
            className="fixed inset-0 z-40 flex items-center justify-center p-4"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <div
              className="absolute inset-0 bg-black/60"
              onClick={() => setSelectedLandmark(null)}
              data-testid="landmark-backdrop"
            />
            <motion.div
              className="relative z-10 glass-dark border border-amber-500/40 rounded-2xl max-w-md w-full p-6 max-h-[80vh] overflow-y-auto"
              initial={{ scale: 0.85, y: 20, opacity: 0 }}
              animate={{ scale: 1, y: 0, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              transition={{ type: 'spring', damping: 22 }}
              data-testid="landmark-lore-popup"
            >
              <button
                onClick={() => setSelectedLandmark(null)}
                className="absolute top-3 right-3 text-gray-400 hover:text-white"
                data-testid="close-landmark-btn"
              >
                <X className="w-5 h-5" />
              </button>
              <div className="flex items-start gap-3 mb-4">
                <div className="w-11 h-11 rounded-full flex items-center justify-center bg-amber-400/15 border border-amber-400/50 shrink-0">
                  <MapPin className="w-5 h-5 text-amber-300" />
                </div>
                <div>
                  <h3 className="text-2xl font-bold text-amber-300 leading-tight">{selectedLandmark.name}</h3>
                  {selectedLandmark.subtitle && (
                    <p className="text-amber-200/70 text-sm italic">{selectedLandmark.subtitle}</p>
                  )}
                </div>
              </div>
              <p className="text-gray-300 leading-relaxed">{selectedLandmark.description}</p>
            </motion.div>
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
