import { useEffect, useState } from 'react';
import PublicLayout from '../components/PublicLayout';

interface Service { name: string; description?: string; }

export default function ServicesPage() {
  const [services, setServices] = useState<Service[] | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const r = await fetch('/api/public/services');
        if (r.ok) setServices(await r.json());
        else setError(true);
      } catch { setError(true); }
    })();
  }, []);

  return (
    <PublicLayout title="Services — Solan">
      <section className="page-hero" style={{ backgroundImage: "linear-gradient(90deg,rgba(15,23,42,.82),rgba(15,23,42,.35)),url('/static/img/hero-farm.jpg')" }}>
        <div className="page-hero-inner">
          <p className="eyebrow">SERVICES</p>
          <h1 className="disp">We operate. You own the panels.</h1>
        </div>
      </section>
      <section className="pub-section">
        <p className="sub">Farm operations, maintenance and support for clients who have purchased Solan panels. No rooftop installation services — we do not work on houses.</p>
        <div className="pub-grid" id="svc-list">
          {services === null && !error && <p className="muted">Loading…</p>}
          {error && <p className="muted">Unable to load services.</p>}
          {services !== null && services.length === 0 && <p className="muted">No public services listed yet.</p>}
          {services && services.map((s, i) => (
            <div key={i} className="pub-card"><h3>{s.name}</h3><p>{s.description || ''}</p></div>
          ))}
        </div>
      </section>
    </PublicLayout>
  );
}
