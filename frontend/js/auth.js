// Login Supabase — só necessário pra CALCULAR (o app local sempre abre e mostra os projetos já
// salvos, sem exigir login; login só é pedido na hora de calcular/recalcular, que precisa da API
// remota — soft-lock estrutural, decisão já travada no ADR). Chama a API REST de Auth do Supabase
// direto via fetch, sem precisar da lib supabase-js (o app não tem empacotador/bundler).
const SUPABASE_URL = 'https://luzvgsgxutggnbyrhswg.supabase.co';
const SUPABASE_ANON_KEY = 'sb_publishable_BreZGIXnU6_rdBi8n3bF5w_N3HZ56-S';
const AUTH_STORAGE_KEY = 'vektorium_auth_session';
const AUTH = {
  _sessao: null,

  carregar() {
    try {
      const raw = localStorage.getItem(AUTH_STORAGE_KEY);
      this._sessao = raw ? JSON.parse(raw) : null;
    } catch (e) { this._sessao = null; }
    return this._sessao;
  },

  salvar(sessao) {
    this._sessao = sessao;
    localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(sessao));
  },

  limpar() {
    this._sessao = null;
    localStorage.removeItem(AUTH_STORAGE_KEY);
  },

  _tokenExpirado() {
    if (!this._sessao || !this._sessao.access_token) return true;
    try {
      const payload = JSON.parse(atob(this._sessao.access_token.split('.')[1]));
      return payload.exp * 1000 < Date.now() - 30000;
    } catch (e) { return true; }
  },

  logado() {
    if (!this._sessao) this.carregar();
    return !!(this._sessao && this._sessao.access_token && !this._tokenExpirado());
  },

  token() {
    if (!this._sessao) this.carregar();
    return this._sessao ? this._sessao.access_token : null;
  },

  async renovar() {
    if (!this._sessao || !this._sessao.refresh_token) { this.limpar(); return false; }
    try {
      const ctrl = new AbortController();
      const timer = setTimeout(() => ctrl.abort(), 5000);
      const r = await fetch(`${SUPABASE_URL}/auth/v1/token?grant_type=refresh_token`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'apikey': SUPABASE_ANON_KEY },
        body: JSON.stringify({ refresh_token: this._sessao.refresh_token }),
        signal: ctrl.signal,
      });
      clearTimeout(timer);
      if (!r.ok) { this.limpar(); return false; }
      const dados = await r.json();
      this.salvar(dados);
      return true;
    } catch (e) { this.limpar(); return false; }
  },

  async garantirToken() {
    if (!this._sessao) this.carregar();
    if (!this._sessao || !this._sessao.access_token) return;
    if (this._tokenExpirado()) {
      if (!this._renovando) {
        this._renovando = this.renovar().finally(() => { this._renovando = null; });
      }
      await this._renovando;
    }
  },

  email() {
    if (!this._sessao) this.carregar();
    return this._sessao && this._sessao.user ? this._sessao.user.email : null;
  },

  async login(email, senha) {
    const r = await fetch(`${SUPABASE_URL}/auth/v1/token?grant_type=password`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'apikey': SUPABASE_ANON_KEY },
      body: JSON.stringify({ email, password: senha }),
    });
    const dados = await r.json();
    if (!r.ok) throw new Error(dados.error_description || dados.msg || 'Falha no login');
    this.salvar(dados);
    this._syncFotosSeNecessario(dados.access_token);
    return dados;
  },

  async _syncFotosSeNecessario(token) {
    try {
      await fetch('/api/catalogo-sync/converter-fotos', { method: 'POST' });
    } catch (e) {
      console.warn('[auth] Conversão de fotos falhou (não-bloqueante):', e);
    }
  },

  // Recuperação de senha: o Supabase redireciona pro app com o token na URL (#access_token=...
  // &type=recovery). Lê isso, sem precisar do formulário de login — é uma sessão temporária só
  // pra permitir definir a senha nova.
  lerTokenRecuperacao() {
    const hash = window.location.hash;
    if (!hash || hash.indexOf('access_token') === -1) return null;
    const params = new URLSearchParams(hash.slice(1));
    if (params.get('type') !== 'recovery') return null;
    const access_token = params.get('access_token');
    if (!access_token) return null;
    let email = null;
    try { email = JSON.parse(atob(access_token.split('.')[1])).email; } catch (e) {}
    history.replaceState(null, '', window.location.pathname);   // tira o token da URL/histórico
    return { access_token, refresh_token: params.get('refresh_token'), email };
  },

  async definirNovaSenha(access_token, novaSenha) {
    const r = await fetch(`${SUPABASE_URL}/auth/v1/user`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', 'apikey': SUPABASE_ANON_KEY, 'Authorization': `Bearer ${access_token}` },
      body: JSON.stringify({ password: novaSenha }),
    });
    const dados = await r.json();
    if (!r.ok) throw new Error(dados.error_description || dados.msg || 'Falha ao definir a nova senha.');
    return dados;
  },

  async logout() {
    const token = this.token();
    this.limpar();
    if (token) {
      const ctrl = new AbortController();
      const t = setTimeout(() => ctrl.abort(), 3000);
      try {
        await fetch(`${SUPABASE_URL}/auth/v1/logout`, {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${token}`, 'apikey': SUPABASE_ANON_KEY },
          signal: ctrl.signal,
        });
      } catch (e) { /* silencioso — a sessão local já foi limpa de qualquer forma */ }
      finally { clearTimeout(t); }
    }
  },
};

AUTH.carregar();
