import { useState } from 'react';
import Icons from '../components/Icons';
import ThemeToggle from '../components/ThemeToggle';

export default function StaffLoginPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [err, setErr] = useState('');

  async function doLogin() {
    setErr('');
    try {
      const r = await fetch('/api/auth/admin/login', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      });
      const d = await r.json();
      if (!r.ok) { setErr(d.detail || 'Login failed.'); return; }
      const role = d.user?.role;
      if (role === 'PRIMARY_ADMIN') window.location.href = '/primary-admin/dashboard';
      else if (role === 'SUPER_ADMIN') window.location.href = '/super-admin/dashboard';
      else window.location.href = '/admin/dashboard';
    } catch { setErr('Network error. Try again.'); }
  }

  return (
    <>
      <Icons />
      <div className="gate hero">
        <div className="gate-l">
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span className="logo-mark">
              <svg className="ico" style={{ width: 18, height: 18 }} viewBox="0 0 24 24"><use href="#i-sun" /></svg>
            </span>
            <span className="disp" style={{ fontWeight: 700, fontSize: 17 }}>SOL<span style={{ color: 'var(--flux)' }}>AN</span></span>
          </div>
          <div>
            <div className="eyebrow">Operations console</div>
            <a href="/" style={{ fontSize: 12.5, color: 'var(--flux)', display: 'inline-block', marginTop: 10 }}>← Public website</a>
            <a href="/login" style={{ fontSize: 12.5, color: 'var(--mute)', display: 'inline-block', marginTop: 10, marginLeft: 14 }}>Client sign in →</a>
          </div>
        </div>

        <div className="gate-r">
          <div style={{ width: '100%' }}>
            <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 16 }}><ThemeToggle /></div>
            <h2 className="disp" style={{ fontSize: 25, fontWeight: 600, marginBottom: 6 }}>Admin sign in</h2>
            <p style={{ color: 'var(--mute)', fontSize: 13.5, margin: '0 0 24px' }}>For Admin, Super Admin and Primary Admin accounts.</p>
            <label className="lab" htmlFor="f-user">Username</label>
            <input id="f-user" className="field" placeholder="admin" style={{ marginBottom: 14 }} value={username} onChange={e => setUsername(e.target.value)} />
            <label className="lab" htmlFor="f-pass">Password</label>
            <input id="f-pass" type="password" className="field" placeholder="••••••••" value={password}
              onChange={e => setPassword(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && doLogin()} />
            {err && <div className="err">{err}</div>}
            <button className="btn flux wide" style={{ marginTop: 16 }} onClick={doLogin}>Sign in</button>
            <div className="card pad" style={{ marginTop: 22, fontSize: 12.5, color: 'var(--mute)' }}>
              <div className="eyebrow" style={{ marginBottom: 8 }}>Seeded development accounts</div>
              <div className="mono">primary / ChangeMe123!</div>
              <div className="mono">superadmin / ChangeMe123!</div>
              <div className="mono">admin / ChangeMe123!</div>
            </div>
          </div>
        </div>
      </div>
      <script src="/static/js/common.js" />
    </>
  );
}
