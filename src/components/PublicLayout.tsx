import { useEffect, useState, ReactNode } from 'react';
import Icons from './Icons';
import ThemeToggle from './ThemeToggle';

interface Settings {
  company_email?: string;
  support_email?: string;
  company_phone?: string;
  support_phone?: string;
  footer_text?: string;
  brand_logo_url?: string;
  brand_favicon_url?: string;
  section_projects?: string;
  section_services?: string;
}

interface Announcement {
  title: string;
  message: string;
  cta_url?: string;
  cta_text?: string;
}

const esc = (s: unknown) =>
  String(s ?? '').replace(/[&<>"']/g, (c) =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c] || c)
  );

export default function PublicLayout({ children, title }: { children: ReactNode; title?: string }) {
  const [settings, setSettings] = useState<Settings>({});
  const [announcement, setAnnouncement] = useState<Announcement | null>(null);
  const [navOpen, setNavOpen] = useState(false);

  useEffect(() => {
    if (title) document.title = title;
    (async () => {
      try {
        const res = await fetch('/api/public/settings');
        if (res.ok) setSettings(await res.json());
      } catch {}
      try {
        const res = await fetch('/api/public/announcements');
        if (res.ok) {
          const anns: Announcement[] = await res.json();
          if (anns.length) setAnnouncement(anns[0]);
        }
      } catch {}
    })();
  }, [title]);

  const year = new Date().getFullYear();
  const email = settings.support_email || settings.company_email || 'hello@solan.local';
  const phone = settings.support_phone || settings.company_phone || '+91 44 4000 1234';
  const footerText =
    settings.footer_text ||
    'We own the land and the farm. You own the panels. We maintain everything and bill energy on usage.';

  return (
    <>
      <Icons />

      {announcement && (
        <div id="ann-banner" className="pub-ann">
          <strong>{announcement.title}</strong>{' '}
          <span>{announcement.message}</span>{' '}
          {announcement.cta_url && (
            <a href={esc(announcement.cta_url)}>{announcement.cta_text || 'Learn more'}</a>
          )}
        </div>
      )}

      <header className="pub-header">
        <div className="pub-header-inner">
          <a href="/" className="pub-logo">
            <span className="pub-logo-mark" id="logo-mark">
              {settings.brand_logo_url ? (
                <img src={settings.brand_logo_url} alt="" style={{ width: '100%', height: '100%', objectFit: 'contain' }} />
              ) : (
                <svg className="ico" viewBox="0 0 24 24"><use href="#i-sun" /></svg>
              )}
            </span>
            <span className="disp">SOL<span className="flux">AN</span></span>
          </a>

          <nav className={`pub-nav${navOpen ? ' open' : ''}`} id="pub-nav">
            <a href="/about">About Us</a>
            <a href="/solar">Our Farms</a>
            <a href="/how-it-works">How it works</a>
            <a href="/services">Services</a>
            <a href="/projects">Projects</a>
            <a href="/faq">FAQ</a>
            <a href="/contact">Contact Us</a>
            <a className="nav-mobile-only" href="/login">Client Login</a>
            <a className="nav-mobile-only" href="/staff-login">Staff Login</a>
          </nav>

          <div className="pub-header-actions">
            <ThemeToggle />
            <a className="btn sm hide-sm" href="/staff-login">Staff</a>
            <a className="btn flux sm" href="/login">Client Login</a>
            <button
              className="pub-menu-btn"
              type="button"
              onClick={() => setNavOpen(o => !o)}
              aria-label="Menu"
            >☰</button>
          </div>
        </div>
      </header>

      <main>{children}</main>

      <footer className="pub-footer" id="media">
        <div className="pub-footer-inner">
          <div>
            <div className="disp" style={{ fontWeight: 700, fontSize: 16, marginBottom: 8 }}>
              SOL<span className="flux">AN</span>
            </div>
            <p className="muted" id="footer-text">{footerText}</p>
          </div>
          <div>
            <div className="eyebrow">Explore</div>
            <a href="/about">About Us</a>
            <a href="/solar">Our Farms</a>
            <a href="/how-it-works">How it works</a>
            <a href="/projects">Projects</a>
          </div>
          <div>
            <div className="eyebrow">Portals</div>
            <a href="/login">Client Login</a>
            <a href="/staff-login">Staff Login</a>
            <a href="/faq">FAQ</a>
            <a href="/contact">Contact Us</a>
          </div>
          <div>
            <div className="eyebrow">Contact</div>
            <p className="muted">{email}</p>
            <p className="muted">{phone}</p>
          </div>
        </div>
        <div className="pub-footer-bottom">
          <span>© {year} Solan. All rights reserved.</span>
        </div>
      </footer>

      <CookieBar />
      <script src="/static/js/common.js" />
    </>
  );
}

function CookieBar() {
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    try {
      if (!localStorage.getItem('ss_cookie')) setVisible(true);
    } catch {}
  }, []);

  function accept() {
    try { localStorage.setItem('ss_cookie', '1'); } catch {}
    setVisible(false);
  }

  if (!visible) return null;
  return (
    <div className="cookie">
      <p>This website uses cookies to keep the site working and remember your preferences.</p>
      <div>
        <button type="button" onClick={accept}>Accept</button>
        <button type="button" onClick={accept}>Decline</button>
      </div>
    </div>
  );
}
