import { useState } from 'react';
import Icons from '../components/Icons';
import ThemeToggle from '../components/ThemeToggle';

export default function LoginPage() {
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [name, setName] = useState('');
  const [phone, setPhone] = useState('');
  const [err, setErr] = useState('');
  const [otpOpen, setOtpOpen] = useState(false);
  const [otpPhone, setOtpPhone] = useState('');
  const [devOtp, setDevOtp] = useState('');
  const [otp, setOtp] = useState(['', '', '', '']);
  const [otpErr, setOtpErr] = useState('');

  async function sendCode() {
    const ph = phone.replace(/\D/g, '');
    setErr('');
    if (ph.length !== 10) { setErr('Enter a valid 10-digit mobile number.'); return; }
    try {
      const r = await fetch('/api/auth/otp/send', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ phone: ph }) });
      const d = await r.json();
      if (!r.ok) { setErr(d.detail || 'Failed to send OTP.'); return; }
      setOtpPhone(ph);
      setDevOtp(d.dev_otp || '');
      setOtpOpen(true);
    } catch { setErr('Network error. Try again.'); }
  }

  async function verifyOtp() {
    const code = otp.join('');
    setOtpErr('');
    if (code.length < 4) { setOtpErr('Enter all 4 digits.'); return; }
    try {
      const r = await fetch('/api/auth/otp/verify', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone: otpPhone, code, full_name: name }),
      });
      const d = await r.json();
      if (!r.ok) { setOtpErr(d.detail || 'Verification failed.'); return; }
      window.location.href = '/client/dashboard';
    } catch { setOtpErr('Network error. Try again.'); }
  }

  async function useDemoClient() {
    setErr('');
    try {
      await fetch('/api/auth/otp/send', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ phone: '9999999999' }) });
      const r = await fetch('/api/auth/otp/verify', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone: '9999999999', code: '1234', full_name: 'Demo Solar Customer' }),
      });
      const d = await r.json();
      if (!r.ok) { setErr(d.detail || 'Demo login failed. Run scripts/seed.py first.'); return; }
      window.location.href = '/client/dashboard';
    } catch { setErr('Demo login failed. Run scripts/seed.py first.'); }
  }

  function setOtpDigit(i: number, v: string) {
    const val = v.replace(/\D/g, '').slice(-1);
    const next = [...otp];
    next[i] = val;
    setOtp(next);
    if (val && i < 3) {
      document.getElementById(`otp-${i + 1}`)?.focus();
    }
  }

  return (
    <>
      <Icons />
      <div className="gate hero">
        <div className="gate-l">
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <span className="logo-mark">
                <svg className="ico" style={{ width: 18, height: 18 }} viewBox="0 0 24 24"><use href="#i-sun" /></svg>
              </span>
              <span className="disp" style={{ fontWeight: 700, fontSize: 17 }}>SOL<span style={{ color: 'var(--flux)' }}>AN</span></span>
            </div>
            <h1 className="disp" style={{ fontSize: 38, fontWeight: 600, marginTop: 34, lineHeight: 1.15, maxWidth: 480 }}>
              Buy farm panels. Pay for the energy they generate.
            </h1>
            <p style={{ color: 'var(--mute)', maxWidth: 440, marginTop: 14 }}>
              Solan builds solar parks on open land. You purchase panels. We install, maintain and operate everything — nothing goes on your roof. Track generation and usage billing in this portal.
            </p>
          </div>
          <div>
            <div className="eyebrow">Open-land farms · usage billing</div>
            <a href="/" style={{ fontSize: 12.5, color: 'var(--flux)', display: 'inline-block', marginTop: 10 }}>← Public website</a>
            <a href="/staff-login" style={{ fontSize: 12.5, color: 'var(--mute)', display: 'inline-block', marginTop: 10, marginLeft: 14 }}>Staff / admin sign in →</a>
          </div>
        </div>

        <div className="gate-r">
          <div style={{ width: '100%' }}>
            <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 16 }}><ThemeToggle /></div>
            <div className="seg" style={{ marginBottom: 26 }}>
              <button id="mode-login" className={mode === 'login' ? 'on' : ''} onClick={() => setMode('login')}>Sign in</button>
              <button id="mode-register" className={mode === 'register' ? 'on' : ''} onClick={() => setMode('register')}>Register</button>
            </div>
            <h2 className="disp" style={{ fontSize: 25, fontWeight: 600, marginBottom: 6 }}>
              {mode === 'register' ? 'Create your consumer account' : 'Sign in with your mobile'}
            </h2>
            <p style={{ color: 'var(--mute)', fontSize: 13.5, margin: '0 0 24px' }}>We send a 4-digit code by SMS. No passwords for client accounts.</p>

            {mode === 'register' && (
              <div style={{ marginBottom: 16 }}>
                <label className="lab" htmlFor="f-name">Name as printed on the electricity bill</label>
                <input id="f-name" className="field" placeholder="R. Vishwanath" value={name} onChange={e => setName(e.target.value)} />
              </div>
            )}

            <label className="lab" htmlFor="f-phone">Mobile number</label>
            <div style={{ display: 'flex', border: '1px solid var(--edge)', borderRadius: 3, background: 'var(--wafer2)' }}>
              <span className="mono" style={{ display: 'flex', alignItems: 'center', padding: '0 13px', color: 'var(--mute)', borderRight: '1px solid var(--edge)', fontSize: 14 }}>+91</span>
              <input
                id="f-phone" className="field" inputMode="numeric" maxLength={10} placeholder="98450 00000"
                style={{ border: 'none', background: 'transparent', letterSpacing: '.06em' }}
                value={phone} onChange={e => setPhone(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && sendCode()}
              />
            </div>
            {err && <div className="err">{err}</div>}

            <button className="btn flux wide" style={{ marginTop: 16 }} onClick={sendCode}>
              <svg className="ico" style={{ width: 16, height: 16 }} viewBox="0 0 24 24"><use href="#i-phone" /></svg> Send code
            </button>
            <p style={{ fontSize: 11.5, color: '#5C7794', marginTop: 18 }}>
              Development build — OTP is fixed at <span className="mono">1234</span> for every number.
            </p>
            <div style={{ marginTop: 20, paddingTop: 16, borderTop: '1px solid var(--edge)' }}>
              <div className="eyebrow" style={{ marginBottom: 8 }}>Demo account (development only)</div>
              <button className="btn sm wide" type="button" onClick={useDemoClient}
                style={{ background: 'var(--wafer2)', border: '1px solid var(--edge)', color: 'var(--ink)' }}>
                Use Demo Solar Customer
              </button>
              <p style={{ fontSize: 11, color: '#5C7794', marginTop: 8 }}>
                Mobile <span className="mono">9999999999</span> · OTP <span className="mono">1234</span>
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* OTP Modal */}
      {otpOpen && (
        <div id="otp-modal">
          <div className="modal-scrim" onClick={e => { if (e.target === e.currentTarget) setOtpOpen(false); }}>
            <div className="sheet rise">
              <div className="sheet-hd">
                <div>
                  <div className="disp" style={{ fontWeight: 600, fontSize: 16 }}>Enter the code</div>
                  <div style={{ color: 'var(--mute)', fontSize: 12.5 }}>Sent to +91 {otpPhone} · dev code is {devOtp}</div>
                </div>
                <button className="btn sm bare" onClick={() => setOtpOpen(false)}>✕</button>
              </div>
              <div className="sheet-body">
                <div style={{ display: 'flex', gap: 8, justifyContent: 'center', margin: '10px 0 16px' }}>
                  {[0, 1, 2, 3].map(i => (
                    <input
                      key={i}
                      id={`otp-${i}`}
                      className="otpbox"
                      maxLength={1}
                      inputMode="numeric"
                      value={otp[i]}
                      onChange={e => setOtpDigit(i, e.target.value)}
                    />
                  ))}
                </div>
                {otpErr && <div className="err" style={{ textAlign: 'center' }}>{otpErr}</div>}
                <button className="btn flux wide" onClick={verifyOtp}>Verify &amp; continue</button>
              </div>
            </div>
          </div>
        </div>
      )}
      <script src="/static/js/common.js" />
    </>
  );
}
