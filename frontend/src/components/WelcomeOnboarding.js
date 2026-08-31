import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Sparkles, UserPlus, Map, Sword, Scroll, Flag, Sun,
  X, ChevronRight, ChevronLeft,
} from 'lucide-react';
import { Button } from './ui/button';

// Compact realm previews (mirrors the canon on the Nations map).
const NATIONS = [
  { name: 'Ammeonon', slug: 'ammeonon', emblem: '/emblems/ammeonon.png', race: 'Humans', accent: '#4ade80', blurb: 'The Northern Kingdom of Humans under the Vritra Clan — rolling hills, ancient forests, and bustling trade roads.' },
  { name: 'Selindori', slug: 'selindori', emblem: '/emblems/selindori.png', race: 'Elves', accent: '#60a5fa', blurb: 'Kingdom of the First Elves — crystal spires, deep magic, and the radiant city of Yillhone.' },
  { name: 'Dhor-Kuldor', slug: 'dhor-kuldor', emblem: '/emblems/dhor-kuldor.png', race: 'Dwarves', accent: '#a78bfa', blurb: 'The ancient Dwarven mountain kingdom — 8,000 years of civilisation carved into the peaks.' },
  { name: 'Aigraels', slug: 'aigraels', emblem: '/emblems/aigraels.png', race: 'Mixed', accent: '#f97316', blurb: 'A wartorn nation split between the Ardent Legion, the Forsaken Court, and the Elderborn Alliance.' },
  { name: 'The Veiled Realms', slug: 'veiled-realms', emblem: '/emblems/veiled-realms.png', race: 'Ancient Elves', accent: '#ec4899', blurb: 'Hidden kingdoms behind barrier magic — home to Moon, Shadow, and Crystal Elves.' },
];

const FIRST_STEPS = [
  { icon: Sword, label: 'Roleplay a scene', desc: 'Step into a living location and write your first action.', path: '/nations' },
  { icon: Scroll, label: 'Take a quest', desc: 'Browse the Quest Board and accept your first job.', path: '/quests' },
  { icon: Flag, label: 'Join a faction', desc: 'Pledge to a guild, court, or legion.', path: '/factions' },
  { icon: Sun, label: 'Pray to the Elder Gods', desc: 'Seek a blessing from Seren, Yros, Uesis, or Ehena.', path: '/prayers' },
];

const swap = {
  initial: { opacity: 0, x: 28 },
  animate: { opacity: 1, x: 0 },
  exit: { opacity: 0, x: -28 },
  transition: { duration: 0.28 },
};

const WelcomeOnboarding = ({ open, username, initialStep = 0, onClose, onStepChange }) => {
  const navigate = useNavigate();
  const [step, setStep] = useState(Math.min(Math.max(initialStep, 0), 3));
  const [peeked, setPeeked] = useState(null);

  const TOTAL = 4;

  const setStepAndPersist = (next) => {
    const clamped = Math.min(Math.max(next, 0), TOTAL - 1);
    setStep(clamped);
    onStepChange?.(clamped);
  };

  // Finish / dismiss the flow (marks it complete) then optionally navigate.
  const finish = (path) => {
    onClose?.();
    if (path) navigate(path);
  };

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="fixed inset-0 z-50 flex items-center justify-center p-4"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          data-testid="welcome-onboarding"
        >
          <div className="absolute inset-0 bg-black/75 backdrop-blur-sm" />
          <motion.div
            className="relative z-10 w-full max-w-2xl glass-dark border border-purple-500/40 rounded-2xl p-7 sm:p-9 max-h-[90vh] overflow-y-auto"
            initial={{ scale: 0.92, y: 24, opacity: 0 }}
            animate={{ scale: 1, y: 0, opacity: 1 }}
            exit={{ scale: 0.92, opacity: 0 }}
            transition={{ type: 'spring', damping: 24 }}
          >
            <button
              onClick={() => finish()}
              className="absolute top-4 right-4 text-gray-400 hover:text-white transition-colors"
              data-testid="welcome-skip-btn"
              aria-label="Skip onboarding"
            >
              <X className="w-5 h-5" />
            </button>

            {/* Progress dots */}
            <div className="flex items-center justify-center gap-2 mb-6" data-testid="welcome-progress">
              {Array.from({ length: TOTAL }).map((_, i) => (
                <span
                  key={i}
                  className={`h-1.5 rounded-full transition-all duration-300 ${
                    i === step ? 'w-8 bg-purple-400' : i < step ? 'w-3 bg-purple-600/70' : 'w-3 bg-white/15'
                  }`}
                />
              ))}
            </div>

            <div className="min-h-[340px]">
              <AnimatePresence mode="wait">
                {/* STEP 0 — Welcome */}
                {step === 0 && (
                  <motion.div key="s0" {...swap} className="text-center" data-testid="welcome-step-0">
                    <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-gradient-to-br from-purple-500/30 to-pink-500/30 border border-purple-400/40 mb-5">
                      <Sparkles className="w-8 h-8 text-yellow-300" />
                    </div>
                    <h2 className="text-3xl sm:text-4xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-pink-500">
                      Welcome{username ? `, ${username}` : ''}!
                    </h2>
                    <p className="text-purple-200/80 mt-2 italic text-sm">Where Legends Are Written in the Stars</p>
                    <p className="text-gray-300 mt-5 max-w-lg mx-auto leading-relaxed">
                      Delarom is a living dark-fantasy world shaped entirely by the choices of its
                      people. Forge a hero, choose a realm, and write your story alongside an
                      AI-driven world that remembers what you do. Let's get you started — it takes
                      about a minute.
                    </p>
                  </motion.div>
                )}

                {/* STEP 1 — Forge your hero */}
                {step === 1 && (
                  <motion.div key="s1" {...swap} data-testid="welcome-step-1">
                    <div className="flex items-center gap-3 mb-4">
                      <div className="w-11 h-11 rounded-full bg-purple-500/20 border border-purple-400/40 flex items-center justify-center">
                        <UserPlus className="w-5 h-5 text-purple-300" />
                      </div>
                      <div>
                        <h2 className="text-2xl font-bold text-white">Forge your hero</h2>
                        <p className="text-sm text-gray-400">Step 1 of your legend</p>
                      </div>
                    </div>
                    <p className="text-gray-300 leading-relaxed mb-5">
                      Every story begins with a character. You'll choose a name, a race, and a class,
                      then spend attribute points and write the backstory and powers that make them
                      truly yours. Races and classes are freeform — play a moon-elf assassin, a
                      dwarven runesmith, or something no one has seen before.
                    </p>
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-6">
                      {['Name & Race', 'Class & Powers', '60 Attribute Points', 'Backstory'].map((t) => (
                        <div key={t} className="glass rounded-lg px-3 py-2 text-center text-xs text-purple-200 border border-purple-500/20">
                          {t}
                        </div>
                      ))}
                    </div>
                    <Button
                      onClick={() => finish('/characters')}
                      className="w-full bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700"
                      data-testid="welcome-cta-character"
                    >
                      Create My Character
                      <ChevronRight className="w-4 h-4 ml-1" />
                    </Button>
                  </motion.div>
                )}

                {/* STEP 2 — Choose your realm */}
                {step === 2 && (
                  <motion.div key="s2" {...swap} data-testid="welcome-step-2">
                    <div className="flex items-center gap-3 mb-4">
                      <div className="w-11 h-11 rounded-full bg-blue-500/20 border border-blue-400/40 flex items-center justify-center">
                        <Map className="w-5 h-5 text-blue-300" />
                      </div>
                      <div>
                        <h2 className="text-2xl font-bold text-white">Choose your realm</h2>
                        <p className="text-sm text-gray-400">Five nations await — tap one to peek at its lore</p>
                      </div>
                    </div>
                    <div className="space-y-2 mb-5">
                      {NATIONS.map((n) => (
                        <button
                          key={n.slug}
                          onClick={() => setPeeked(peeked === n.slug ? null : n.slug)}
                          className="w-full text-left glass rounded-xl p-3 flex items-center gap-3 border border-white/10 hover:border-white/25 transition-colors"
                          style={peeked === n.slug ? { borderColor: n.accent } : undefined}
                          data-testid={`welcome-nation-${n.slug}`}
                        >
                          <img src={n.emblem} alt={`${n.name} emblem`} className="w-11 h-11 object-contain shrink-0 drop-shadow" />
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                              <span className="font-semibold text-white">{n.name}</span>
                              <span className="text-[11px] px-1.5 py-0.5 rounded-full border" style={{ color: n.accent, borderColor: `${n.accent}66` }}>{n.race}</span>
                            </div>
                            <AnimatePresence initial={false}>
                              {peeked === n.slug && (
                                <motion.p
                                  initial={{ height: 0, opacity: 0 }}
                                  animate={{ height: 'auto', opacity: 1 }}
                                  exit={{ height: 0, opacity: 0 }}
                                  className="text-xs text-gray-400 leading-snug mt-1 overflow-hidden"
                                >
                                  {n.blurb}
                                </motion.p>
                              )}
                            </AnimatePresence>
                          </div>
                          <ChevronRight className={`w-4 h-4 text-gray-500 shrink-0 transition-transform ${peeked === n.slug ? 'rotate-90' : ''}`} />
                        </button>
                      ))}
                    </div>
                    <Button
                      onClick={() => finish('/nations')}
                      className="w-full bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-700 hover:to-cyan-700"
                      data-testid="welcome-cta-nation"
                    >
                      Explore the Living Map
                      <ChevronRight className="w-4 h-4 ml-1" />
                    </Button>
                  </motion.div>
                )}

                {/* STEP 3 — First steps */}
                {step === 3 && (
                  <motion.div key="s3" {...swap} data-testid="welcome-step-3">
                    <div className="flex items-center gap-3 mb-4">
                      <div className="w-11 h-11 rounded-full bg-yellow-500/20 border border-yellow-400/40 flex items-center justify-center">
                        <Sparkles className="w-5 h-5 text-yellow-300" />
                      </div>
                      <div>
                        <h2 className="text-2xl font-bold text-white">Your first steps</h2>
                        <p className="text-sm text-gray-400">A few ways to dive into Delarom</p>
                      </div>
                    </div>
                    <div className="space-y-2 mb-6">
                      {FIRST_STEPS.map((s) => {
                        const Icon = s.icon;
                        return (
                          <button
                            key={s.label}
                            onClick={() => finish(s.path)}
                            className="w-full text-left glass rounded-xl p-3 flex items-center gap-3 border border-white/10 hover:border-purple-400/40 transition-colors"
                            data-testid={`welcome-firststep-${s.path.replace('/', '')}`}
                          >
                            <div className="w-9 h-9 rounded-full bg-white/5 border border-white/15 flex items-center justify-center shrink-0">
                              <Icon className="w-4 h-4 text-purple-300" />
                            </div>
                            <div className="flex-1 min-w-0">
                              <div className="text-white font-medium text-sm">{s.label}</div>
                              <div className="text-xs text-gray-400 leading-snug">{s.desc}</div>
                            </div>
                            <ChevronRight className="w-4 h-4 text-gray-500 shrink-0" />
                          </button>
                        );
                      })}
                    </div>
                    <Button
                      onClick={() => finish()}
                      className="w-full bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700"
                      data-testid="welcome-cta-enter"
                    >
                      Enter Delarom
                    </Button>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            {/* Footer nav */}
            <div className="flex items-center justify-between mt-6 pt-4 border-t border-white/10">
              <button
                onClick={() => setStepAndPersist(step - 1)}
                disabled={step === 0}
                className={`flex items-center gap-1 text-sm ${step === 0 ? 'text-gray-600 cursor-not-allowed' : 'text-gray-300 hover:text-white'}`}
                data-testid="welcome-back-btn"
              >
                <ChevronLeft className="w-4 h-4" /> Back
              </button>

              {step < TOTAL - 1 ? (
                <Button
                  onClick={() => setStepAndPersist(step + 1)}
                  variant="outline"
                  className="border-purple-500/40 text-purple-200 hover:bg-purple-500/10"
                  data-testid="welcome-next-btn"
                >
                  Next <ChevronRight className="w-4 h-4 ml-1" />
                </Button>
              ) : (
                <button
                  onClick={() => finish()}
                  className="text-sm text-gray-400 hover:text-gray-200"
                  data-testid="welcome-later-btn"
                >
                  I'll explore on my own
                </button>
              )}
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

export default WelcomeOnboarding;
