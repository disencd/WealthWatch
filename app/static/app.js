/* WealthWatch - Alpine.js global app() */
function app() {
  return {
    token: localStorage.getItem('token') || '',
    user: JSON.parse(localStorage.getItem('user') || 'null'),
    sidebarOpen: false,
    toasts: [],
    categories: [],
    subCategories: [],

    get isLoggedIn() { return !!this.token; },
    get authHeader() {
      return { 'Authorization': 'Bearer ' + this.token, 'Content-Type': 'application/json' };
    },

    async api(method, path, body = null) {
      const opts = { method, headers: this.authHeader };
      if (body) opts.body = JSON.stringify(body);
      const res = await fetch('/api/v1' + path, opts);
      if (res.status === 401 || res.status === 403) { this.logout(); throw new Error('Unauthorized'); }
      if (res.status === 204) return null;
      if (!res.ok) { const e = await res.json().catch(() => ({})); throw new Error(e.detail || 'Request failed'); }
      return res.json();
    },

    async apiUpload(path, formData) {
      const res = await fetch('/api/v1' + path, {
        method: 'POST',
        headers: { 'Authorization': 'Bearer ' + this.token },
        body: formData
      });
      if (res.status === 401 || res.status === 403) { this.logout(); throw new Error('Unauthorized'); }
      if (!res.ok) { const e = await res.json().catch(() => ({})); throw new Error(e.detail || 'Upload failed'); }
      return res.json();
    },

    setAuth(token, user) {
      this.token = token;
      this.user = user;
      localStorage.setItem('token', token);
      localStorage.setItem('user', JSON.stringify(user));
    },

    logout() {
      this.token = '';
      this.user = null;
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    },

    async loadCategories() {
      if (!this.token) return;
      try {
        this.categories = await this.api('GET', '/budget/categories');
        this.subCategories = await this.api('GET', '/budget/subcategories');
      } catch (e) { console.error('Failed to load categories', e); }
    },

    toast(message, type = 'info', duration = 4000) {
      const t = { message, type };
      this.toasts.push(t);
      if (duration > 0) setTimeout(() => { const i = this.toasts.indexOf(t); if (i > -1) this.toasts.splice(i, 1); }, duration);
    },

    money(n) { return '$' + (Number(n) || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }); },
    pct(n) { return (Number(n) || 0).toFixed(1) + '%'; },
    fmtDate(d) { if (!d) return ''; return new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }); }
  };
}
