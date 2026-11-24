/* ===========================================================
   SIGNAL — storefront logic (Controller talks to /api/*)
   =========================================================== */
(function () {
  'use strict';

  const $ = (id) => document.getElementById(id);
  const money = (n) => '¥' + Number(n || 0).toFixed(2).replace(/\.00$/, '');
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g,
    (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

  const BRIEF_ARTICLE = {
    lead: '一句话：把噪声折叠起来，只留下能改变判断的那几条。',
    sections: [
      { h: '信息源分享', items: [
        '一手源优先：监管公告、交易所披露、发行人文件。二手解读只作导航。',
        '为每个源标注「更新频率 / 口径 / 滞后」，口径比数字本身更重要。',
        '建一份可回溯的清单：来源、抓取时间、校验人。三条，足矣。',
      ]},
      { h: 'AI 信息分享', items: [
        '用模型做「抽取与对齐」，不让它做「结论」。结论留给人。',
        '每条输出都带原文出处；无出处，即丢弃。',
        '提示词与版本入库，结果才可复现、可审计。',
      ]},
    ],
    foot: '信息差不在更多，而在更快被验证。',
  };

  let ME = { loggedIn: false };
  let CATEGORY = 'all';
  let PRODUCTS = [];
  let DELIVERY_METHODS = [];
  let PICKED_METHOD = 'doc';
  let CART = [];
  try { CART = JSON.parse(localStorage.getItem('signal-cart') || '[]'); } catch (e) { CART = []; }

  // ---------------- HTTP ----------------
  async function api(path, opts) {
    const res = await fetch(path, Object.assign({
      credentials: 'same-origin', headers: { 'Content-Type': 'application/json' },
    }, opts || {}));
    let data = {};
    try { data = await res.json(); } catch (e) { /* ignore */ }
    if (!res.ok) {
      const err = new Error(data.msg || ('HTTP ' + res.status));
      err.status = res.status; err.data = data;
      throw err;
    }
    return data;
  }
  const post = (p, body) => api(p, { method: 'POST', body: JSON.stringify(body || {}) });

  // ---------------- UI helpers ----------------
  let toastTimer = 0;
  function toast(msg) {
    const t = $('toast');
    t.textContent = msg; t.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => t.classList.remove('show'), 2600);
  }
  const LAYERS = [
    { key: 'cart', o: 'cart-overlay', p: 'cart-drawer' },
    { key: 'product', o: 'product-overlay', p: 'product-modal' },
    { key: 'auth', o: 'auth-overlay', p: 'auth-modal' },
    { key: 'orders', o: 'orders-overlay', p: 'orders-modal' },
    { key: 'brief', o: 'brief-overlay', p: 'brief-modal' },
  ];
  function closeAll() {
    LAYERS.forEach((l) => { $(l.o).hidden = true; $(l.p).hidden = true; });
    document.body.style.overflow = '';
    $('user-dropdown').hidden = true;
    $('user-trigger').setAttribute('aria-expanded', 'false');
  }
  function openLayer(key) {
    closeAll();
    const l = LAYERS.find((x) => x.key === key);
    if (!l) return;
    $(l.o).hidden = false; $(l.p).hidden = false;
    document.body.style.overflow = 'hidden';
  }

  // ---------------- product artwork (line-only, single accent) ----------------
  function art(p) {
    const blue = '#0071e3', grey = '#c7c7cc';
    const line = `fill="none" stroke="${grey}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"`;
    const ink = `fill="none" stroke="${blue}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"`;
    const cat = (p.category || '');
    if (cat.indexOf('数据') >= 0) {
      return `<svg viewBox="0 0 96 96" aria-hidden="true"><rect x="16" y="18" width="64" height="60" rx="8" ${line}/><path d="M28 64V50M42 64V42M56 64V54M70 64V36" ${ink}/><path d="M24 70h48" ${line}/></svg>`;
    }
    if (cat.indexOf('AI') >= 0) {
      return `<svg viewBox="0 0 96 96" aria-hidden="true"><circle cx="48" cy="48" r="9" ${ink}/><path d="M48 20v14M48 62v14M20 48h14M62 48h14M28 28l10 10M58 58l10 10M68 28L58 38M38 58L28 68" ${line}/></svg>`;
    }
    if (cat.indexOf('模板') >= 0) {
      return `<svg viewBox="0 0 96 96" aria-hidden="true"><rect x="20" y="16" width="56" height="64" rx="8" ${line}/><rect x="30" y="28" width="36" height="8" rx="4" fill="${blue}" opacity=".18"/><path d="M30 46h36M30 56h28M30 66h20" ${line}/></svg>`;
    }
    if (cat.indexOf('订阅') >= 0) {
      return `<svg viewBox="0 0 96 96" aria-hidden="true"><rect x="16" y="30" width="64" height="42" rx="10" ${line}/><path d="M16 44h64" ${line}/><path d="M32 58h20" ${ink}/><circle cx="68" cy="58" r="4" fill="${blue}"/></svg>`;
    }
    if (cat.indexOf('信息源') >= 0) {
      return `<svg viewBox="0 0 96 96" aria-hidden="true"><path d="M24 20h40l10 10v46H24z" ${line}/><path d="M64 20v10h10" ${line}/><path d="M34 42h28M34 52h28M34 62h18" ${ink}/></svg>`;
    }
    // brief / default
    return `<svg viewBox="0 0 96 96" aria-hidden="true"><rect x="22" y="14" width="52" height="68" rx="8" ${line}/><path d="M34 34h28M34 44h28M34 54h18" ${ink}/><path d="M34 66h28" ${line}/><circle cx="70" cy="70" r="9" fill="${blue}"/><path d="M66 70l3 3 5-6" stroke="#fff" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
  }

  const methodName = (k) => {
    const m = DELIVERY_METHODS.find((x) => x.key === k);
    return m ? m.name : k;
  };
  function methodTags(list) {
    return (list || []).map((k) => `<span class="method-tag">${esc(methodName(k))}</span>`).join('');
  }

  // ---------------- brief stage ----------------
  async function loadBrief() {
    try {
      const d = await api('/api/brief');
      const b = d.brief || {};
      $('brief-sources').innerHTML = (b.sources || []).map((s) => `<li>${esc(s)}</li>`).join('');
      $('brief-ai').innerHTML = (b.ai || []).map((s) => `<li>${esc(s)}</li>`).join('');
      $('brief-foot').textContent = b.foot || '';
    } catch (e) { /* leave empty */ }
  }

  // ---------------- delivery cards ----------------
  async function loadDelivery() {
    try {
      const d = await api('/api/delivery-methods');
      DELIVERY_METHODS = d.items || [];
      $('delivery-grid').innerHTML = DELIVERY_METHODS.map((m, i) => `
        <article class="delivery-card">
          <span class="delivery-num">0${i + 1}</span>
          <h3>${esc(m.name)}</h3>
          <p>${esc(m.desc)}</p>
          <span class="delivery-en">${esc(m.en)}</span>
        </article>`).join('');
      $('delivery-pick').innerHTML = DELIVERY_METHODS.map((m) =>
        `<button class="pick${m.key === 'doc' ? ' active' : ''}" data-method="${esc(m.key)}">${esc(m.name)}</button>`).join('');
    } catch (e) { /* leave empty */ }
  }

  // ---------------- products ----------------
  function cardTpl(p) {
    const fmt = esc(p.format || '数字文件');
    return `<article class="card">
      <div class="product-media"><span class="media-badge">${fmt}</span>${art(p)}</div>
      <span class="card-cat">${esc(p.category || '数字文件')}</span>
      <h3>${esc(p.name)}</h3>
      <p class="card-sub">${esc(p.subtitle || '')}</p>
      <div class="card-methods">${methodTags(p.delivery)}</div>
      <div class="card-foot">
        <span class="price"><small>¥</small>${Number(p.price || 0).toFixed(0)}</span>
        <button class="pill small" data-detail="${esc(p.id)}">查看详情</button>
      </div>
    </article>`;
  }

  async function loadProducts() {
    const grid = $('product-grid');
    $('products-error').hidden = true;
    $('products-empty').hidden = true;
    $('products-loading').hidden = false;
    grid.innerHTML = '';
    try {
      const q = $('search-input').value.trim();
      const qs = new URLSearchParams();
      if (CATEGORY && CATEGORY !== 'all') qs.set('category', CATEGORY);
      if (q) qs.set('q', q);
      const data = await api('/api/products' + (qs.toString() ? '?' + qs : ''));
      PRODUCTS = data.items || [];
      $('products-loading').hidden = true;
      if (!PRODUCTS.length) { $('products-empty').hidden = false; return; }
      grid.innerHTML = PRODUCTS.map(cardTpl).join('');
    } catch (e) {
      $('products-loading').hidden = true;
      $('products-error').hidden = false;
    }
  }

  function openProduct(id) {
    const p = PRODUCTS.find((x) => x.id === id);
    if (!p) return;
    const meta = [p.format, p.size, p.author].filter(Boolean);
    $('product-detail').innerHTML = `
      <div class="pd-media">${art(p)}</div>
      <span class="pd-cat">${esc(p.category || '数字文件')}</span>
      <h3 class="pd-title">${esc(p.name)}</h3>
      <p class="pd-sub">${esc(p.subtitle || '')}</p>
      <p class="pd-desc">${esc(p.description || '')}</p>
      <div class="pd-meta">${meta.map((m) => `<span>${esc(m)}</span>`).join('')}</div>
      ${p.sample ? `<div class="pd-sample"><b>试读 · </b>${esc(p.sample)}</div>` : ''}
      <div class="pd-methods">支持发货：${methodTags(p.delivery)}</div>
      <div class="pd-foot">
        <span class="price"><small>¥</small>${Number(p.price || 0).toFixed(0)}</span>
        <button class="pill" data-add="${esc(p.id)}">加入购物袋</button>
      </div>`;
    openLayer('product');
  }

  // ---------------- cart ----------------
  function saveCart() {
    localStorage.setItem('signal-cart', JSON.stringify(CART));
    renderCart();
  }
  function addToCart(id) {
    const p = PRODUCTS.find((x) => x.id === id);
    if (!p) return;
    const line = CART.find((x) => x.id === id);
    if (line) line.qty += 1;
    else CART.push({ id, name: p.name, price: Number(p.price), category: p.category, qty: 1 });
    saveCart();
    toast('已加入购物袋 · ' + p.name);
  }
  const cartCount = () => CART.reduce((n, x) => n + x.qty, 0);
  const cartTotal = () => CART.reduce((n, x) => n + x.price * x.qty, 0);
  function renderCartBadge() {
    const n = cartCount();
    $('cart-count').textContent = n;
    $('cart-count').hidden = n === 0;
  }
  function renderCart() {
    renderCartBadge();
    const box = $('cart-items');
    if (!CART.length) {
      box.innerHTML = '<div class="empty-note">购物袋是空的，去挑一份信息吧。</div>';
    } else {
      box.innerHTML = CART.map((x) => `<div class="cart-line">
        <div class="cart-thumb">${art({ category: x.category })}</div>
        <div class="cart-info"><b>${esc(x.name)}</b><span>${money(x.price)}</span>
          <div class="qty">
            <button data-q="-1" data-id="${esc(x.id)}" aria-label="减少">−</button>
            <span>${x.qty}</span>
            <button data-q="1" data-id="${esc(x.id)}" aria-label="增加">+</button>
          </div>
        </div>
        <button class="cart-del" data-remove="${esc(x.id)}" aria-label="移除">×</button>
      </div>`).join('');
    }
    $('cart-total').textContent = money(cartTotal());
    $('btn-checkout').disabled = CART.length === 0;
    $('cart-hint').textContent = ME.loggedIn
      ? '付款后自动发货，凭证保存在「我的订单」'
      : '登录后可结算下单';
  }

  // ---------------- auth ----------------
  function authStep(n) {
    $('auth-step1').hidden = n !== 1;
    $('auth-step2').hidden = n !== 2;
    $('auth-step3').hidden = n !== 3;
    $('auth-msg').textContent = '';
  }
  function openAuth() {
    authStep(1);
    $('auth-email').value = ''; $('auth-code').value = '';
    $('demo-code').hidden = true;
    $('auth-title').textContent = '登录 SIGNAL';
    openLayer('auth');
    setTimeout(() => $('auth-email').focus(), 120);
  }
  function applyNav() {
    const on = !!ME.loggedIn;
    $('btn-login-open').hidden = on;
    $('nav-user').hidden = !on;
    if (on) {
      $('user-email').textContent = ME.email;
      $('user-avatar').textContent = (ME.email || 'S')[0].toUpperCase();
    }
    renderCart();
  }
  async function refreshMe() {
    try { ME = await api('/api/me'); }
    catch (e) { ME = { loggedIn: false }; }
    applyNav();
  }

  // ---------------- orders + delivery payload ----------------
  function deliveryItem(d) {
    let body = '';
    if (d.kind === 'doc') {
      body = `<div class="di-note">${esc(d.note || '')}</div>
        <a class="di-btn" href="${esc(d.url)}" target="_blank" rel="noopener">下载文件 ↗</a>`;
    } else if (d.kind === 'code') {
      body = `<div class="di-note">${esc(d.note || '')}</div>
        <div class="di-value">${esc(d.code)}<button class="di-copy" data-copy="${esc(d.code)}">复制</button></div>`;
    } else if (d.kind === 'link') {
      body = `<div class="di-note">${esc(d.note || '')}</div>
        <div class="di-value">${esc(d.url)}</div>
        ${d.code ? `<div class="di-value">提取码 ${esc(d.code)}<button class="di-copy" data-copy="${esc(d.code)}">复制</button></div>` : ''}
        <a class="di-btn" href="${esc(d.url)}" target="_blank" rel="noopener">打开链接 ↗</a>`;
    } else if (d.kind === 'email') {
      body = `<div class="di-note">收件：${esc(d.to || '')} · 状态：${esc(d.status === 'queued' ? '已排入队列' : d.status || '已发送')}</div>
        <div class="di-note">${esc(d.note || '')}</div>
        ${d.preview ? `<div class="di-content">${esc(d.preview)}</div>` : ''}`;
    } else if (d.kind === 'online') {
      body = `<div class="di-note">${esc(d.note || '')}</div>
        <div class="di-content">${esc(d.content || '')}</div>`;
    } else {
      body = `<div class="di-note">${esc(d.text || d.note || '')}</div>`;
    }
    return `<div class="delivery-item">
      <div class="di-top"><b>${esc(d.name || '')}</b>
        <span class="di-kind">${esc(d.methodName || methodName(d.method))}${d.fallback ? ' · 已自动适配' : ''}</span></div>
      ${body}
    </div>`;
  }
  function orderCard(o) {
    const names = (o.items || []).map((i) => esc(i.name) + ' ×' + i.qty).join('、');
    return `<div class="order-card">
      <div class="order-head"><b>${esc(o.id)}</b><span>${money(o.total)}</span></div>
      <div class="order-meta">${esc(o.createdAt || '')} · ${esc(names)}
        <span class="status-tag">${o.status === 'delivered' ? '已交付' : esc(o.status || '')}</span></div>
      ${(o.deliveries || []).map(deliveryItem).join('') || '<div class="di-note">暂无交付凭证</div>'}
    </div>`;
  }
  async function openOrders() {
    openLayer('orders');
    $('orders-list').innerHTML = '<div class="state-box"><span class="spinner"></span> 加载中…</div>';
    if (!ME.loggedIn) {
      $('orders-list').innerHTML = '<div class="empty-note">登录后查看你的订单与交付凭证。</div>';
      return;
    }
    try {
      const d = await api('/api/orders');
      $('orders-list').innerHTML = (d.items || []).length
        ? d.items.map(orderCard).join('')
        : '<div class="empty-note">还没有订单，去挑一份信息吧。</div>';
    } catch (e) {
      $('orders-list').innerHTML = '<div class="empty-note">加载失败，请稍后再试。</div>';
    }
  }

  // ---------------- brief modal ----------------
  function openBrief() {
    $('brief-article').innerHTML = `
      <p class="lead">${esc(BRIEF_ARTICLE.lead)}</p>
      ${BRIEF_ARTICLE.sections.map((s) => `
        <h2>${esc(s.h)}</h2><ul>${s.items.map((i) => `<li>${esc(i)}</li>`).join('')}</ul>`).join('')}
      <h2>一句话</h2><p>${esc(BRIEF_ARTICLE.foot)}</p>
      <p style="margin-top:24px;font-size:12px;color:#86868b">信息仅供参考，不构成投资建议。</p>`;
    openLayer('brief');
  }

  // ---------------- events ----------------
  document.addEventListener('DOMContentLoaded', () => {
    refreshMe();
    loadBrief();
    loadDelivery();
    loadProducts();
    renderCart();

    LAYERS.forEach((l) => $(l.o).addEventListener('click', closeAll));
    document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeAll(); });

    // nav
    $('nav-cart').addEventListener('click', () => { renderCart(); openLayer('cart'); });
    $('cart-close').addEventListener('click', closeAll);
    $('btn-login-open').addEventListener('click', openAuth);
    $('btn-join').addEventListener('click', openAuth);
    $('btn-foot-login').addEventListener('click', openAuth);
    $('btn-foot-orders').addEventListener('click', () => ME.loggedIn ? openOrders() : openAuth());
    $('user-trigger').addEventListener('click', (e) => {
      e.stopPropagation();
      const d = $('user-dropdown'); d.hidden = !d.hidden;
      $('user-trigger').setAttribute('aria-expanded', String(!d.hidden));
    });
    document.addEventListener('click', (e) => {
      if (!$('nav-user').contains(e.target)) $('user-dropdown').hidden = true;
    });
    $('btn-my-orders').addEventListener('click', openOrders);
    $('btn-logout').addEventListener('click', async () => {
      await post('/api/logout', {});
      ME = { loggedIn: false }; applyNav(); closeAll(); toast('已退出登录');
    });

    // brief
    $('btn-brief-read').addEventListener('click', openBrief);
    $('brief-close').addEventListener('click', closeAll);

    // filters
    let searchTimer = 0;
    $('category-bar').addEventListener('click', (e) => {
      const b = e.target.closest('.chip'); if (!b) return;
      document.querySelectorAll('.chip').forEach((c) => c.classList.toggle('active', c === b));
      CATEGORY = b.dataset.cat; loadProducts();
    });
    $('search-input').addEventListener('input', () => {
      clearTimeout(searchTimer); searchTimer = setTimeout(loadProducts, 280);
    });
    $('btn-retry').addEventListener('click', loadProducts);

    // product grid / detail
    $('product-grid').addEventListener('click', (e) => {
      const d = e.target.closest('[data-detail]'); if (d) openProduct(d.dataset.detail);
      const a = e.target.closest('[data-add]'); if (a) addToCart(a.dataset.add);
    });
    $('product-detail').addEventListener('click', (e) => {
      const a = e.target.closest('[data-add]');
      if (a) { addToCart(a.dataset.add); closeAll(); renderCart(); openLayer('cart'); }
    });
    $('product-close').addEventListener('click', closeAll);

    // delivery pick
    $('delivery-pick').addEventListener('click', (e) => {
      const b = e.target.closest('[data-method]'); if (!b) return;
      PICKED_METHOD = b.dataset.method;
      document.querySelectorAll('.pick').forEach((x) => x.classList.toggle('active', x === b));
    });

    // cart quantity / remove
    $('cart-items').addEventListener('click', (e) => {
      const q = e.target.closest('[data-q]');
      if (q) {
        const line = CART.find((x) => x.id === q.dataset.id);
        if (line) { line.qty += Number(q.dataset.q); if (line.qty <= 0) CART = CART.filter((x) => x !== line); }
        saveCart(); return;
      }
      const r = e.target.closest('[data-remove]');
      if (r) { CART = CART.filter((x) => x.id !== r.dataset.remove); saveCart(); }
    });
    $('btn-checkout').addEventListener('click', async () => {
      if (!ME.loggedIn) { openAuth(); toast('先登录，再结算'); return; }
      const btn = $('btn-checkout'); btn.disabled = true; btn.textContent = '提交中…';
      try {
        const d = await post('/api/orders', {
          items: CART.map((x) => ({ id: x.id, qty: x.qty })),
          deliveryMethod: PICKED_METHOD,
          deliveryTarget: $('delivery-target').value.trim(),
        });
        CART = []; saveCart(); closeAll();
        toast('下单成功 · 已自动发货');
        setTimeout(openOrders, 400);
      } catch (err) { toast(err.message || '下单失败'); }
      finally { btn.disabled = false; btn.textContent = '去结算'; }
    });

    // copy buttons (delegate, also inside orders)
    document.addEventListener('click', (e) => {
      const c = e.target.closest('[data-copy]'); if (!c) return;
      const text = c.dataset.copy;
      (navigator.clipboard ? navigator.clipboard.writeText(text) : Promise.reject())
        .then(() => toast('已复制')).catch(() => toast('请手动复制：' + text));
    });

    // auth flow
    $('btn-auth-close').addEventListener('click', closeAll);
    $('btn-send-code').addEventListener('click', async () => {
      const email = $('auth-email').value.trim();
      if (!email) { $('auth-msg').textContent = '请先填写邮箱'; return; }
      const btn = $('btn-send-code'); btn.disabled = true; btn.textContent = '发送中…';
      try {
        const d = await post('/api/send-code', { email });
        authStep(2);
        if (d.demoCode) {
          $('demo-code').hidden = false;
          $('demo-code').innerHTML = '演示模式验证码：<b>' + esc(d.demoCode) + '</b>（接入邮件后自动隐藏）';
        }
        setTimeout(() => $('auth-code').focus(), 120);
      } catch (err) { $('auth-msg').textContent = err.message || '发送失败'; }
      finally { btn.disabled = false; btn.textContent = '获取验证码'; }
    });
    $('auth-code').addEventListener('keydown', (e) => { if (e.key === 'Enter') $('btn-verify').click(); });
    $('btn-verify').addEventListener('click', async () => {
      const email = $('auth-email').value.trim();
      const code = $('auth-code').value.trim();
      if (!code) { $('auth-msg').textContent = '请填写验证码'; return; }
      const btn = $('btn-verify'); btn.disabled = true; btn.textContent = '验证中…';
      try {
        await post('/api/verify', { email, code });
        await refreshMe();
        $('auth-title').textContent = '欢迎回来';
        $('auth-success-text').textContent = ME.email + '，你已成功登录。';
        authStep(3);
      } catch (err) { $('auth-msg').textContent = err.message || '验证失败'; authStep(2); }
      finally { btn.disabled = false; btn.textContent = '验证并继续'; }
    });
    $('btn-back').addEventListener('click', () => authStep(1));
    $('btn-auth-done').addEventListener('click', closeAll);
    $('orders-close').addEventListener('click', closeAll);
  });
})();
