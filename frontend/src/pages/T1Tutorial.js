import React, { useState } from 'react';
import Navbar from '../components/Navbar';
import AnimatedBackground from '../components/AnimatedBackground';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/card';
import T1PracticeArena from '../components/t1-tutorial/T1PracticeArena';
import {
  BookOpen,
  Swords,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  ChevronDown,
  ChevronUp,
  Scroll,
  Shield,
  Brain,
  Zap,
  Users,
  Target,
} from 'lucide-react';

const T1Tutorial = () => {
  const [activeSection, setActiveSection] = useState('intro');
  const [expandedExamples, setExpandedExamples] = useState({});

  const toggleExample = (id) => {
    setExpandedExamples((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const sections = [
    { id: 'intro', label: 'Introduction', icon: BookOpen },
    { id: 'autohit', label: 'Auto-Hitting', icon: Target },
    { id: 'puppet', label: 'Puppeteering', icon: Users },
    { id: 'meta', label: 'Metagaming', icon: Brain },
    { id: 'godmod', label: 'Godmodding', icon: Zap },
    { id: 'powerplay', label: 'Powerplaying', icon: Shield },
    { id: 'posts', label: 'Post Types', icon: Scroll },
    { id: 'practice', label: 'Practice Arena', icon: Swords },
  ];

  const renderSection = () => {
    switch (activeSection) {
      case 'intro':
        return (
          <div className="space-y-6">
            <h2 className="text-3xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-pink-500">
              Welcome to T1 Roleplay
            </h2>
            <p className="text-gray-300 text-lg leading-relaxed">
              T1 (Tier 1) roleplay is a turn-based, paragraph-style combat and storytelling system that emphasizes 
              <span className="text-yellow-400 font-semibold"> fairness, creativity, and player agency</span>. 
              It's the gold standard for text-based roleplay combat.
            </p>

            <Card className="glass border-purple-500/30">
              <CardContent className="p-6">
                <h3 className="text-xl font-bold text-purple-400 mb-4">Core Philosophy</h3>
                <ul className="space-y-3 text-gray-300">
                  <li className="flex items-start gap-3">
                    <CheckCircle2 className="w-5 h-5 text-green-400 mt-1 flex-shrink-0" />
                    <span><strong className="text-white">Attempt-Based Actions:</strong> All actions are written as attempts, never guaranteed successes</span>
                  </li>
                  <li className="flex items-start gap-3">
                    <CheckCircle2 className="w-5 h-5 text-green-400 mt-1 flex-shrink-0" />
                    <span><strong className="text-white">Player Agency:</strong> You control only YOUR character - never others</span>
                  </li>
                  <li className="flex items-start gap-3">
                    <CheckCircle2 className="w-5 h-5 text-green-400 mt-1 flex-shrink-0" />
                    <span><strong className="text-white">Fair Play:</strong> Actions must be logical, possible, and respect established abilities</span>
                  </li>
                  <li className="flex items-start gap-3">
                    <CheckCircle2 className="w-5 h-5 text-green-400 mt-1 flex-shrink-0" />
                    <span><strong className="text-white">Descriptive Writing:</strong> Use vivid, cinematic descriptions with sensory details</span>
                  </li>
                </ul>
              </CardContent>
            </Card>

            <Card className="glass border-yellow-500/30">
              <CardContent className="p-6">
                <h3 className="text-xl font-bold text-yellow-400 mb-4">The Golden Rule</h3>
                <p className="text-gray-300 text-lg italic">
                  "Write your actions as attempts, and let your opponent decide how their character responds."
                </p>
              </CardContent>
            </Card>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Card className="glass border-red-500/30">
                <CardHeader>
                  <CardTitle className="text-red-400 flex items-center gap-2">
                    <XCircle className="w-5 h-5" />
                    What T1 is NOT
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <ul className="space-y-2 text-gray-300 text-sm">
                    <li>• Assuming your attacks automatically hit</li>
                    <li>• Controlling other players' characters</li>
                    <li>• Using knowledge your character doesn't have</li>
                    <li>• Making your character invincible</li>
                    <li>• Adding powers mid-fight</li>
                  </ul>
                </CardContent>
              </Card>

              <Card className="glass border-green-500/30">
                <CardHeader>
                  <CardTitle className="text-green-400 flex items-center gap-2">
                    <CheckCircle2 className="w-5 h-5" />
                    What T1 IS
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <ul className="space-y-2 text-gray-300 text-sm">
                    <li>• Collaborative storytelling</li>
                    <li>• Fair, skill-based combat</li>
                    <li>• Respecting other writers</li>
                    <li>• Creative problem-solving</li>
                    <li>• Immersive roleplay</li>
                  </ul>
                </CardContent>
              </Card>
            </div>
          </div>
        );

      case 'autohit':
        return (
          <div className="space-y-6">
            <h2 className="text-3xl font-bold text-red-400 flex items-center gap-3">
              <Target className="w-8 h-8" />
              Auto-Hitting
            </h2>
            <p className="text-gray-300 text-lg">
              Auto-hitting is when you write an action that assumes it successfully affects another character 
              without giving them a chance to respond.
            </p>

            <Card className="glass border-red-500/50 bg-red-500/10">
              <CardHeader>
                <CardTitle className="text-red-400 flex items-center gap-2">
                  <XCircle className="w-5 h-5" />
                  BAD Examples (Auto-Hits)
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="p-4 bg-red-900/30 rounded-lg border border-red-500/30">
                  <p className="text-red-300 font-mono text-sm">
                    "I swing my sword and slice open his chest, causing him to stumble backward in pain."
                  </p>
                  <p className="text-gray-400 text-sm mt-2">
                    <AlertTriangle className="w-4 h-4 inline mr-1 text-yellow-400" />
                    Problem: Assumes the hit lands AND dictates the opponent's reaction
                  </p>
                </div>
                <div className="p-4 bg-red-900/30 rounded-lg border border-red-500/30">
                  <p className="text-red-300 font-mono text-sm">
                    "My fireball engulfs him, burning his armor and singing his hair."
                  </p>
                  <p className="text-gray-400 text-sm mt-2">
                    <AlertTriangle className="w-4 h-4 inline mr-1 text-yellow-400" />
                    Problem: Assumes the spell hits and causes specific damage
                  </p>
                </div>
              </CardContent>
            </Card>

            <Card className="glass border-green-500/50 bg-green-500/10">
              <CardHeader>
                <CardTitle className="text-green-400 flex items-center gap-2">
                  <CheckCircle2 className="w-5 h-5" />
                  GOOD Examples (Attempt-Based)
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="p-4 bg-green-900/30 rounded-lg border border-green-500/30">
                  <p className="text-green-300 font-mono text-sm">
                    "I swing my sword in a horizontal arc toward his chest, attempting to slice through his defenses."
                  </p>
                  <p className="text-gray-400 text-sm mt-2">
                    <CheckCircle2 className="w-4 h-4 inline mr-1 text-green-400" />
                    Good: States the action as an attempt, lets opponent decide outcome
                  </p>
                </div>
                <div className="p-4 bg-green-900/30 rounded-lg border border-green-500/30">
                  <p className="text-green-300 font-mono text-sm">
                    "I unleash a torrent of flame toward him, the fireball seeking to engulf his position."
                  </p>
                  <p className="text-gray-400 text-sm mt-2">
                    <CheckCircle2 className="w-4 h-4 inline mr-1 text-green-400" />
                    Good: Describes the attack approaching, not hitting
                  </p>
                </div>
              </CardContent>
            </Card>

            <Card className="glass border-purple-500/30">
              <CardContent className="p-6">
                <h3 className="text-xl font-bold text-purple-400 mb-4">Key Phrases to Use</h3>
                <div className="flex flex-wrap gap-2">
                  {['attempts to', 'seeks to', 'tries to', 'aims to', 'moves to', 'reaches for', 'swings toward', 'thrusts at', 'hoping to', 'intending to'].map(phrase => (
                    <span key={phrase} className="px-3 py-1 bg-purple-500/20 rounded-full text-purple-300 text-sm">
                      {phrase}
                    </span>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        );

      case 'puppet':
        return (
          <div className="space-y-6">
            <h2 className="text-3xl font-bold text-red-400 flex items-center gap-3">
              <Users className="w-8 h-8" />
              Puppeteering
            </h2>
            <p className="text-gray-300 text-lg">
              Puppeteering is controlling another player's character in any way. This includes dictating their 
              actions, speech, reactions, thoughts, feelings, or even what they perceive.
            </p>

            <Card className="glass border-red-500/50 bg-red-500/10">
              <CardHeader>
                <CardTitle className="text-red-400 flex items-center gap-2">
                  <XCircle className="w-5 h-5" />
                  Examples of Puppeteering (NEVER DO THIS)
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-4">
                  <div className="p-4 bg-red-900/30 rounded-lg border border-red-500/30">
                    <p className="text-red-300 font-semibold">Controlling Actions:</p>
                    <p className="text-red-300/80 font-mono text-sm mt-1">
                      "You stumble backward from the force of my blow."
                    </p>
                  </div>
                  <div className="p-4 bg-red-900/30 rounded-lg border border-red-500/30">
                    <p className="text-red-300 font-semibold">Controlling Speech:</p>
                    <p className="text-red-300/80 font-mono text-sm mt-1">
                      "You cry out 'Have mercy!' as I approach."
                    </p>
                  </div>
                  <div className="p-4 bg-red-900/30 rounded-lg border border-red-500/30">
                    <p className="text-red-300 font-semibold">Controlling Feelings:</p>
                    <p className="text-red-300/80 font-mono text-sm mt-1">
                      "Fear grips your heart as you see my power."
                    </p>
                  </div>
                  <div className="p-4 bg-red-900/30 rounded-lg border border-red-500/30">
                    <p className="text-red-300 font-semibold">Controlling Perceptions:</p>
                    <p className="text-red-300/80 font-mono text-sm mt-1">
                      "You see my blade coming but are too slow to react."
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="glass border-green-500/50 bg-green-500/10">
              <CardHeader>
                <CardTitle className="text-green-400 flex items-center gap-2">
                  <CheckCircle2 className="w-5 h-5" />
                  Correct Alternatives
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-4">
                  <div className="p-4 bg-green-900/30 rounded-lg border border-green-500/30">
                    <p className="text-green-300 font-semibold">Describe YOUR action:</p>
                    <p className="text-green-300/80 font-mono text-sm mt-1">
                      "I deliver a powerful blow that carries considerable force."
                    </p>
                  </div>
                  <div className="p-4 bg-green-900/30 rounded-lg border border-green-500/30">
                    <p className="text-green-300 font-semibold">Describe what they COULD perceive:</p>
                    <p className="text-green-300/80 font-mono text-sm mt-1">
                      "My approach is menacing, blade raised with clear lethal intent."
                    </p>
                  </div>
                  <div className="p-4 bg-green-900/30 rounded-lg border border-green-500/30">
                    <p className="text-green-300 font-semibold">Let THEM decide their reaction:</p>
                    <p className="text-green-300/80 font-mono text-sm mt-1">
                      "The blade whistles through the air toward their position."
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="glass border-yellow-500/30">
              <CardContent className="p-6">
                <h3 className="text-xl font-bold text-yellow-400 mb-4">Remember</h3>
                <p className="text-gray-300">
                  You control: <span className="text-green-400">Your character's actions, speech, thoughts, and feelings</span>
                </p>
                <p className="text-gray-300 mt-2">
                  They control: <span className="text-purple-400">Their character's actions, speech, thoughts, and feelings</span>
                </p>
                <p className="text-gray-300 mt-2">
                  Quest Master controls: <span className="text-blue-400">NPCs, environment, and world events</span>
                </p>
              </CardContent>
            </Card>
          </div>
        );

      case 'meta':
        return (
          <div className="space-y-6">
            <h2 className="text-3xl font-bold text-red-400 flex items-center gap-3">
              <Brain className="w-8 h-8" />
              Metagaming
            </h2>
            <p className="text-gray-300 text-lg">
              Metagaming is using out-of-character (OOC) knowledge to influence in-character (IC) decisions. 
              Your character only knows what they could realistically know.
            </p>

            <Card className="glass border-red-500/50 bg-red-500/10">
              <CardHeader>
                <CardTitle className="text-red-400 flex items-center gap-2">
                  <XCircle className="w-5 h-5" />
                  Examples of Metagaming
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="p-4 bg-red-900/30 rounded-lg border border-red-500/30">
                  <p className="text-red-300 font-semibold">Using OOC Knowledge:</p>
                  <p className="text-gray-400 text-sm mt-1">
                    You (the writer) read that the assassin is behind your character. Your blind character 
                    suddenly "senses danger" and dodges the attack with no established ability to do so.
                  </p>
                </div>
                <div className="p-4 bg-red-900/30 rounded-lg border border-red-500/30">
                  <p className="text-red-300 font-semibold">Mixing (OOC Grudges IC):</p>
                  <p className="text-gray-400 text-sm mt-1">
                    You're angry at another player OOC, so your character conveniently has a reason to 
                    attack their character without any IC justification.
                  </p>
                </div>
                <div className="p-4 bg-red-900/30 rounded-lg border border-red-500/30">
                  <p className="text-red-300 font-semibold">Knowing Hidden Information:</p>
                  <p className="text-gray-400 text-sm mt-1">
                    An NPC's secret weakness was mentioned in another scene. Your character who wasn't 
                    there somehow knows exactly how to exploit it.
                  </p>
                </div>
              </CardContent>
            </Card>

            <Card className="glass border-green-500/50 bg-green-500/10">
              <CardHeader>
                <CardTitle className="text-green-400 flex items-center gap-2">
                  <CheckCircle2 className="w-5 h-5" />
                  How to Avoid Metagaming
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <ul className="space-y-3 text-gray-300">
                  <li className="flex items-start gap-3">
                    <CheckCircle2 className="w-5 h-5 text-green-400 mt-1 flex-shrink-0" />
                    <span>Ask yourself: "How would my character know this?"</span>
                  </li>
                  <li className="flex items-start gap-3">
                    <CheckCircle2 className="w-5 h-5 text-green-400 mt-1 flex-shrink-0" />
                    <span>Keep OOC conversations separate from IC actions</span>
                  </li>
                  <li className="flex items-start gap-3">
                    <CheckCircle2 className="w-5 h-5 text-green-400 mt-1 flex-shrink-0" />
                    <span>Only use senses your character actually has</span>
                  </li>
                  <li className="flex items-start gap-3">
                    <CheckCircle2 className="w-5 h-5 text-green-400 mt-1 flex-shrink-0" />
                    <span>Accept that your character might be surprised or fooled</span>
                  </li>
                </ul>
              </CardContent>
            </Card>

            <Card className="glass border-purple-500/30">
              <CardContent className="p-6">
                <h3 className="text-xl font-bold text-purple-400 mb-4">The IC/OOC Separation</h3>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-blue-400 font-semibold mb-2">YOU (OOC) know:</p>
                    <ul className="text-gray-400 text-sm space-y-1">
                      <li>• The enemy's stats and abilities</li>
                      <li>• What other players are planning</li>
                      <li>• Plot twists and secrets</li>
                      <li>• Everything in other scenes</li>
                    </ul>
                  </div>
                  <div>
                    <p className="text-green-400 font-semibold mb-2">Your CHARACTER knows:</p>
                    <ul className="text-gray-400 text-sm space-y-1">
                      <li>• What they've personally seen/heard</li>
                      <li>• What others have told them IC</li>
                      <li>• Their own backstory knowledge</li>
                      <li>• Public/common knowledge</li>
                    </ul>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        );

      case 'godmod':
        return (
          <div className="space-y-6">
            <h2 className="text-3xl font-bold text-red-400 flex items-center gap-3">
              <Zap className="w-8 h-8" />
              Godmodding
            </h2>
            <p className="text-gray-300 text-lg">
              Godmodding is making your character invincible, omnipotent, or otherwise impossible to 
              defeat through normal means. It removes all tension and fairness from roleplay.
            </p>

            <Card className="glass border-red-500/50 bg-red-500/10">
              <CardHeader>
                <CardTitle className="text-red-400 flex items-center gap-2">
                  <XCircle className="w-5 h-5" />
                  Examples of Godmodding
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="p-4 bg-red-900/30 rounded-lg border border-red-500/30">
                  <p className="text-red-300 font-semibold">Invincibility:</p>
                  <p className="text-gray-400 text-sm mt-1">
                    "The sword passes through me harmlessly - I cannot be wounded by mortal weapons."
                  </p>
                </div>
                <div className="p-4 bg-red-900/30 rounded-lg border border-red-500/30">
                  <p className="text-red-300 font-semibold">Impossible Dodging:</p>
                  <p className="text-gray-400 text-sm mt-1">
                    "I easily dodge all twelve arrows fired at me simultaneously while mid-conversation."
                  </p>
                </div>
                <div className="p-4 bg-red-900/30 rounded-lg border border-red-500/30">
                  <p className="text-red-300 font-semibold">Unlimited Power:</p>
                  <p className="text-gray-400 text-sm mt-1">
                    "I snap my fingers and the entire army turns to dust."
                  </p>
                </div>
              </CardContent>
            </Card>

            <Card className="glass border-green-500/50 bg-green-500/10">
              <CardHeader>
                <CardTitle className="text-green-400 flex items-center gap-2">
                  <CheckCircle2 className="w-5 h-5" />
                  Good Character Limitations
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <ul className="space-y-3 text-gray-300">
                  <li className="flex items-start gap-3">
                    <CheckCircle2 className="w-5 h-5 text-green-400 mt-1 flex-shrink-0" />
                    <span><strong>Stamina:</strong> Powerful abilities tire your character</span>
                  </li>
                  <li className="flex items-start gap-3">
                    <CheckCircle2 className="w-5 h-5 text-green-400 mt-1 flex-shrink-0" />
                    <span><strong>Cooldowns:</strong> Big spells need time to recharge</span>
                  </li>
                  <li className="flex items-start gap-3">
                    <CheckCircle2 className="w-5 h-5 text-green-400 mt-1 flex-shrink-0" />
                    <span><strong>Weaknesses:</strong> Every strength has a counter</span>
                  </li>
                  <li className="flex items-start gap-3">
                    <CheckCircle2 className="w-5 h-5 text-green-400 mt-1 flex-shrink-0" />
                    <span><strong>Consequences:</strong> Actions have realistic effects</span>
                  </li>
                </ul>
              </CardContent>
            </Card>

            <Card className="glass border-yellow-500/30">
              <CardContent className="p-6">
                <h3 className="text-xl font-bold text-yellow-400 mb-4">Note on Divine Characters</h3>
                <p className="text-gray-300">
                  Characters can have backstories where they were "worshipped as gods" by civilizations, 
                  but they must <span className="text-red-400 font-bold">NOT</span> be actually divine in combat. 
                  No character is truly immortal or all-powerful in T1 roleplay.
                </p>
              </CardContent>
            </Card>
          </div>
        );

      case 'powerplay':
        return (
          <div className="space-y-6">
            <h2 className="text-3xl font-bold text-red-400 flex items-center gap-3">
              <Shield className="w-8 h-8" />
              Powerplaying
            </h2>
            <p className="text-gray-300 text-lg">
              Powerplaying is artificially boosting your character's abilities mid-fight or using powers 
              that weren't established in your character bio.
            </p>

            <Card className="glass border-red-500/50 bg-red-500/10">
              <CardHeader>
                <CardTitle className="text-red-400 flex items-center gap-2">
                  <XCircle className="w-5 h-5" />
                  Examples of Powerplaying
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="p-4 bg-red-900/30 rounded-lg border border-red-500/30">
                  <p className="text-red-300 font-semibold">Mid-Fight Power Boost:</p>
                  <p className="text-gray-400 text-sm mt-1">
                    Bio says "strong warrior." Mid-fight: "I tap into my hidden power, becoming 
                    ten times stronger than before!"
                  </p>
                </div>
                <div className="p-4 bg-red-900/30 rounded-lg border border-red-500/30">
                  <p className="text-red-300 font-semibold">Unestablished Abilities:</p>
                  <p className="text-gray-400 text-sm mt-1">
                    Bio mentions sword skills only. Mid-fight: "I unleash my secret fire magic 
                    that I've been hiding all along."
                  </p>
                </div>
                <div className="p-4 bg-red-900/30 rounded-lg border border-red-500/30">
                  <p className="text-red-300 font-semibold">Reactive Countering:</p>
                  <p className="text-gray-400 text-sm mt-1">
                    Opponent uses ice magic. Suddenly: "My armor is specifically enchanted against 
                    ice!" (when this was never mentioned before)
                  </p>
                </div>
              </CardContent>
            </Card>

            <Card className="glass border-green-500/50 bg-green-500/10">
              <CardHeader>
                <CardTitle className="text-green-400 flex items-center gap-2">
                  <CheckCircle2 className="w-5 h-5" />
                  Best Practices
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <ul className="space-y-3 text-gray-300">
                  <li className="flex items-start gap-3">
                    <CheckCircle2 className="w-5 h-5 text-green-400 mt-1 flex-shrink-0" />
                    <span>Write a detailed character bio BEFORE combat</span>
                  </li>
                  <li className="flex items-start gap-3">
                    <CheckCircle2 className="w-5 h-5 text-green-400 mt-1 flex-shrink-0" />
                    <span>Include all abilities, weapons, and equipment in your bio</span>
                  </li>
                  <li className="flex items-start gap-3">
                    <CheckCircle2 className="w-5 h-5 text-green-400 mt-1 flex-shrink-0" />
                    <span>Establish limitations and weaknesses</span>
                  </li>
                  <li className="flex items-start gap-3">
                    <CheckCircle2 className="w-5 h-5 text-green-400 mt-1 flex-shrink-0" />
                    <span>Stick to what you've established - consistency matters</span>
                  </li>
                </ul>
              </CardContent>
            </Card>
          </div>
        );

      case 'posts':
        return (
          <div className="space-y-6">
            <h2 className="text-3xl font-bold text-purple-400 flex items-center gap-3">
              <Scroll className="w-8 h-8" />
              Post Types
            </h2>
            <p className="text-gray-300 text-lg">
              Different situations call for different types of posts. Understanding these helps you 
              write more effective roleplay.
            </p>

            <div className="grid gap-4">
              {[
                {
                  type: 'Entrance Post',
                  desc: 'Your character arrives at the scene',
                  rules: ['Set the stage with description', 'Establish your position', 'NO attacking in entrance posts', 'You can prep abilities but cannot harm others'],
                  color: 'blue'
                },
                {
                  type: 'Prep Post',
                  desc: 'Charging energy or preparing abilities',
                  rules: ['Cannot attack while prepping same energy', 'Describe the charging process', 'Can be interrupted by opponents', 'Building up for a bigger attack'],
                  color: 'purple'
                },
                {
                  type: 'Attack Post',
                  desc: 'Offensive actions against others',
                  rules: ['ALWAYS write as attempts', 'Describe direction, speed, intended target', 'State potential damage IF it hits', 'Leave room for response'],
                  color: 'red'
                },
                {
                  type: 'Defense Post',
                  desc: 'Blocking incoming attacks',
                  rules: ['Must address ALL damage intended', 'Failing to address = damage lands', 'Explain HOW you block', 'Consider positioning and timing'],
                  color: 'green'
                },
                {
                  type: 'Evasive Post',
                  desc: 'Dodging incoming attacks',
                  rules: ['Explain how you sensed the attack', 'Logical movement required', 'Consider terrain and positioning', 'You can dodge + counter in one post'],
                  color: 'yellow'
                },
                {
                  type: 'Exit Post',
                  desc: 'Leaving the scene',
                  rules: ['Describe how you leave', 'Can be used to flee combat', 'May count as loss in death matches', 'Must be clean escape to survive'],
                  color: 'gray'
                }
              ].map(post => (
                <Card key={post.type} className={`glass border-${post.color}-500/30`}>
                  <CardHeader 
                    className="cursor-pointer" 
                    onClick={() => toggleExample(post.type)}
                  >
                    <CardTitle className={`text-${post.color}-400 flex items-center justify-between`}>
                      <span>{post.type}</span>
                      {expandedExamples[post.type] ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
                    </CardTitle>
                    <p className="text-gray-400 text-sm">{post.desc}</p>
                  </CardHeader>
                  {expandedExamples[post.type] && (
                    <CardContent>
                      <ul className="space-y-2 text-gray-300 text-sm">
                        {post.rules.map((rule) => (
                          <li key={`${post.type}-${rule}`} className="flex items-start gap-2">
                            <CheckCircle2 className="w-4 h-4 text-green-400 mt-0.5 flex-shrink-0" />
                            {rule}
                          </li>
                        ))}
                      </ul>
                    </CardContent>
                  )}
                </Card>
              ))}
            </div>

            <Card className="glass border-yellow-500/30">
              <CardContent className="p-6">
                <h3 className="text-xl font-bold text-yellow-400 mb-4">Successive Actions</h3>
                <p className="text-gray-300">
                  You can combine multiple actions in one post (typically 3-4 max). For example: 
                  dodge + counter-attack. However, you <span className="text-red-400 font-bold">cannot</span> prep 
                  and attack with the same energy in one post.
                </p>
              </CardContent>
            </Card>
          </div>
        );

      case 'practice':
        return <T1PracticeArena />;

      default:
        return null;
    }
  };

  return (
    <div className="min-h-screen relative">
      <AnimatedBackground />
      <Navbar />
      
      <main className="container mx-auto px-4 py-8 relative z-10">
        <div className="text-center mb-8">
          <h1 className="text-5xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-purple-400 via-pink-500 to-red-500 mb-4">
            T1 Roleplay Tutorial
          </h1>
          <p className="text-xl text-gray-400">
            Master the art of fair, skill-based text roleplay
          </p>
        </div>

        <div className="flex gap-8">
          {/* Sidebar Navigation */}
          <div className="w-64 flex-shrink-0">
            <Card className="glass border-purple-500/30 sticky top-8">
              <CardContent className="p-4">
                <nav className="space-y-2">
                  {sections.map(section => (
                    <button
                      key={section.id}
                      onClick={() => setActiveSection(section.id)}
                      className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition text-left ${
                        activeSection === section.id 
                          ? 'bg-purple-500/30 text-purple-300' 
                          : 'text-gray-400 hover:bg-purple-500/10 hover:text-gray-300'
                      }`}
                    >
                      <section.icon className="w-5 h-5" />
                      {section.label}
                    </button>
                  ))}
                </nav>
              </CardContent>
            </Card>
          </div>

          {/* Main Content */}
          <div className="flex-1">
            <Card className="glass border-purple-500/30">
              <CardContent className="p-8">
                {renderSection()}
              </CardContent>
            </Card>
          </div>
        </div>
      </main>
    </div>
  );
};

export default T1Tutorial;
