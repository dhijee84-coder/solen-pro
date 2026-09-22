import { useEffect, useState } from 'react';
import PublicLayout from '../components/PublicLayout';

interface Project { name: string; location?: string; capacity_kw: number; total_panels?: number; status: string; description?: string; }

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[] | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const r = await fetch('/api/public/projects');
        if (r.ok) setProjects(await r.json());
        else setError(true);
      } catch { setError(true); }
    })();
  }, []);

  return (
    <PublicLayout title="Projects — Solan">
      <section className="page-hero" style={{ backgroundImage: "linear-gradient(90deg,rgba(15,23,42,.82),rgba(15,23,42,.35)),url('/static/img/hero-farm.jpg')" }}>
        <div className="page-hero-inner">
          <p className="eyebrow">SOLAR FARMS</p>
          <h1 className="disp">Open-land sites you can buy into</h1>
        </div>
      </section>
      <section className="pub-section">
        <p className="sub">Public Solan farms only. Panels are sold from these sites. Private client, payment and document data is never shown here.</p>
        <div className="pub-grid" id="prj-list">
          {projects === null && !error && <p className="muted">Loading…</p>}
          {error && <p className="muted">Unable to load farms.</p>}
          {projects !== null && projects.length === 0 && <p className="muted">No public farms published yet.</p>}
          {projects && projects.map((p, i) => (
            <div key={i} className="pub-card">
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
                <h3 style={{ margin: 0 }}>{p.name}</h3>
                <span className="pill p-live">{p.status}</span>
              </div>
              <p style={{ marginTop: 8 }}>{p.location || '—'} · {p.capacity_kw} kW{p.total_panels ? ` · ${p.total_panels} panels` : ''}</p>
              <p style={{ marginTop: 8 }}>{p.description || ''}</p>
            </div>
          ))}
        </div>
      </section>
    </PublicLayout>
  );
}
