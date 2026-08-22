import React, { useState, useRef, useEffect, useCallback } from 'react';
import AnimatedBackground from '../components/AnimatedBackground';
import Navbar from '../components/Navbar';
import { Feather, Newspaper, ScrollText, Wind, Skull, Music, Mail, Heart, ChevronLeft, ChevronRight } from 'lucide-react';

import QuillCofferFrontPage from '../components/quill/QuillCofferFrontPage';
import ChroniclePanel from './Chronicle';
import RumorsPanel from './Rumors';
import BountyBoard from './BountyBoard';
import MemorialPanel from './Memorial';
import BalladsPanel from './Ballads';
import LettersPanel from './Letters';
import BondsPanel from './Bonds';

const TABS = [
  { id: 'frontpage', label: 'Front Page', icon: Newspaper,  accent: 'text-amber-300',  sub: "today's print" },
  { id: 'chronicle', label: 'Chronicle',  icon: ScrollText, accent: 'text-amber-300',  sub: 'world events' },
  { id: 'rumors',    label: 'Rumors',     icon: Wind,       accent: 'text-purple-200', sub: 'tongues wag' },
  { id: 'bounties',  label: 'Bounties',   icon: Skull,      accent: 'text-rose-300',   sub: 'open warrants' },
  { id: 'memorial',  label: 'Memorial',   icon: Skull,      accent: 'text-gray-300',   sub: 'the fallen' },
  { id: 'ballads',   label: 'Ballads',    icon: Music,      accent: 'text-amber-200',  sub: 'songs of deeds' },
  { id: 'letters',   label: 'Letters',    icon: Mail,       accent: 'text-amber-300',  sub: 'sealed words' },
  { id: 'bonds',     label: 'Bonds',      icon: Heart,      accent: 'text-pink-300',   sub: 'oaths kept' },
];

const PANELS = {
  chronicle: ChroniclePanel,
  rumors:    RumorsPanel,
  bounties:  BountyBoard,
  memorial:  MemorialPanel,
  ballads:   BalladsPanel,
  letters:   LettersPanel,
  bonds:     BondsPanel,
};

const QuillAndCoffer = () => {
  const [activeId, setActiveId] = useState('frontpage');
  const tabBarRef = useRef(null);
  const [showLeftFade, setShowLeftFade] = useState(false);
  const [showRightFade, setShowRightFade] = useState(false);

  const active = TABS.find((t) => t.id === activeId) || TABS[0];

  const jumpToTab = useCallback((id) => {
    setActiveId(id);
  }, []);

  // Track horizontal scroll position to show/hide edge fade indicators on mobile.
  useEffect(() => {
    const el = tabBarRef.current;
    if (!el) return;
    const update = () => {
      setShowLeftFade(el.scrollLeft > 4);
      setShowRightFade(el.scrollLeft + el.clientWidth < el.scrollWidth - 4);
    };
    update();
    el.addEventListener('scroll', update, { passive: true });
    window.addEventListener('resize', update);
    return () => {
      el.removeEventListener('scroll', update);
      window.removeEventListener('resize', update);
    };
  }, []);

  // When active tab changes, ensure it's visible in the scroll strip on mobile.
  useEffect(() => {
    const el = tabBarRef.current;
    if (!el) return;
    const activeBtn = el.querySelector(`[data-tab-id="${activeId}"]`);
    if (activeBtn && activeBtn.scrollIntoView) {
      activeBtn.scrollIntoView({ behavior: 'smooth', inline: 'center', block: 'nearest' });
    }
  }, [activeId]);

  const scrollTabs = (dir) => {
    const el = tabBarRef.current;
    if (!el) return;
    el.scrollBy({ left: dir * 200, behavior: 'smooth' });
  };

  return (
    <div className="min-h-screen relative">
      <AnimatedBackground />
      <Navbar />

      <div className="relative z-10 container mx-auto px-4 pt-8 pb-4">
        {/* Page title — parchment-toned heading */}
        <header className="text-center mb-6" data-testid="quill-coffer-header">
          <div className="inline-flex items-center gap-3 mb-2">
            <Feather className="w-7 h-7 text-amber-300" />
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-amber-200 via-amber-300 to-amber-500 tracking-tight" style={{ fontFamily: 'Georgia, serif' }}>
              Quill &amp; Coffer
            </h1>
            <Feather className="w-7 h-7 text-amber-300 scale-x-[-1]" />
          </div>
          <p className="text-gray-400 italic text-sm max-w-2xl mx-auto">
            The realm's standing newspaper — chronicles, rumors, warrants, and oaths,
            all bound under one cover. What's printed here, the world reads.
          </p>
        </header>

        {/* Parchment scroll tab strip */}
        <div className="relative mb-2" data-testid="quill-coffer-tabbar">
          {/* Left edge fade + scroll button (mobile) */}
          {showLeftFade && (
            <button
              type="button"
              aria-label="Scroll tabs left"
              onClick={() => scrollTabs(-1)}
              className="absolute left-0 top-1/2 -translate-y-1/2 z-20 hidden sm:flex md:hidden items-center justify-center w-7 h-7 rounded-full bg-amber-900/80 border border-amber-600/60 text-amber-100 hover:bg-amber-800"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
          )}
          {showLeftFade && (
            <div className="pointer-events-none absolute left-0 top-0 bottom-0 w-8 bg-gradient-to-r from-gray-950/90 to-transparent z-10" />
          )}

          {/* Scrollable strip of parchment-pill tabs */}
          <div
            ref={tabBarRef}
            className="overflow-x-auto scrollbar-hide flex gap-2 py-2 px-1 snap-x snap-mandatory"
            style={{ scrollbarWidth: 'none' }}
          >
            <style>{`
              [data-testid="quill-coffer-tabbar"] > div::-webkit-scrollbar { display: none; }
            `}</style>
            {TABS.map((t) => {
              const Icon = t.icon;
              const isActive = t.id === activeId;
              return (
                <button
                  key={t.id}
                  type="button"
                  data-tab-id={t.id}
                  data-testid={`quill-tab-${t.id}`}
                  onClick={() => setActiveId(t.id)}
                  className={`
                    relative flex-shrink-0 snap-start
                    flex items-center gap-2 px-5 py-2.5 rounded-t-lg rounded-b-sm
                    border transition-all duration-200
                    ${isActive
                      ? 'bg-gradient-to-b from-amber-100/95 to-amber-50/90 border-amber-700/70 text-amber-950 shadow-lg shadow-amber-900/40 -translate-y-0.5'
                      : 'bg-gradient-to-b from-amber-950/60 to-stone-900/60 border-amber-700/30 text-amber-200/80 hover:text-amber-100 hover:border-amber-600/50'}
                  `}
                  style={isActive ? { fontFamily: 'Georgia, serif' } : undefined}
                >
                  <Icon className={`w-4 h-4 ${isActive ? 'text-amber-900' : ''}`} />
                  <span className="text-sm font-semibold tracking-wide">{t.label}</span>
                  {isActive && (
                    <span className="absolute -bottom-px left-0 right-0 h-0.5 bg-amber-100" />
                  )}
                </button>
              );
            })}
          </div>

          {/* Right edge fade + scroll button (mobile) */}
          {showRightFade && (
            <div className="pointer-events-none absolute right-0 top-0 bottom-0 w-8 bg-gradient-to-l from-gray-950/90 to-transparent z-10" />
          )}
          {showRightFade && (
            <button
              type="button"
              aria-label="Scroll tabs right"
              onClick={() => scrollTabs(1)}
              className="absolute right-0 top-1/2 -translate-y-1/2 z-20 hidden sm:flex md:hidden items-center justify-center w-7 h-7 rounded-full bg-amber-900/80 border border-amber-600/60 text-amber-100 hover:bg-amber-800"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          )}
        </div>

        {/* Subtitle for active tab */}
        <p className="text-center text-xs uppercase tracking-[0.3em] text-amber-300/60 mb-4" data-testid="quill-coffer-subtitle">
          {active.sub}
        </p>
      </div>

      {/* Active tab content — parchment-edged page */}
      <div className="relative z-10 pb-20" data-testid={`quill-panel-${activeId}`}>
        {activeId === 'frontpage' ? (
          <QuillCofferFrontPage onJumpToTab={jumpToTab} />
        ) : (
          (() => { const P = PANELS[activeId]; return P ? <P /> : null; })()
        )}
      </div>
    </div>
  );
};

export default QuillAndCoffer;
