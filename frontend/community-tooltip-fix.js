/* JoyStream AI: avoid duplicate tooltip on Community charts.
 * The custom purple tooltip remains; we remove only the browser-native SVG
 * <title> tooltip on this page, preserving the text in aria-label.
 */
(() => {
  'use strict';
  const isCommunityPage = () => location.hash.replace(/^#/, '') === 'comunidad';
  const clean = () => {
    if (!isCommunityPage()) return;
    const root = document.getElementById('page-root');
    if (!root) return;
    root.querySelectorAll('svg circle').forEach(circle => {
      const title = circle.querySelector(':scope > title');
      const nativeTitle = circle.getAttribute('title');
      const description = title?.textContent?.trim() || nativeTitle?.trim();
      if (!description) return;
      if (!circle.getAttribute('aria-label')) circle.setAttribute('aria-label', description);
      if (title) title.remove();
      if (nativeTitle !== null) circle.removeAttribute('title');
    });
  };
  const start = () => {
    const root = document.getElementById('page-root');
    if (!root) return;
    let pending = false;
    const schedule = () => {
      if (pending) return;
      pending = true;
      requestAnimationFrame(() => { pending = false; clean(); });
    };
    new MutationObserver(schedule).observe(root, {childList: true, subtree: true});
    window.addEventListener('hashchange', schedule);
    schedule();
  };
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', start, {once: true});
  } else {
    start();
  }
})();
