import { useEffect, useState } from 'react';
import PublicLayout from '../components/PublicLayout';

interface Faq { question: string; answer: string; }

export default function FaqPage() {
  const [faqs, setFaqs] = useState<Faq[] | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const r = await fetch('/api/public/faqs');
        if (r.ok) setFaqs(await r.json());
        else setError(true);
      } catch { setError(true); }
    })();
  }, []);

  return (
    <PublicLayout title="FAQ — Solan">
      <section className="page-hero" style={{ backgroundImage: "linear-gradient(90deg,rgba(15,23,42,.82),rgba(15,23,42,.35)),url('/static/img/hero-plant.jpg')" }}>
        <div className="page-hero-inner">
          <p className="eyebrow">HELP</p>
          <h1 className="disp">Frequently asked questions</h1>
        </div>
      </section>
      <section className="pub-section">
        <p className="sub">How panel purchase, farm operations and usage billing work. Contact us if your question is not listed.</p>
        <div id="faq-list">
          {faqs === null && !error && <p className="muted">Loading…</p>}
          {error && <p className="muted">Unable to load FAQs.</p>}
          {faqs !== null && faqs.length === 0 && <p className="muted">FAQs will appear here once published.</p>}
          {faqs && faqs.map((f, i) => (
            <details key={i} className="faq-item">
              <summary>{f.question}</summary>
              <p>{f.answer}</p>
            </details>
          ))}
        </div>
      </section>
    </PublicLayout>
  );
}
