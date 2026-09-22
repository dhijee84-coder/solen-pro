import { useEffect } from 'react';
import Icons from '../components/Icons';
import ThemeToggle from '../components/ThemeToggle';

/**
 * ClientDashboardPage — mirrors templates/client/dashboard.html verbatim.
 * The heavy lifting is done by /static/js/client.js which is loaded below.
 * React is used only to render the identical HTML skeleton.
 */
export default function ClientDashboardPage() {
  useEffect(() => {
    document.title = 'My panels — Solan';
    // client.js expects the DOM to be ready; it self-executes after load
  }, []);

  return (
    <>
      <Icons />
      <div id="shell">
        <header className="fingers" style={{ borderBottom: '1px solid var(--edge)', padding: '12px 20px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap', background: 'var(--wafer2)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span style={{ width: 27, height: 27, border: '1px solid var(--flux)', borderRadius: 3, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--flux)' }}>
              <svg className="ico" style={{ width: 15, height: 15 }} viewBox="0 0 24 24"><use href="#i-sun" /></svg>
            </span>
            <span className="disp" style={{ fontWeight: 700, fontSize: 14 }}>SOL<span style={{ color: 'var(--flux)' }}>AN</span></span>
            <span id="hdr-rr" className="mono" style={{ fontSize: 11, color: 'var(--mute)', borderLeft: '1px solid var(--edge2)', paddingLeft: 12, marginLeft: 4, display: 'none' }} />
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <button id="hdr-alert" className="btn sm" style={{ display: 'none', borderColor: 'var(--flux)', color: 'var(--flux)' }}>
              <svg className="ico" style={{ width: 14, height: 14 }} viewBox="0 0 24 24"><use href="#i-bell" /></svg> Payment due
            </button>
            <div style={{ textAlign: 'right', lineHeight: 1.25 }}>
              <div id="hdr-name" style={{ fontSize: 13, fontWeight: 500 }} />
              <div id="hdr-phone" className="mono" style={{ fontSize: 11, color: 'var(--mute)' }} />
            </div>
            <ThemeToggle />
            <button className="btn sm" aria-label="Sign out" style={{ padding: 8 }}
              onClick={async () => {
                try { await fetch('/api/auth/logout', { method: 'POST' }); } catch {}
                window.location.href = '/login';
              }}>
              <svg className="ico" style={{ width: 14, height: 14 }} viewBox="0 0 24 24"><use href="#i-out" /></svg>
            </button>
          </div>
        </header>
        <div id="body-row">
          <nav id="rail">
            <div className="rail-sec eyebrow" style={{ padding: '4px 12px 10px' }}>Your connection</div>
            <div id="rail-nav" />
            <div className="rail-sec" style={{ marginTop: 20, paddingTop: 16, borderTop: '1px solid var(--edge)' }}>
              <div className="eyebrow" style={{ padding: '0 12px 10px' }}>Onboarding</div>
              <div id="rail-onboarding" />
            </div>
          </nav>
          <main id="main" />
        </div>
      </div>
      <div id="modal" />
      {/* client.js is the SPA engine for the client dashboard */}
      <script src="/static/js/common.js" />
      <script src="/static/js/client.js" />
    </>
  );
}
