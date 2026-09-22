import PublicLayout from '../components/PublicLayout';

export default function SolarPage() {
  return (
    <PublicLayout title="Our Farms — Solan">
      <section className="page-hero" style={{ backgroundImage: "linear-gradient(90deg,rgba(15,23,42,.82),rgba(15,23,42,.35)),url('/static/img/hero-cells.jpg')" }}>
        <div className="page-hero-inner">
          <p className="eyebrow">OUR FARMS</p>
          <h1 className="disp">Buy panels. We keep them running.</h1>
        </div>
      </section>
      <section className="pub-section">
        <p className="sub">Every Solan site is a company-operated solar farm on open land. You purchase modules from inventory. We commission them on our rows, maintain them, and bill energy from their generation.</p>
        <div className="solution-grid">
          <article className="solution-card">
            <img src="/static/img/hero-cells.jpg" alt="Solar modules" />
            <div><h3>Panel purchase</h3><p>Serial-tracked modules with warranty. You buy capacity; title of the panel is yours.</p></div>
          </article>
          <article className="solution-card">
            <img src="/static/img/hero-farm.jpg" alt="Open-land farm" />
            <div><h3>Open-land farms</h3><p>No rooftop, no house work. Panels sit on Solan land we already operate.</p></div>
          </article>
          <article className="solution-card">
            <img src="/static/img/hero-plant.jpg" alt="Operations" />
            <div><h3>Usage energy</h3><p>Generation is metered from your panels. You pay for the energy they produce.</p></div>
          </article>
        </div>
        <div className="pub-grid" style={{ marginTop: 28 }}>
          <div className="pub-card"><h3>We install</h3><p>Farm-side mounting, cabling, inspection and grid connection — all by Solan crews.</p></div>
          <div className="pub-card"><h3>We maintain</h3><p>Cleaning, repairs, warranty claims and plant availability stay our responsibility.</p></div>
          <div className="pub-card"><h3>You monitor</h3><p>Daily generation, payments and tickets live in the client portal after login.</p></div>
        </div>
      </section>
    </PublicLayout>
  );
}
