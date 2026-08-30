import React, { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import AnimatedBackground from '../components/AnimatedBackground';
import { Button } from '../components/ui/button';
import { Volume2, VolumeX } from 'lucide-react';

const HERO_VIDEO_SRC = '/delarom-hero-loop.mp4';

const LandingPage = () => {
  const videoRef = useRef(null);
  const [muted, setMuted] = useState(true);
  const [videoFailed, setVideoFailed] = useState(false);

  // Browsers block autoplay WITH sound until the user interacts. We autoplay
  // muted (so the loop always shows), then unmute on the first user gesture
  // anywhere on the page so the homepage audio kicks in naturally.
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
    <div className="min-h-screen relative flex flex-col items-center justify-center overflow-hidden">
      <AnimatedBackground />

      <div className="relative z-10 w-full px-4 py-12 flex flex-col items-center justify-center">
        {/* Hero logo — seamless looping video with audio */}
        <div className="relative mb-10 w-full max-w-3xl" data-testid="hero-video-wrap">
          {!videoFailed ? (
            <>
              <video
                ref={videoRef}
                src={HERO_VIDEO_SRC}
                autoPlay
                loop
                muted
                playsInline
                onError={() => setVideoFailed(true)}
                data-testid="hero-video"
                className="w-full h-auto max-h-[70vh] object-contain rounded-2xl shadow-[0_0_80px_-15px_rgba(168,85,247,0.55)] mx-auto"
              />
              <button
                type="button"
                onClick={toggleMute}
                aria-label={muted ? 'Unmute' : 'Mute'}
                data-testid="hero-sound-toggle"
                className="absolute bottom-4 right-4 z-20 flex items-center justify-center w-11 h-11 rounded-full bg-black/50 backdrop-blur-md border border-purple-400/40 text-purple-100 hover:bg-black/70 hover:border-purple-300/70 transition-colors"
              >
                {muted ? <VolumeX className="w-5 h-5" /> : <Volume2 className="w-5 h-5" />}
              </button>
            </>
          ) : (
            <h1
              className="text-6xl sm:text-7xl font-bold text-center text-transparent bg-clip-text bg-gradient-to-r from-purple-400 via-pink-500 to-blue-500"
              data-testid="landing-title-fallback"
            >
              Continents of Delarom
            </h1>
          )}
        </div>

        {/* Actions */}
        <div className="flex flex-col sm:flex-row gap-4 justify-center items-center" data-testid="cta-buttons">
          <Link to="/register">
            <Button
              size="lg"
              className="bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-lg px-8 py-6"
              data-testid="begin-journey-btn"
            >
              🌟 Begin Your Journey
            </Button>
          </Link>
          <Link to="/login">
            <Button
              size="lg"
              variant="outline"
              className="border-purple-500/50 text-lg px-8 py-6"
              data-testid="return-realm-btn"
            >
              ⚔️ Return to Realm
            </Button>
          </Link>
        </div>
      </div>
    </div>
  );
};

export default LandingPage;
