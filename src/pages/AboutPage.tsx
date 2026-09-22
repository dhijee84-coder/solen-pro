import { useEffect, useState } from 'react';
import PublicLayout from '../components/PublicLayout';

export default function AboutPage() {
  const [body, setBody] = useState('Solan develops solar farms on empty land. Clients buy panels at those farms. We install, maintain and operate the plant. You never host equipment on your house — you buy capacity, then pay for the energy those panels generate.');
  const [mission, setMission] = useState('Let people own solar capacity without rooftop construction. Fair panel sales, farm-side operations, usage-based energy billing.');
  const [vision, setVision] = useState('A trusted farm operator: our land, your panels, our maintenance, your generation.');

  useEffect(() => {
    (async () => {
      try {
        const s = await fetch('/api/public/settings').then(r => r.json());
        if (s.about_body) setBody(s.about_body);
        if (s.about_mission) setMission(s.about_mission);
        if (s.about_vision) setVision(s.about_vision);
      } catch {}
    })();
  }, []);

  return (
    <PublicLayout title="About Us — Solan">
      <section className="page-hero" style={{ backgroundImage: "linear-gradient(90deg,rgba(15,23,42,.82),rgba(15,23,42,.35)),url('/static/img/hero-farm.jpg')" }}>
        <div className="page-hero-inner">
          <p className="eyebrow">ABOUT US</p>
          <h1 className="disp">Solar farms on open land. Panels you own.</h1>
        </div>
      </section>
      <section className="pub-section">
        <div className="intro-grid">
          <div><img src="/static/img/hero-plant.jpg" alt="Solan farm operations" /></div>
          <div>
            <p className="eyebrow blue">WHO WE ARE</p>
            <h2 className="disp">Solan</h2>
            <p className="sub" style={{ marginBottom: 0 }}>{body}</p>
          </div>
        </div>
        <div className="pub-grid" style={{ marginTop: 48 }}>
          <div className="pub-card"><h3>Mission</h3><p>{mission}</p></div>
          <div className="pub-card"><h3>Vision</h3><p>{vision}</p></div>
          <div className="pub-card"><h3>What we do not do</h3><p>We do not mount panels on homes, factories or rooftops. All hardware stays on Solan farms.</p></div>
        </div>
      </section>
    </PublicLayout>
  );
}
