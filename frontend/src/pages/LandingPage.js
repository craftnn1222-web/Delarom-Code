import React, { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import AnimatedBackground from '../components/AnimatedBackground';
import { Button } from '../components/ui/button';
import { Sparkles, Volume2, VolumeX } from 'lucide-react';

const HERO_VIDEO_SRC = '/delarom-hero-loop.mp4';

const LandingPage = () => {
  const videoRef = useRef(null);
  const [muted, setMuted] = useState(true);
  const [videoFailed, setVideoFailed] = useState(false);

  // Browsers block autoplay WITH sound until the user interacts. The background
  // video autoplays muted (so it always shows), then unmutes on the first user
  // gesture anywhere on the page so the homepage audio kicks in.
  useEffect(() => {
    const enableSound = () => {
      const v = videoRef.current;
      if (v) {
        v.muted = false;
        v.volume = 0.7;
        setMuted(false);
        v.play().catch(() => { /* autoplay guard */ });
      }
      window.removeEventListener('pointerdown', enableSound);
      window.removeEventListener('keydown', enableSound);
      window.removeEventListener('touchstart', enableSound);
    };
    window.addEventListener('pointerdown', enableSound, { once: true });
    window.addEventListener('keydown', enableSound, { once: true });
    window.addEventListener('touchstart', enableSound, { once: true });
    return () => {
      window.removeEventListener('pointerdown', enableSound);
      window.removeEventListener('keydown', enableSound);
      window.removeEventListener('touchstart', enableSound);
    };
  }, []);

  const toggleMute = (e) => {
    e.stopPropagation();
    const v = videoRef.current;
    if (!v) return;
    const next = !v.muted;
    v.muted = next;
    if (!next) {
      v.volume = 0.7;
      v.play().catch(() => { /* autoplay guard */ });
    }
    setMuted(next);
  };

  return (
    <div className="min-h-screen relative bg-[#0b0714]">
      {/* Full-bleed background: the seamless logo loop, covering the whole viewport.
          Falls back to the animated starfield if the clip can't play. */}
      {videoFailed ? (
        <AnimatedBackground />
      ) : (
        <>
          <video
            ref={videoRef}
            src={HERO_VIDEO_SRC}
            autoPlay
            loop
            muted
            playsInline
            onError={() => setVideoFailed(true)}
            data-testid="hero-bg-video"
            className="fixed inset-0 w-full h-full object-cover z-0"
          />
          {/* Darkening overlay so the foreground content stays readable. */}
          <div className="fixed inset-0 z-0 bg-gradient-to-b from-black/70 via-purple-950/50 to-black/80" />
          <button
            type="button"
            onClick={toggleMute}
            aria-label={muted ? 'Unmute' : 'Mute'}
            data-testid="hero-sound-toggle"
            className="fixed bottom-5 right-5 z-30 flex items-center justify-center w-11 h-11 rounded-full bg-black/50 backdrop-blur-md border border-purple-400/40 text-purple-100 hover:bg-black/70 hover:border-purple-300/70 transition-colors"
          >
            {muted ? <VolumeX className="w-5 h-5" /> : <Volume2 className="w-5 h-5" />}
          </button>
        </>
      )}

      <div className="relative z-10">
        {/* Top hero — tagline + buttons near the top so the "Continents of
            Delarom" logo in the background video is clearly visible below them
            on the first screen. */}
        <div className="min-h-screen flex flex-col items-center pt-12 px-4 text-center">
          <p className="text-2xl text-gray-200 mb-8 flex items-center justify-center gap-2 drop-shadow-lg">
            <Sparkles className="w-6 h-6 text-yellow-400" />
            Where Legends Are Written in the Stars
            <Sparkles className="w-6 h-6 text-yellow-400" />
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center" data-testid="cta-buttons">
            <Link to="/register">
              <Button size="lg" className="bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-lg px-8 py-6" data-testid="begin-journey-btn">
                🌟 Begin Your Journey
              </Button>
            </Link>
            <Link to="/login">
              <Button size="lg" variant="outline" className="border-purple-500/50 text-lg px-8 py-6" data-testid="return-realm-btn">
                ⚔️ Return to Realm
              </Button>
            </Link>
          </div>
        </div>

        <div className="container mx-auto px-4 pb-20">
          {/* World Description */}
          <div className="glass-dark p-8 rounded-2xl max-w-5xl mx-auto mb-16">
            <h2 className="text-3xl font-bold text-center mb-6 text-purple-300">The World Awaits</h2>
            <p className="text-gray-300 text-lg leading-relaxed text-center">
              In the year 215 A.E., the Continents of Delarom thrive under the watchful gaze of the Astral King. 
              From the frozen peaks of Frostpeak to the molten depths of Emberdeep, from the celestial cities of 
              Selindori to the bustling ports of Ammeonon—your story begins here.
            </p>
          </div>

          {/* Nations */}
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6 mb-16">
            <div className="glass p-6 rounded-xl hover:scale-105 transition-transform duration-300" data-testid="nation-ammeonon">
              <div className="text-4xl mb-3">⚔️</div>
              <h3 className="text-2xl font-bold mb-2 text-purple-300">Ammeonon</h3>
              <p className="text-gray-400">
                The human empire where peace and prosperity reign. Cities like Wymroost and Invrasil beckon adventurers.
              </p>
            </div>

            <div className="glass p-6 rounded-xl hover:scale-105 transition-transform duration-300" data-testid="nation-dhor-kuldor">
              <div className="text-4xl mb-3">⛰️</div>
              <h3 className="text-2xl font-bold mb-2 text-purple-300">Dhor-Kuldor</h3>
              <p className="text-gray-400">
                Eight dwarven holds carved into mountains, where forge-fires never die and honor runs deeper than stone.
              </p>
            </div>

            <div className="glass p-6 rounded-xl hover:scale-105 transition-transform duration-300" data-testid="nation-selindori">
              <div className="text-4xl mb-3">🌟</div>
              <h3 className="text-2xl font-bold mb-2 text-purple-300">Selindori</h3>
              <p className="text-gray-400">
                The elven kingdoms of magic and mystery, from Sun Elves to Shadow Elves, each with ancient secrets.
              </p>
            </div>

            <div className="glass p-6 rounded-xl hover:scale-105 transition-transform duration-300" data-testid="nation-aigraels">
              <div className="text-4xl mb-3">⚡</div>
              <h3 className="text-2xl font-bold mb-2 text-purple-300">Aigraels</h3>
              <p className="text-gray-400">
                A land of shifting power, where three factions vie for control and the throne changes hands like the wind.
              </p>
            </div>
          </div>

          {/* Features */}
          <div className="glass-dark p-8 rounded-2xl">
            <h2 className="text-3xl font-bold text-center mb-8 text-purple-300">Your Adventure Includes</h2>
            <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
              <div className="text-center" data-testid="feature-characters">
                <div className="text-5xl mb-3">📜</div>
                <h4 className="text-xl font-bold mb-2 text-white">Create Your Legend</h4>
                <p className="text-gray-400">Craft detailed character bios with rich backstories, powers, and destinies.</p>
              </div>

              <div className="text-center" data-testid="feature-quests">
                <div className="text-5xl mb-3">🎯</div>
                <h4 className="text-xl font-bold mb-2 text-white">Quest & Earn</h4>
                <p className="text-gray-400">Accept quests from fellow adventurers and earn currency for your deeds.</p>
              </div>

              <div className="text-center" data-testid="feature-marketplace">
                <div className="text-5xl mb-3">🛍️</div>
                <h4 className="text-xl font-bold mb-2 text-white">Trade & Prosper</h4>
                <p className="text-gray-400">Open your own shop, sell items, and build your fortune in the marketplace.</p>
              </div>

              <div className="text-center" data-testid="feature-forums">
                <div className="text-5xl mb-3">💬</div>
                <h4 className="text-xl font-bold mb-2 text-white">Roleplay Together</h4>
                <p className="text-gray-400">Join forums, share stories, and shape the world alongside other heroes.</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LandingPage;
