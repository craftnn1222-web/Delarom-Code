import React, { useState, useEffect } from 'react';
import { Button } from '../ui/button';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/card';
import { toast } from 'sonner';
import api from '../../utils/api';
import {
  Swords,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Send,
  Trophy,
  RotateCcw,
  ArrowRight,
} from 'lucide-react';

/**
 * Progressive combat scenarios — the player advances by writing a T1-compliant
 * response judged by the backend.
 */
export const COMBAT_SCENARIOS = [
  {
    id: 1,
    title: 'The Confrontation',
    prompt: 'You sit at a worn wooden table in the dimly lit Rusty Tankard tavern, nursing a mug of ale. The door crashes open. A hooded figure scans the room, their eyes locking onto you. They draw a gleaming dagger from beneath their cloak and begin stalking toward your table, murder in their gaze.',
    hint: 'Describe your initial reaction. How does your character respond to the threat? Remember: attempt-based language!',
    context: 'Initial confrontation - enemy approaching with weapon drawn',
  },
  {
    id: 2,
    title: 'First Blood',
    prompt: 'The hooded figure closes the distance with frightening speed! They lunge forward, their dagger slashing in a vicious arc toward your throat, attempting to end this fight before it truly begins. The blade whistles through the air, mere inches from your flesh.',
    hint: 'How do you defend yourself? Dodge, block, or parry? Describe your defensive action as an attempt.',
    context: 'Defending against an attack to the throat',
  },
  {
    id: 3,
    title: 'Counter Strike',
    prompt: 'Your defensive maneuver creates a brief opening! The assassin is momentarily off-balance from their missed strike, their right side exposed. Their breathing is heavy, and you notice a slight tremor in their dagger hand. This is your chance to turn the tide.',
    hint: 'Launch your counter-attack! Remember to target a specific body part and describe the intended effect IF it connects.',
    context: 'Counter-attacking an off-balance opponent',
  },
  {
    id: 4,
    title: 'The Dance Continues',
    prompt: 'The assassin recovers faster than expected! They twist away from your attack and circle to your left, kicking a chair into your path. Glass shatters somewhere nearby as patrons flee. The assassin feints high, then drives their dagger low toward your midsection in a deceptive thrust.',
    hint: 'Another attack incoming! How do you handle the feint and the real attack? Consider the environment too.',
    context: 'Dealing with a feint attack to the midsection',
  },
  {
    id: 5,
    title: 'Pressing the Advantage',
    prompt: 'The assassin stumbles back, clearly tiring. Blood drips from a wound on their arm—evidence of your previous exchange. They raise their dagger defensively, eyes darting toward the tavern door. You sense desperation in their stance. The other patrons have cleared out, leaving overturned tables and broken glass scattered across the floor.',
    hint: 'Your opponent is weakening. Press your advantage, but remember—a cornered enemy is dangerous. Write your aggressive action.',
    context: 'Pressing advantage against a wounded, desperate opponent',
  },
  {
    id: 6,
    title: 'The Decisive Moment',
    prompt: 'The assassin makes one final, desperate gambit—they hurl their dagger directly at your face while simultaneously diving toward a fallen chair leg as an improvised weapon. The thrown blade spins end over end toward you, glinting in the candlelight. This is the decisive moment.',
    hint: 'Multiple threats at once! Deal with the thrown dagger and the desperate enemy. How do you end this fight?',
    context: 'Final confrontation - thrown weapon and desperate enemy',
  },
  {
    id: 7,
    title: 'Victory',
    prompt: 'The fight is over. The assassin lies defeated at your feet, groaning in pain. The tavern is in shambles—broken furniture, shattered glass, and spilled ale everywhere. The barkeep peeks out from behind the counter, eyes wide. You hear the distant sound of the city watch approaching. What do you do now?',
    hint: 'The combat has ended. How does your character handle the aftermath? Interrogate the assassin? Flee before the guards arrive? Celebrate?',
    context: 'Post-combat - dealing with aftermath and defeated enemy',
  },
];

/**
 * Self-contained Practice Arena tab. Owns all combat practice state +
 * the call to /api/t1/judge-action.
 */
const T1PracticeArena = () => {
  const [practiceAction, setPracticeAction] = useState('');
  const [judgeResult, setJudgeResult] = useState(null);
  const [isJudging, setIsJudging] = useState(false);
  const [currentScenarioIndex, setCurrentScenarioIndex] = useState(0);
  const [completedScenarios, setCompletedScenarios] = useState([]);
  const [showContinueButton, setShowContinueButton] = useState(false);
  const [practiceComplete, setPracticeComplete] = useState(false);

  const currentScenario = COMBAT_SCENARIOS[currentScenarioIndex];

  // Reset transient state whenever the scenario index changes.
  useEffect(() => {
    setShowContinueButton(false);
    setJudgeResult(null);
    setPracticeAction('');
  }, [currentScenarioIndex]);

  const handleJudgeAction = async () => {
    if (!practiceAction.trim()) {
      toast.error('Please enter an action to judge');
      return;
    }
    setIsJudging(true);
    try {
      const response = await api.post('/t1/judge-action', {
        action_text: practiceAction,
        context: currentScenario.context,
      });
      setJudgeResult(response.data);
      if (response.data.is_valid) {
        setShowContinueButton(true);
        setCompletedScenarios((prev) => [...prev, currentScenarioIndex]);
        toast.success('Excellent! Your response is T1 compliant!');
      }
    } catch (error) {
      toast.error('Failed to judge action');
      console.error(error);
    } finally {
      setIsJudging(false);
    }
  };

  const handleNextScenario = () => {
    if (currentScenarioIndex < COMBAT_SCENARIOS.length - 1) {
      setCurrentScenarioIndex((prev) => prev + 1);
    } else {
      setPracticeComplete(true);
      toast.success('Congratulations! You have completed the T1 Combat Practice!');
    }
  };

  const handleRestartPractice = () => {
    setCurrentScenarioIndex(0);
    setCompletedScenarios([]);
    setPracticeComplete(false);
    setJudgeResult(null);
    setPracticeAction('');
    setShowContinueButton(false);
  };

  return (
    <div className="space-y-6" data-testid="practice-arena">
      <h2 className="text-3xl font-bold text-green-400 flex items-center gap-3">
        <Swords className="w-8 h-8" />
        Practice Arena
      </h2>
      <p className="text-gray-300 text-lg">
        Experience a full T1 combat encounter! Write proper responses to advance through the battle.
      </p>

      {/* Progress Bar */}
      <div className="space-y-2">
        <div className="flex justify-between text-sm">
          <span className="text-gray-400">Combat Progress</span>
          <span className="text-purple-400">
            {practiceComplete ? 'Complete!' : `Round ${currentScenarioIndex + 1} of ${COMBAT_SCENARIOS.length}`}
          </span>
        </div>
        <div className="h-3 bg-black/40 rounded-full overflow-hidden border border-purple-500/30">
          <div
            className="h-full bg-gradient-to-r from-purple-500 to-pink-500 transition-all duration-500"
            style={{ width: `${(completedScenarios.length / COMBAT_SCENARIOS.length) * 100}%` }}
          />
        </div>
        <div className="flex justify-between">
          {COMBAT_SCENARIOS.map((scenario, idx) => (
            <div
              key={scenario.id}
              className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold transition-all ${
                completedScenarios.includes(idx)
                  ? 'bg-green-500 text-white'
                  : idx === currentScenarioIndex
                  ? 'bg-purple-500 text-white animate-pulse'
                  : 'bg-gray-700 text-gray-400'
              }`}
            >
              {completedScenarios.includes(idx) ? <CheckCircle2 className="w-4 h-4" /> : idx + 1}
            </div>
          ))}
        </div>
      </div>

      {/* Victory Screen */}
      {practiceComplete ? (
        <Card className="glass border-yellow-500/50 bg-yellow-500/10">
          <CardContent className="p-8 text-center space-y-6">
            <Trophy className="w-20 h-20 text-yellow-400 mx-auto" />
            <h3 className="text-3xl font-bold text-yellow-400">Victory!</h3>
            <p className="text-gray-300 text-lg">
              Congratulations, warrior! You have successfully completed the T1 Combat Practice. You have
              demonstrated mastery of attempt-based combat writing.
            </p>
            <div className="flex justify-center gap-4">
              <Button
                onClick={handleRestartPractice}
                className="bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700"
                data-testid="practice-restart-btn"
              >
                <RotateCcw className="w-4 h-4 mr-2" />
                Fight Again
              </Button>
            </div>
          </CardContent>
        </Card>
      ) : (
        <>
          {/* Current Scenario */}
          <Card className="glass border-purple-500/50 bg-purple-500/10">
            <CardHeader>
              <CardTitle className="text-purple-400 flex items-center justify-between">
                <span className="flex items-center gap-2">
                  <Swords className="w-5 h-5" />
                  {currentScenario.title}
                </span>
                <span className="text-sm text-gray-400 font-normal">
                  Round {currentScenarioIndex + 1}
                </span>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-gray-200 text-lg leading-relaxed italic">{currentScenario.prompt}</p>
              <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-3">
                <p className="text-blue-300 text-sm flex items-start gap-2">
                  <AlertTriangle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                  <span><strong>Hint:</strong> {currentScenario.hint}</span>
                </p>
              </div>
            </CardContent>
          </Card>

          {/* Response Input */}
          <div className="space-y-4">
            <textarea
              value={practiceAction}
              onChange={(e) => setPracticeAction(e.target.value)}
              placeholder="Write your T1-compliant response here... Remember to use attempt-based language!"
              className="w-full h-40 bg-black/40 border border-purple-500/30 rounded-lg p-4 text-gray-200 placeholder-gray-500 focus:outline-none focus:border-purple-500"
              disabled={showContinueButton}
              data-testid="practice-input"
            />

            {!showContinueButton ? (
              <Button
                onClick={handleJudgeAction}
                disabled={isJudging || !practiceAction.trim()}
                className="w-full bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700"
                data-testid="practice-submit-btn"
              >
                {isJudging ? (
                  <span className="flex items-center gap-2">
                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    Analyzing…
                  </span>
                ) : (
                  <span className="flex items-center gap-2">
                    <Send className="w-4 h-4" />
                    Submit Response
                  </span>
                )}
              </Button>
            ) : (
              <Button
                onClick={handleNextScenario}
                className="w-full bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700"
                data-testid="practice-next-btn"
              >
                <span className="flex items-center gap-2">
                  <ArrowRight className="w-4 h-4" />
                  {currentScenarioIndex < COMBAT_SCENARIOS.length - 1 ? 'Continue to Next Round' : 'Complete Practice'}
                </span>
              </Button>
            )}
          </div>

          {/* Judge Result */}
          {judgeResult && (
            <Card className={`glass ${judgeResult.is_valid ? 'border-green-500/50 bg-green-500/10' : 'border-red-500/50 bg-red-500/10'}`}>
              <CardHeader>
                <CardTitle className={`flex items-center gap-2 ${judgeResult.is_valid ? 'text-green-400' : 'text-red-400'}`}>
                  {judgeResult.is_valid ? (
                    <><CheckCircle2 className="w-6 h-6" /> Excellent! T1 Compliant Response!</>
                  ) : (
                    <><XCircle className="w-6 h-6" /> Rule Violations Detected - Try Again</>
                  )}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {judgeResult.violations && judgeResult.violations.length > 0 && (
                  <div>
                    <p className="text-red-400 font-semibold mb-2">Violations:</p>
                    <ul className="space-y-1">
                      {judgeResult.violations.map((v) => (
                        <li key={v} className="text-red-300 flex items-center gap-2">
                          <AlertTriangle className="w-4 h-4" />
                          {v}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                <div>
                  <p className="text-purple-400 font-semibold mb-2">Feedback:</p>
                  <p className="text-gray-300">{judgeResult.feedback}</p>
                </div>

                {judgeResult.suggested_rewrite && !judgeResult.is_valid && (
                  <div>
                    <p className="text-green-400 font-semibold mb-2">Suggested Rewrite:</p>
                    <p className="text-gray-300 italic bg-green-900/30 p-3 rounded-lg border border-green-500/30">
                      &ldquo;{judgeResult.suggested_rewrite}&rdquo;
                    </p>
                  </div>
                )}

                {judgeResult.is_valid && (
                  <div className="bg-green-900/30 p-4 rounded-lg border border-green-500/30">
                    <p className="text-green-300 flex items-center gap-2">
                      <CheckCircle2 className="w-5 h-5" />
                      Click &ldquo;Continue to Next Round&rdquo; to advance!
                    </p>
                  </div>
                )}
              </CardContent>
            </Card>
          )}
        </>
      )}

      {/* Tips Card */}
      <Card className="glass border-blue-500/30">
        <CardHeader>
          <CardTitle className="text-blue-400">Quick T1 Reminders</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div className="p-3 bg-green-900/20 rounded-lg border border-green-500/30">
              <p className="text-green-300 text-sm">
                <CheckCircle2 className="w-4 h-4 inline mr-2" />
                Use: &ldquo;attempts to&rdquo;, &ldquo;tries to&rdquo;, &ldquo;aims to&rdquo;
              </p>
            </div>
            <div className="p-3 bg-green-900/20 rounded-lg border border-green-500/30">
              <p className="text-green-300 text-sm">
                <CheckCircle2 className="w-4 h-4 inline mr-2" />
                Describe YOUR actions, not their reactions
              </p>
            </div>
            <div className="p-3 bg-red-900/20 rounded-lg border border-red-500/30">
              <p className="text-red-300 text-sm">
                <XCircle className="w-4 h-4 inline mr-2" />
                Avoid: &ldquo;I hit him&rdquo;, &ldquo;he falls&rdquo;
              </p>
            </div>
            <div className="p-3 bg-red-900/20 rounded-lg border border-red-500/30">
              <p className="text-red-300 text-sm">
                <XCircle className="w-4 h-4 inline mr-2" />
                Never control your opponent&apos;s character
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Restart Button (mid-fight) */}
      {(currentScenarioIndex > 0 || completedScenarios.length > 0) && !practiceComplete && (
        <Button
          onClick={handleRestartPractice}
          variant="outline"
          className="w-full border-gray-600 text-gray-400 hover:bg-gray-800"
        >
          <RotateCcw className="w-4 h-4 mr-2" />
          Restart Practice from Beginning
        </Button>
      )}
    </div>
  );
};

export default T1PracticeArena;
