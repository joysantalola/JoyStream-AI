/* JoyStream AI 26C: password entered only on demand, never stored in JS/storage. */
(() => {
  'use strict';
  const nativeFetch = window.fetch.bind(window);
  let loginInProgress = null;
  const sensitive = new Set(['/api/sync', '/api/channel/sync', '/api/ai/analyze']);

  async function login() {
    const password = window.prompt('JoyStream AI · Acceso de administrador\nIntroduce la contraseña local para sincronizar o utilizar la IA:');
    if (password === null || !password) return false;
    try {
      const result = await nativeFetch('/api/auth/login', {
        method: 'POST', credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password })
      });
      if (!result.ok) {
        const info = await result.json().catch(() => ({}));
        window.alert(info.detail || 'No se ha podido iniciar sesión.');
        return false;
      }
      return true;
    } catch (_) {
      window.alert('No se puede conectar con el backend para iniciar sesión.');
      return false;
    }
  }

  window.fetch = async (input, init) => {
    const req = new Request(input, init);
    const url = new URL(req.url, window.location.href);
    if (url.origin !== window.location.origin || req.method.toUpperCase() !== 'POST' || !sensitive.has(url.pathname)) {
      return nativeFetch(input, init);
    }
    const copy = req.clone();
    const result = await nativeFetch(req);
    if (result.status !== 401) return result;
    if (!loginInProgress) {
      loginInProgress = login().finally(() => { loginInProgress = null; });
    }
    if (!(await loginInProgress)) return result;
    return nativeFetch(copy);
  };
})();
