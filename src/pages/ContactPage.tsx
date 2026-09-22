import { useState } from 'react';
import PublicLayout from '../components/PublicLayout';

export default function ContactPage() {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [subject, setSubject] = useState('');
  const [message, setMessage] = useState('');
  const [err, setErr] = useState('');
  const [ok, setOk] = useState('');

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setErr(''); setOk('');
    try {
      const r = await fetch('/api/public/contact', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, email, phone, subject, message }),
      });
      const data = await r.json();
      if (!r.ok) { setErr(data.detail || 'Could not send. Please try again.'); return; }
      setOk(data.message || 'Thank you. We received your message.');
      setName(''); setEmail(''); setPhone(''); setSubject(''); setMessage('');
    } catch { setErr('Could not send. Please try again.'); }
  }

  return (
    <PublicLayout title="Contact Us — Solan">
      <section className="page-hero" style={{ backgroundImage: "linear-gradient(90deg,rgba(15,23,42,.82),rgba(15,23,42,.35)),url('/static/img/hero-farm.jpg')" }}>
        <div className="page-hero-inner">
          <p className="eyebrow">GET IN TOUCH</p>
          <h1 className="disp">Talk to Solan</h1>
        </div>
      </section>
      <section className="pub-section">
        <p className="sub">Ask about buying farm panels or energy billing. Existing clients should use support tickets after login.</p>
        <form className="contact-form" onSubmit={submit}>
          <label className="lab">Name</label>
          <input className="field" required maxLength={150} placeholder="Your name" value={name} onChange={e => setName(e.target.value)} />
          <label className="lab">Email</label>
          <input className="field" type="email" required maxLength={150} placeholder="you@example.com" value={email} onChange={e => setEmail(e.target.value)} />
          <label className="lab">Phone</label>
          <input className="field" maxLength={20} placeholder="+91 …" value={phone} onChange={e => setPhone(e.target.value)} />
          <label className="lab">Subject</label>
          <input className="field" maxLength={200} placeholder="How can we help?" value={subject} onChange={e => setSubject(e.target.value)} />
          <label className="lab">Message</label>
          <textarea className="field" required maxLength={5000} placeholder="Tell us a bit more…" value={message} onChange={e => setMessage(e.target.value)} />
          {err && <div className="err">{err}</div>}
          {ok && <div style={{ color: 'var(--export)', fontSize: 13, marginBottom: 8 }}>{ok}</div>}
          <button className="pill-button" type="submit" style={{ marginTop: 8, border: 0, cursor: 'pointer' }}>Send message</button>
        </form>
      </section>
    </PublicLayout>
  );
}
