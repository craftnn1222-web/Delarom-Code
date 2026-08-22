import React, { useEffect, useState } from 'react';
import api from '../../utils/api';
import { fetchBallads, fetchMemorial, fetchFeaturedMaster } from '../../utils/api';
import { ScrollText, Wind, Skull, Music, Mail, Heart, ChevronRight, Newspaper, Hammer } from 'lucide-react';

/**
 * Quill & Coffer Front Page — newspaper-style hero shown on first load.
 *
 * Pulls a single teaser from each public section (Chronicle, Rumors, Bounties,
 * Memorial, Ballads) and renders them as a lead story + grid of side cards.
 * Letters and Bonds are personal (require character context), so they're shown
 * as static "open the section" prompts at the bottom rather than teased.
 *
 * Each card calls `onJumpToTab(tabId)` to swap into the relevant tab.
 */

const PRINT_DATE_OPTS = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };

const sectionStyles = {
  chronicle: { icon: ScrollText, ring: 'border-amber-500/40',  text: 'text-amber-200',  kicker: 'A WHISPER FROM THE WORLD' },
  rumors:    { icon: Wind,       ring: 'border-purple-500/40', text: 'text-purple-200', kicker: 'TONGUES WAG' },
  bounties:  { icon: Skull,      ring: 'border-rose-500/40',   text: 'text-rose-200',   kicker: 'OPEN WARRANTS' },
  memorial:  { icon: Skull,      ring: 'border-gray-500/40',   text: 'text-gray-200',   kicker: 'THE FALLEN' },
  ballads:   { icon: Music,      ring: 'border-amber-500/40',  text: 'text-amber-200',  kicker: 'A SONG, RECENTLY SUNG' },
};

const truncate = (s, n) => (s && s.length > n ? `${s.slice(0, n).trim()}…` : s || '');

const TeaserCard = ({ section, kicker, title, body, footer, onClick, size = 'normal' }) => {
  const s = sectionStyles[section];
  const Icon = s.icon;
  const isLead = size === 'lead';
  return (
    <button
      type="button"
      onClick={onClick}
      data-testid={`frontpage-card-${section}`}
      className={`group text-left w-full glass-dark ${s.ring} border rounded-lg p-5 hover:border-amber-300/60 hover:bg-stone-900/60 transition-all duration-200 ${isLead ? 'sm:col-span-2 sm:row-span-2' : ''}`}
    >
      <div className={`flex items-center gap-2 ${s.text} text-[10px] tracking-[0.3em] mb-3`}>
        <Icon className="w-3.5 h-3.5" />
        {kicker}
      </div>
      <h3 className={`${isLead ? 'text-2xl sm:text-3xl' : 'text-lg'} font-bold text-gray-100 leading-snug mb-2 group-hover:text-white`} style={{ fontFamily: 'Georgia, serif' }}>
        {title}
      </h3>
      {body && (
        <p className={`text-gray-300 ${isLead ? 'text-sm sm:text-base' : 'text-xs'} leading-relaxed`}>
          {body}
        </p>
      )}
      <div className="mt-4 flex items-center justify-between text-[11px] text-gray-400 italic">
        <span>{footer}</span>
        <span className="flex items-center gap-1 text-amber-300 group-hover:text-amber-200 not-italic font-semibold">
          Read more <ChevronRight className="w-3 h-3" />
        </span>
      </div>
    </button>
  );
};

const QuillCofferFrontPage = ({ onJumpToTab }) => {
  const [data, setData] = useState({ chronicle: null, rumor: null, bounty: null, memorial: null, ballad: null });
  const [master, setMaster] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      const calls = await Promise.allSettled([
        api.get('/chronicle?limit=1'),
        api.get('/rumors'),
        api.get('/bounty-board'),
        fetchMemorial(),
        fetchBallads(),
        fetchFeaturedMaster(),
      ]);
      if (cancelled) return;
      const pick = (i) => (calls[i].status === 'fulfilled' ? calls[i].value.data : null);
      const c = pick(0); const r = pick(1); const b = pick(2); const m = pick(3); const bal = pick(4); const fm = pick(5);
      setData({
        chronicle: Array.isArray(c) ? c[0] : null,
        rumor:     Array.isArray(r) ? r[0] : null,
        bounty:    Array.isArray(b) ? b[0] : null,
        memorial:  Array.isArray(m) ? m[0] : null,
        ballad:    Array.isArray(bal) ? bal[0] : null,
      });
      setMaster(fm && fm.id ? fm : null);
      setLoading(false);
    };
    load();
    return () => { cancelled = true; };
  }, []);

  const today = new Date().toLocaleDateString(undefined, PRINT_DATE_OPTS);

  return (
    <div className="container mx-auto px-4 pb-10 max-w-6xl" data-testid="quill-frontpage">
      {/* Newspaper masthead */}
      <header className="text-center border-y-2 border-amber-700/40 py-3 mb-6">
        <div className="flex items-center justify-center gap-2 text-[10px] tracking-[0.4em] text-amber-300/70 mb-1">
          <Newspaper className="w-3 h-3" />
          THE FRONT PAGE
        </div>
        <p className="text-xs italic text-gray-400">{today} — Vol. I · The realm reads on</p>
      </header>

      {loading ? (
        <p className="text-center text-gray-500 italic py-12" data-testid="frontpage-loading">
          The presses are still warm…
        </p>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {/* Lead story — Chronicle */}
          {data.chronicle ? (
            <TeaserCard
              section="chronicle"
              kicker={sectionStyles.chronicle.kicker}
              title={truncate(data.chronicle.summary, 120) || 'The Chronicle stirs.'}
              body={truncate(data.chronicle.details, 240)}
              footer={data.chronicle.created_at ? new Date(data.chronicle.created_at).toLocaleDateString() : 'Recently chronicled'}
              size="lead"
              onClick={() => onJumpToTab('chronicle')}
            />
          ) : (
            <button
              type="button"
              onClick={() => onJumpToTab('chronicle')}
              data-testid="frontpage-card-chronicle"
              className="sm:col-span-2 sm:row-span-2 glass-dark border border-amber-500/30 rounded-lg p-6 text-left hover:border-amber-300/60 transition"
            >
              <p className="text-[10px] tracking-[0.3em] text-amber-300 mb-2">A WHISPER FROM THE WORLD</p>
              <h3 className="text-2xl font-bold text-gray-100" style={{ fontFamily: 'Georgia, serif' }}>The Chronicle waits to be written.</h3>
              <p className="text-sm text-gray-400 mt-2">No events yet. The first deeds will become the realm's first headlines.</p>
            </button>
          )}

          {/* Rumor */}
          <TeaserCard
            section="rumors"
            kicker={sectionStyles.rumors.kicker}
            title={data.rumor ? `"${truncate(data.rumor.content, 90)}"` : 'No rumors stir the taverns.'}
            body={data.rumor ? null : 'Plant the first whisper and watch it spread.'}
            footer={data.rumor ? `Overheard in ${data.rumor.nation || 'the realm'}` : 'Tap to plant a rumor'}
            onClick={() => onJumpToTab('rumors')}
          />

          {/* Bounty */}
          <TeaserCard
            section="bounties"
            kicker={sectionStyles.bounties.kicker}
            title={data.bounty ? `Wanted: ${data.bounty.perpetrator_name || 'a fugitive'}` : 'No warrants posted.'}
            body={data.bounty ? `Crimes against the crown of ${data.bounty.nation || 'the realm'}.` : 'The realm sleeps quietly — for now.'}
            footer={data.bounty ? `${data.bounty.total_bounty ?? 0} gold offered` : 'Tap to view the board'}
            onClick={() => onJumpToTab('bounties')}
          />

          {/* Memorial */}
          <TeaserCard
            section="memorial"
            kicker={sectionStyles.memorial.kicker}
            title={data.memorial ? `In Memoriam: ${data.memorial.name}` : 'The Hall is quiet.'}
            body={data.memorial ? truncate(data.memorial.cause_of_death || `${data.memorial.race} ${data.memorial.character_class} of ${data.memorial.nation}`, 110) : 'None have yet passed into legend.'}
            footer={data.memorial && data.memorial.died_at ? new Date(data.memorial.died_at).toLocaleDateString() : 'Tap to visit the Hall'}
            onClick={() => onJumpToTab('memorial')}
          />

          {/* Ballad */}
          <TeaserCard
            section="ballads"
            kicker={sectionStyles.ballads.kicker}
            title={data.ballad ? data.ballad.title : 'No songs yet sung.'}
            body={data.ballad ? truncate(data.ballad.body, 110) : 'The bards await their first commission.'}
            footer={data.ballad ? `By ${data.ballad.bard || 'a wandering bard'}` : 'Tap to commission one'}
            onClick={() => onJumpToTab('ballads')}
          />
        </div>
      )}

      {/* Featured Master of the Week — rotating spotlight on one of the
          80 master NPCs available for apprenticeship. Drives players toward
          the Apprenticeships system and gives the world an extra heartbeat. */}
      {master && (
        <div className="mt-8 pt-6 border-t border-amber-700/30">
          <p className="text-center text-[10px] tracking-[0.3em] text-amber-300/60 mb-4">
            FEATURED MASTER · {master.iso_week || 'this week'}
          </p>
          <div
            className="glass-dark border border-amber-500/40 rounded-lg p-5 sm:p-6 flex items-start gap-4"
            data-testid="frontpage-featured-master"
          >
            <div className="bg-amber-900/30 border border-amber-500/30 rounded-full p-3 flex-shrink-0">
              <Hammer className="w-6 h-6 text-amber-300" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 text-[10px] tracking-[0.3em] text-amber-300/70 mb-1">
                MASTER {String(master.craft || '').toUpperCase()}
                <span className="text-gray-500">·</span>
                <span className="capitalize text-gray-400">{String(master.nation || '').replace('-', ' ')}</span>
              </div>
              <h3
                className="text-2xl sm:text-3xl font-bold text-amber-100 leading-tight"
                style={{ fontFamily: 'Georgia, serif' }}
                data-testid="frontpage-featured-master-name"
              >
                {master.name}
              </h3>
              <p className="text-sm text-gray-400 italic mt-1">
                {master.race}{master.location ? ` — of ${master.location}` : ''}
              </p>
              {master.quirks && (
                <p className="text-gray-200 mt-3 leading-relaxed">
                  &ldquo;{master.quirks}&rdquo;
                </p>
              )}
              {master.motivation && (
                <p className="text-xs text-gray-500 mt-3 italic">
                  Keeps to: {master.motivation}
                </p>
              )}
              <p className="text-xs text-amber-300/80 mt-4">
                Apprentices are taken in person — visit your character&apos;s Apprenticeships panel to seek them out.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Personal sections — Letters / Bonds */}
      <div className="mt-8 pt-6 border-t border-amber-700/30">
        <p className="text-center text-[10px] tracking-[0.3em] text-amber-300/60 mb-4">YOUR OWN HAND, YOUR OWN BONDS</p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <button
            type="button"
            onClick={() => onJumpToTab('letters')}
            data-testid="frontpage-card-letters"
            className="glass-dark border border-amber-500/30 rounded-lg p-4 text-left hover:border-amber-300/60 transition group"
          >
            <div className="flex items-center gap-3">
              <Mail className="w-5 h-5 text-amber-300" />
              <div>
                <p className="font-semibold text-gray-100">Letters</p>
                <p className="text-xs text-gray-400">Sealed words travel by courier — half an hour within a nation, four hours across the sea.</p>
              </div>
              <ChevronRight className="w-4 h-4 text-amber-300 ml-auto group-hover:translate-x-1 transition" />
            </div>
          </button>
          <button
            type="button"
            onClick={() => onJumpToTab('bonds')}
            data-testid="frontpage-card-bonds"
            className="glass-dark border border-pink-500/30 rounded-lg p-4 text-left hover:border-pink-300/60 transition group"
          >
            <div className="flex items-center gap-3">
              <Heart className="w-5 h-5 text-pink-300" />
              <div>
                <p className="font-semibold text-gray-100">Bonds</p>
                <p className="text-xs text-gray-400">Blood-brothers, mentors, rivals — oaths sworn and oaths broken.</p>
              </div>
              <ChevronRight className="w-4 h-4 text-pink-300 ml-auto group-hover:translate-x-1 transition" />
            </div>
          </button>
        </div>
      </div>
    </div>
  );
};

export default QuillCofferFrontPage;
