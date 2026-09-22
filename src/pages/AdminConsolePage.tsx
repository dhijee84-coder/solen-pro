import { useEffect } from 'react';
import Icons from '../components/Icons';
import ThemeToggle from '../components/ThemeToggle';

/**
 * AdminConsolePage — mirrors templates/admin/console.html verbatim.
 * Used for /admin/dashboard, /super-admin/dashboard, /primary-admin/dashboard.
 * The heavy lifting (role detection, nav, main content) is done by /static/js/console.js.
 */
export default function AdminConsolePage() {
  // Derive role label from the path — console.js will also read data-role
  const path = window.location.pathname;
  let role = 'ADMIN';
  let roleLabel = 'Admin';
  if (path.startsWith('/super-admin')) { role = 'SUPER_ADMIN'; roleLabel = 'Super Admin'; }
  if (path.startsWith('/primary-admin')) { role = 'PRIMARY_ADMIN'; roleLabel = 'Primary Admin'; }

  useEffect(() => {
    document.title = 'Operations — Solan';
  }, []);

  return (
    <>
      <Icons />
      <div id="shell" data-role={role}>
        <header className="fingers" style={{ borderBottom: '1px solid var(--edge)', padding: '12px 20px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap', background: 'var(--wafer2)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span style={{ width: 27, height: 27, border: '1px solid var(--flux)', borderRadius: 3, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--flux)' }}>
              <svg className="ico" style={{ width: 15, height: 15 }} viewBox="0 0 24 24"><use href="#i-sun" /></svg>
            </span>
            <span className="disp" style={{ fontWeight: 700, fontSize: 14 }}>SOL<span style={{ color: 'var(--flux)' }}>AN</span></span>
            <span className="mono pill p-live" style={{ marginLeft: 6 }}>{roleLabel}</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div style={{ position: 'relative' }}>
              <input id="global-search" className="field" placeholder="Search clients, panels, tickets…"
                style={{ width: 220, padding: '8px 12px', fontSize: 13 }} aria-label="Global search" />
              <div id="search-results" className="card pad" style={{ display: 'none', position: 'absolute', right: 0, top: 40, width: 320, zIndex: 30, maxHeight: 360, overflow: 'auto' }} />
            </div>
            <div style={{ textAlign: 'right', lineHeight: 1.25 }}>
              <div id="hdr-name" style={{ fontSize: 13, fontWeight: 500 }} />
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
          <nav id="rail"><div id="rail-nav" /></nav>
          <main id="main" />
        </div>
      </div>
      <div id="modal" />
      <script src="/static/js/common.js" />
      <script src="/static/js/console.js" />
    </>
  );
}
