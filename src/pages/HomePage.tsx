import { useEffect, useRef, useState } from 'react';
import PublicLayout from '../components/PublicLayout';

const esc = (s: unknown) =>
  String(s ?? '').replace(/[&<>"']/g, (c) =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c] || c)
  );

const HERO_SLIDES = [
  {
    kicker: 'SOLAN',
    title: 'You buy the panels.<br>We run the farm.',
    body: 'Solan builds solar parks on <b>open land</b>. Clients purchase panels. We install, maintain and operate everything.',
    image: '/static/img/hero-farm.jpg',
    cta: 'See our farms',
    href: '/projects',
  },
  {
    kicker: 'NO ROOFTOP',
    title: 'Energy billed on<br>what you use',
    body: 'Your panels stay on our site. You track generation in the portal and pay for the energy those panels produce.',
    image: '/static/img/hero-plant.jpg',
    cta: 'How it works',
    href: '/how-it-works',
  },
  {
    kicker: 'WE MAINTAIN',
    title: 'Own solar without<br>owning a roof',
    body: 'Cleaning, repairs, warranty and grid operations are Solan\'s job. You own the capacity — not the construction risk.',
    image: '/static/img/hero-cells.jpg',
    cta: 'Buy panels',
    href: '/login',
  },
];

interface Project { name: string; location?: string; capacity_kw: number; status: string; description?: string; }
interface Service { name: string; description?: string; }

export default function HomePage() {
  const [slideIdx, setSlideIdx] = useState(0);
  const [projects, setProjects] = useState<Project[] | null>(null);
  const [services, setServices] = useState<Service[] | null>(null);
  const [aboutBlurb, setAboutBlurb] = useState('');
  const [showProjects, setShowProjects] = useState(true);
  const [showServices, setShowServices] = useState(true);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  function goTo(i: number) {
    setSlideIdx(i);
    if (timerRef.current) clearInterval(timerRef.current);
    timerRef.current = setInterval(() => setSlideIdx(n => (n + 1) % HERO_SLIDES.length), 7000);
  }

  useEffect(() => {
    timerRef.current = setInterval(() => setSlideIdx(n => (n + 1) % HERO_SLIDES.length), 7000);
    (async () => {
      try {
        const s = await fetch('/api/public/settings').then(r => r.json());
        if (s.section_projects === 'off') setShowProjects(false);
        if (s.section_services === 'off') setShowServices(false);
        if (s.about_body) setAboutBlurb(s.about_body);
      } catch {}
      try {
        const p = await fetch('/api/public/projects').then(r => r.json());
        setProjects(p);
      } catch { setProjects([]); }
      try {
        const sv = await fetch('/api/public/services').then(r => r.json());
        setServices(sv);
      } catch { setServices([]); }
    })();
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, []);

  const slide = HERO_SLIDES[slideIdx];

  return (
    <PublicLayout title="Solan — Buy panels on our farm. Pay for the energy you use.">
      {/* Hero */}
      <section
        id="top"
        className="acme-hero"
        style={{ backgroundImage: `linear-gradient(90deg, rgba(15,23,42,.78), rgba(15,23,42,.18)), url('${slide.image}')` }}
      >
        <button className="hero-arrow left" type="button" onClick={() => goTo((slideIdx + HERO_SLIDES.length - 1) % HERO_SLIDES.length)} aria-label="Previous slide">‹</button>
        <div className="acme-hero-copy">
          <p className="eyebrow">{slide.kicker}</p>
          <h1 dangerouslySetInnerHTML={{ __html: slide.title }} />
          <p dangerouslySetInnerHTML={{ __html: slide.body }} />
          <a className="pill-button" href={slide.href}>{slide.cta}</a>
        </div>
        <button className="hero-arrow right" type="button" onClick={() => goTo((slideIdx + 1) % HERO_SLIDES.length)} aria-label="Next slide">›</button>
        <div className="dots">
          {HERO_SLIDES.map((_, n) => (
            <button key={n} type="button" className={n === slideIdx ? 'active' : ''} onClick={() => goTo(n)} aria-label={`Go to slide ${n + 1}`} />
          ))}
        </div>
      </section>

      {/* Who we are */}
      <section className="pub-section">
        <div className="intro-grid">
          <div><img src="/static/img/hero-farm.jpg" alt="Solan solar farm on open land" /></div>
          <div>
            <p className="eyebrow blue">WHO WE ARE</p>
            <h2 className="disp">Solan</h2>
            <p id="about-blurb">{aboutBlurb || 'Solan is not a rooftop installer. We develop solar farms on empty land, sell panel capacity to clients, and keep the plant running. Your panels stay on our site. Your portal shows generation, usage billing, warranty and support.'}</p>
            <p>No work on your house. No roof mounting. We own the land and the operations. You own the panels and the energy they produce.</p>
            <a className="text-link" href="/about" style={{ color: 'var(--sky)', fontWeight: 700, display: 'inline-block', marginTop: 16 }}>Know more →</a>
          </div>
        </div>
      </section>

      {/* Business model */}
      <section id="business" className="portfolio-band">
        <div className="portfolio-inner">
          <div className="portfolio-copy">
            <p className="eyebrow blue">THE MODEL</p>
            <h2 className="disp">Energy billed on usage</h2>
            <p className="muted">Buy a block of panels at a Solan farm. We commission and maintain them. You see daily generation and pay for the energy those panels actually produce.</p>
            <div className="metrics">
              <div><strong>Our land</strong><span>Farms on open sites</span></div>
              <div><strong>Your panels</strong><span>Purchased capacity</span></div>
              <div><strong>Our ops</strong><span>Install + maintenance</span></div>
            </div>
          </div>
          <img src="/static/img/hero-plant.jpg" alt="Solan plant operations" />
        </div>
      </section>

      {/* Solution cards */}
      <section className="pub-section">
        <div className="section-heading">
          <p className="eyebrow blue">WHAT WE DO</p>
          <h2 className="disp">Farm-side solar, end to end</h2>
        </div>
        <div className="solution-grid">
          <article className="solution-card">
            <img src="/static/img/hero-cells.jpg" alt="Photovoltaic modules" />
            <div><h3>Panel sales</h3><p>Buy serial-tracked modules from live farm inventory. Capacity is allocated fairly from available stock.</p><a href="/solar">Learn more →</a></div>
          </article>
          <article className="solution-card">
            <img src="/static/img/hero-farm.jpg" alt="Open-land solar farm" />
            <div><h3>Farm operations</h3><p>We install, inspect, connect and maintain every panel on our land. Nothing is mounted on your house.</p><a href="/how-it-works">Learn more →</a></div>
          </article>
          <article className="solution-card">
            <img src="/static/img/hero-plant.jpg" alt="Generation monitoring" />
            <div><h3>Usage billing</h3><p>Track generation from your panels and pay for the energy used. Warranty and tickets stay in your portal.</p><a href="/login">Client login →</a></div>
          </article>
        </div>
      </section>

      {/* Impact band */}
      <section className="impact-band">
        <div className="pub-section" style={{ paddingBottom: 36 }}>
          <div className="section-heading">
            <p className="eyebrow blue">WHY SOLAN</p>
            <h2 className="disp">Own solar without owning a rooftop</h2>
          </div>
        </div>
        <div className="impact-grid">
          <div className="impact-stat"><strong>Open land</strong><p>Farms built on empty sites we operate</p></div>
          <div className="impact-stat"><strong>No rooftop</strong><p>Nothing installed on your house</p></div>
          <div className="impact-stat"><strong>We maintain</strong><p>Cleaning, repairs and warranty by Solan</p></div>
          <div className="impact-stat"><strong>Usage billed</strong><p>Pay for energy your panels generate</p></div>
          <div className="impact-stat"><strong>Portal</strong><p>KYC, payments, generation, support</p></div>
        </div>
      </section>

      {/* Public projects */}
      {showProjects && (
        <section className="pub-section" id="public-projects-section">
          <div className="section-heading">
            <p className="eyebrow blue">FARMS</p>
            <h2 className="disp">Public solar sites</h2>
          </div>
          <p className="sub" style={{ marginLeft: 'auto', marginRight: 'auto', textAlign: 'center' }}>Only farms marked public are listed. Private client and payment data stays in the portal.</p>
          <div className="pub-grid" id="home-projects">
            {projects === null && <p className="muted">Loading farms…</p>}
            {projects !== null && projects.length === 0 && <p className="muted">Public farms will appear here when published.</p>}
            {projects && projects.slice(0, 3).map((p, i) => (
              <div key={i} className="pub-card">
                <h3>{p.name}</h3>
                <p>{p.location || ''} · {p.capacity_kw} kW · {p.status}</p>
                <p style={{ marginTop: 8 }}>{p.description || ''}</p>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Public services */}
      {showServices && (
        <section className="pub-section" id="public-services-section" style={{ paddingTop: 0 }}>
          <div className="section-heading">
            <p className="eyebrow blue">SERVICES</p>
            <h2 className="disp">What we operate for you</h2>
          </div>
          <div className="pub-grid" id="home-services">
            {services === null && <p className="muted">Loading services…</p>}
            {services !== null && services.length === 0 && <p className="muted">Services coming soon.</p>}
            {services && services.map((s, i) => (
              <div key={i} className="pub-card"><h3>{s.name}</h3><p>{s.description || ''}</p></div>
            ))}
          </div>
        </section>
      )}

      {/* CTA band */}
      <section id="contact" className="cta-band">
        <p className="eyebrow">GET IN TOUCH</p>
        <h2 className="disp">Ready to buy farm panels?</h2>
        <p className="muted">Create a client account or talk to us about capacity at an active Solan site.</p>
        <a className="pill-button" href="/contact">Reach out</a>
        <div style={{ marginTop: 16 }}><a className="btn" href="/login">Client Login / Register</a></div>
      </section>
    </PublicLayout>
  );
}
