// Mirrors templates/partials/theme_toggle.html
export default function ThemeToggle() {
  function toggleTheme() {
    const html = document.documentElement;
    const current = html.getAttribute('data-theme') === 'light' ? 'light' : 'dark';
    const next = current === 'dark' ? 'light' : 'dark';
    html.setAttribute('data-theme', next);
    try { localStorage.setItem('solan-theme', next); } catch (e) {}
    document.querySelectorAll<HTMLButtonElement>('.theme-toggle').forEach(btn => {
      btn.setAttribute('aria-pressed', next === 'light' ? 'true' : 'false');
      btn.title = next === 'light' ? 'Switch to night mode' : 'Switch to day mode';
    });
  }

  return (
    <button
      type="button"
      className="theme-toggle"
      onClick={toggleTheme}
      aria-label="Toggle day and night mode"
      title="Switch to day mode"
    >
      <svg className="ico theme-icon-sun" viewBox="0 0 24 24"><use href="#i-sun" /></svg>
      <svg className="ico theme-icon-moon" viewBox="0 0 24 24"><use href="#i-moon" /></svg>
    </button>
  );
}
