import { Link } from 'react-router-dom';
import { ArrowRight, BookOpen, Check, ChevronDown, Clock3, Gift, Headphones, Landmark, Feather, Eye, CirclePause, Heart, CreditCard, MonitorSmartphone, Languages } from 'lucide-react';
import { availableReadingPasses } from '../lib/readingPassOffers';
import '../styles/reading-passes.css';

const ART = '/assets/commerce/';
const money = n => `₹${new Intl.NumberFormat('en-IN', { maximumFractionDigits: 2 }).format(n)}`;
const PERSONAS = [
  ['new-reader', 'For the first chapter', 'Let curiosity choose your next companion.'],
  ['daily-reader', 'For your everyday pause', 'A little reading. A little room for yourself.'],
  ['deep-reader', 'For the long way home', 'Some stories deserve an unhurried evening.'],
  ['audio-reader', 'For a story in your ear', 'Discover listening editions as they become available.'],
];
const FAQ = [
  ['Is a Reading Pass a subscription?', 'No. Reading Passes are one-time purchases and do not auto-renew. Choose another only when you want more reading time.'],
  ['How long is my pass valid?', 'Purchased unused Reading Pass minutes do not expire. A pass is a one-time purchase, not a subscription.'],
  ['Can I try a book before choosing?', 'Where a preview is available, the first 3 canonical text pages are free. Public audiobooks are unavailable in this launch.'],
];
function MiniFact({ icon: Icon, title, children }) { return <div className="rp-mini-fact"><Icon aria-hidden="true"/><div><strong>{title}</strong><span>{children}</span></div></div>; }

export default function ReadingPassesSurface({ packs = [], config, busyId, offerStatus = 'ready', selectedPackId, onBuy, onRetry, illustrativePasses = false }) {
  const offers = availableReadingPasses(packs);
  // The existing checkout owns availability. Test-mode checkout remains a
  // legitimate configured path; presentation must neither bypass nor hide it.
  const canSelect = illustrativePasses || config?.configured === true || config?.mode === 'test';
  const state = offerStatus === 'ready' && !offers.length ? 'empty' : offerStatus;
  return <div className="reading-passes" data-testid="pricing-reference-surface">
    <section className="rp-hero" aria-labelledby="rp-title">
      <div className="rp-hero-inner">
        <div className="rp-hero-copy">
          <p className="rp-eyebrow">READING PASSES</p>
          <h1 id="rp-title">Read more.<br/>Live the stories.</h1>
          <p className="rp-lede">For the pages that call you back.<br/>Make a little room for a world beyond your own.</p>
          <ul className="rp-hero-points">
            <li><Eye aria-hidden="true"/>3 free pages where a preview is available</li>
            <li><Clock3 aria-hidden="true"/>Reading time runs only while you read</li>
            <li><CirclePause aria-hidden="true"/>One-time passes. No auto-renewal.</li>
          </ul>
          <a className="rp-text-link" href="#reading-passes">Find your Reading Pass <ArrowRight aria-hidden="true"/></a>
        </div>
        <img className="rp-hero-art" src={`${ART}lamp-reading-room.png`} alt="" width="270" height="260" fetchPriority="high"/>
        <aside className="rp-promise" aria-labelledby="rp-promise-title">
          <h2 id="rp-promise-title">A little time. A world within.</h2>
          <p>A Reading Pass, simply explained.</p>
          <div className="rp-fact-rings">
            <div><span>3</span><strong>free text pages</strong><small>where previews are available</small></div>
            <div><span>0</span><strong>auto-renewals</strong><small>no recurring subscription</small></div>
            <div><span>You</span><strong>set the rhythm</strong><small>choose your reading time</small></div>
          </div>
          <div className="rp-promise-note"><BookOpen aria-hidden="true"/><p>Meet the story first.<br/><strong>Stay when it speaks to you.</strong></p></div>
        </aside>
      </div>
    </section>

    <section id="reading-passes" className="rp-section rp-offers" aria-labelledby="rp-offers-title">
      <div className="rp-section-heading"><div><h2 id="rp-offers-title">Choose a pass that fits your rhythm.</h2><p>A brief escape or a longer stay. The next chapter is yours.</p></div><span className="rp-no-renewal"><Check aria-hidden="true"/> One-time purchase</span></div>
      {illustrativePasses && <p className="rp-fixture-note">Design preview · Prices and validity below are from the supplied mock. They are illustrative, not live offers.</p>}
      <div className="rp-offer-grid" aria-busy={state === 'loading'}>
        {state === 'loading' ? <div className="rp-offer-state" role="status" data-testid="pricing-offers-loading"><Clock3 aria-hidden="true"/><h3>Finding your next chapter…</h3><p>Loading available Reading Passes.</p></div> : state === 'error' ? <div className="rp-offer-state" role="alert" data-testid="pricing-offers-error"><h3>A brief pause.</h3><p>We couldn’t load Reading Passes just now.</p><button className="rp-button" type="button" onClick={onRetry}>Try again</button></div> : state === 'empty' ? <div className="rp-offer-state" data-testid="pricing-offers-empty"><h3>The shelves are still here.</h3><p>No Reading Passes are available at the moment.</p><Link className="rp-button" to="/library">Explore the Library</Link></div> : offers.map((pack, index) => {
          const featured = pack.recommended === true || pack.is_recommended === true;
          return <article className={`rp-offer${featured ? ' is-featured' : ''}${selectedPackId === pack.id ? ' is-selected' : ''}`} key={pack.id} aria-labelledby={`rp-pack-${pack.id}`}>
            {featured && <span className="rp-featured-label">FEATURED PASS</span>}
            <h3 id={`rp-pack-${pack.id}`}>{pack.minutes.toLocaleString('en-IN')} Minutes</h3>
            <p className="rp-offer-poem">{['A little door into another world.', 'Room for a reading ritual.', 'Linger a little longer.', 'For stories that take their time.'][index % 4]}</p>
            <strong className="rp-price">{money(pack.price_inr)}</strong>
            <p className="rp-validity">{Number.isInteger(pack.validity_days) && pack.validity_days > 0 ? `Valid for ${pack.validity_days} days` : 'Purchased unused minutes do not expire'}</p>
            <ul><li><Check aria-hidden="true"/>{pack.minutes.toLocaleString('en-IN')} reading minutes</li><li><Check aria-hidden="true"/>Browse eligible reading editions</li><li><Check aria-hidden="true"/>No subscription or auto-renewal</li><li><Check aria-hidden="true"/>3-page previews where available</li></ul>
            <button className="rp-button" type="button" data-testid={`pricing-pack-${pack.id}`} onClick={() => onBuy?.(pack)} disabled={Boolean(busyId) || !canSelect || typeof onBuy !== 'function'}>{busyId === pack.id ? 'Opening checkout…' : !canSelect ? 'Currently unavailable' : `Choose ${pack.minutes.toLocaleString('en-IN')} Minutes`}</button>
            <small className="rp-unit-price">₹{pack.unitPrice} per minute</small>
          </article>;
        })}
      </div>
      <p className="rp-offer-footnote"><Clock3 aria-hidden="true"/>Your time, clearly counted. Reading minutes are used only while you read.</p>
    </section>

    <section className="rp-section rp-partnerships" aria-label="More ways to share stories">
      <article className="rp-partner rp-partner-institutions"><Landmark aria-hidden="true"/><div><span className="rp-coming-soon">Coming soon</span><h2>For Institutions</h2><p className="rp-partner-sub">Let a whole community turn the page.</p><p>Schools, colleges and libraries: begin a conversation about reading together.</p><Link className="rp-button" to="/contact?interest=institutional-access">Discuss institutional access</Link></div></article>
      <article className="rp-partner rp-partner-publishers"><Feather aria-hidden="true"/><div><span className="rp-coming-soon">Coming soon</span><h2>For Publishers</h2><p className="rp-partner-sub">Give a lasting story a new doorway.</p><p>Authors and rights holders: explore a thoughtful home for your editions.</p><Link className="rp-button" to="/contact?interest=publishing">Start a publishing conversation</Link></div></article>
      <article className="rp-partner rp-partner-gift"><Gift aria-hidden="true"/><div><span className="rp-coming-soon">Coming soon</span><h2>A Gift of Stories</h2><p className="rp-partner-sub">Some gifts stay long after the last page.</p><p>Interested in gifting reading time? Ask us what is available.</p><Link className="rp-button" to="/contact?interest=gifting">Ask about gifting</Link></div><img src={`${ART}gift.png`} width="240" height="200" alt="A black and gold Earnalism gift card, tied with a ribbon" loading="lazy"/></article>
    </section>
    <div className="rp-section rp-assurance" aria-label="Reading Pass essentials">
      <MiniFact icon={CreditCard} title="A clear choice">Price and validity together</MiniFact>
      <MiniFact icon={CirclePause} title="No auto-renewal">Another pass is your decision</MiniFact>
      <MiniFact icon={Clock3} title="Time to read">Minutes used while reading</MiniFact>
      <MiniFact icon={Eye} title="A first glimpse">3 pages where available</MiniFact>
      <MiniFact icon={Headphones} title="Listening">Audiobooks are unavailable in this launch</MiniFact>
    </div>

    <section className="rp-section rp-rhythm" aria-labelledby="rp-rhythm-title">
      <h2 id="rp-rhythm-title">Less to think about. More to get lost in.</h2><p className="rp-center-copy">A simple way to make space for stories.</p>
      <div className="rp-rhythm-grid">
        <article><Clock3 aria-hidden="true"/><h3>Your minutes</h3><p>A pass gives you reading time,<br/>across eligible editions.</p></article>
        <article><BookOpen aria-hidden="true"/><h3>Your curiosity</h3><p>Begin with a preview,<br/>where one is available.</p></article>
        <article><Heart aria-hidden="true"/><h3>Your own rhythm</h3><p>No recurring subscription.<br/>Choose when to come back.</p></article>
      </div>
    </section>

    <section className="rp-section rp-world" aria-labelledby="rp-world-title">
      <h2 id="rp-world-title">One pass. So many ways in.</h2>
      <div className="rp-capabilities">
        <MiniFact icon={BookOpen} title="Read">Find your next favourite among eligible editions.</MiniFact>
        <MiniFact icon={Headphones} title="Listen">Discover audio where an edition is available.</MiniFact>
        <MiniFact icon={Eye} title="Preview">Meet the first 3 pages before deciding.</MiniFact>
        <MiniFact icon={Languages} title="Explore">Follow stories through Bengali and English.</MiniFact>
      </div>
      <div className="rp-personas"><h2>For every kind of reading day.</h2><div className="rp-persona-grid">{PERSONAS.map(([image,title,description]) => <article key={image}><img src={`${ART}${image}.png`} alt="" width="116" height="125" loading="lazy"/><div><h3>{title}</h3><p>{description}</p></div></article>)}</div></div>
    </section>

    <section className="rp-section rp-questions" aria-labelledby="rp-questions-title"><h2 id="rp-questions-title">Before you turn the page.</h2><p className="rp-center-copy">A few things worth knowing.</p><div className="rp-faq-grid">{FAQ.map(([question,answer]) => <details key={question}><summary>{question}<ChevronDown aria-hidden="true"/></summary><p>{answer}</p></details>)}</div></section>
    <section className="rp-section rp-final" aria-labelledby="rp-final-title"><div><p className="rp-eyebrow">YOUR NEXT CHAPTER</p><h2 id="rp-final-title">A good story has a way<br/>of finding you.</h2><p>Wander the shelves. See what calls your name.</p><Link className="rp-button" to="/library">Explore the Library <ArrowRight aria-hidden="true"/></Link></div><img src={`${ART}books-phone.png`} width="179" height="126" alt="Classic editions beside an Earnalism reading screen" loading="lazy"/><p className="rp-final-aside">Your story<br/>awaits.</p></section>
  </div>;
}
