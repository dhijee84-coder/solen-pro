import PublicLayout from '../components/PublicLayout';

const STEPS = [
  { title: 'Register', body: 'Create a client account with your mobile number and OTP.' },
  { title: 'Complete KYC', body: 'PAN and Aadhaar so panel ownership is in your name.' },
  { title: 'Share usage', body: 'Electricity bill details help size how many farm panels you need.' },
  { title: 'Choose a farm', body: 'You are linked to an active Solan site on open land.' },
  { title: 'Buy panels', body: 'Available modules are allocated from farm inventory (first-in, first-out).' },
  { title: 'We install on our land', body: 'Solan crews mount, cable and commission your panels at the farm — never on your roof.' },
  { title: 'Pay for the panels', body: 'Milestone payments for the purchase; farm work stays our job.' },
  { title: 'Grid & handover', body: 'Inspection and grid connection at the farm. You receive generation rights.' },
  { title: 'Energy on usage', body: 'Track daily generation. You are billed for the energy your panels produce.' },
  { title: 'We maintain', body: 'Cleaning, repairs, warranty claims and support are handled by Solan.' },
];

export default function HowItWorksPage() {
  return (
    <PublicLayout title="How it works — Solan">
      <section className="page-hero" style={{ backgroundImage: "linear-gradient(90deg,rgba(15,23,42,.82),rgba(15,23,42,.35)),url('/static/img/hero-plant.jpg')" }}>
        <div className="page-hero-inner">
          <p className="eyebrow">THE JOURNEY</p>
          <h1 className="disp">How Solan works</h1>
        </div>
      </section>
      <section className="pub-section">
        <p className="sub">You buy panels on our farm. We run the plant. You pay for the energy those panels generate. Nothing is installed on your house.</p>
        <div className="pub-steps">
          {STEPS.map((s, i) => (
            <div key={i} className="pub-step">
              <div><strong>{s.title}</strong><p className="muted">{s.body}</p></div>
            </div>
          ))}
        </div>
        <p style={{ marginTop: 24 }}><a className="pill-button" href="/login">Start as a client</a></p>
      </section>
    </PublicLayout>
  );
}
