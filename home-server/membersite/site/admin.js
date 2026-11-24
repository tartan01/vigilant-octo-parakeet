/* ===========================================================
   SIGNAL Admin Console — logic
   Independent username/password session (cookie `csid`).
   =========================================================== */
(function () {
  'use strict';

  const $ = (id) => document.getElementById(id);
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g,
    (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const money = (n) => '¥' + Number(n || 0).toFixed(2);

  const METHOD_NAMES = {
    doc: '文档', email: '邮件', link: '外链', code: '授权码', online: '在线',
  };
  const VIEW_META = {
    overview: ['概览', '经营数据与最近动态'],
    products: ['商品管理', '上架、编辑与发货方式配置'],
    orders: ['订单与发货', '查看交付凭证并标记状态'],
    media: ['图片 / 文件', '上传素材，用于封面与交付物'],
    settings: ['设置', '管理员账号安全'],
  };

  let PRODUCTS = [];
  let CURRENT_USER = '';

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
  const post = (p, b) => api(p, { method: 'POST', body: JSON.stringify(b || {}) });
  const put = (p, b) => api(p, { method: 'PUT', body: JSON.stringify(b || {}) });
  const del = (p) => api(p, { method: 'DELETE' });

  let toastTimer = 0;
  function toast(msg) {
    const t = $('toast');
    t.textContent = msg; t.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => t.classList.remove('show'), 2600);
  }

  // ---------------- boot / session ----------------
  async function boot() {
    try {
      const d = await api('/api/admin/session');
      if (d.loggedIn) { enterApp(d.user); return; }
    } catch (e) { /* fall through */ }
    $('login-view').hidden = false;
    $('app-view').hidden = true;
  }
  function enterApp(user) {
    CURRENT_USER = user || 'admin';
    $('top-user').textContent = CURRENT_USER;
    $('login-view').hidden = true;
    $('app-view').hidden = false;
    switchView('overview');
  }

  // ---------------- view switching ----------------
  function switchView(name) {
    document.querySelectorAll('.side-item').forEach((b) =>
      b.classList.toggle('active', b.dataset.view === name));
    Object.keys(VIEW_META).forEach((k) => { $('view-' + k).hidden = k !== name; });
    $('view-title').textContent = VIEW_META[name][0];
    $('view-sub').textContent = VIEW_META[name][1];
    if (name === 'overview') loadOverview();
    if (name === 'products') loadProducts();
    if (name === 'orders') loadOrders();
    if (name === 'media') loadMedia();
    window.scrollTo(0, 0);
  }

  // ---------------- overview ----------------
  async function loadOverview() {
    try {
      const d = await api('/api/admin/overview');
      $('stat-grid').innerHTML = [
        ['注册用户', d.users], ['商品总数', d.products], ['累计订单', d.orders],
        ['成交金额', money(d.revenue)], ['待处理', d.pending != null ? d.pending : 0],
      ].map(([k, v]) => `<div class="stat"><b>${esc(v)}</b><span>${esc(k)}</span></div>`).join('');
      const rows = d.recentOrders || [];
      $('overview-orders').innerHTML = rows.length ? `
        <table><thead><tr><th>订单号</th><th>用户</th><th>发货方式</th><th>金额</th><th>状态</th><th>时间</th></tr></thead>
        <tbody>${rows.map((o) => `<tr>
          <td>${esc(o.id)}</td><td>${esc(o.email)}</td>
          <td>${esc(METHOD_NAMES[o.deliveryMethod] || o.deliveryMethod || '—')}</td>
          <td>${money(o.total)}</td>
          <td><span class="tag ${o.status === 'delivered' ? 'ok' : 'warn'}">${esc(o.status === 'delivered' ? '已交付' : o.status || '')}</span></td>
          <td>${esc(o.createdAt || '')}</td></tr>`).join('')}</tbody></table>`
        : '<div class="empty">还没有订单。</div>';
    } catch (e) { toast('概览加载失败：' + e.message); }
  }

  // ---------------- products ----------------
  async function loadProducts() {
    const box = $('product-table');
    box.innerHTML = '<div class="empty">加载中…</div>';
    try {
      const d = await api('/api/admin/products');
      PRODUCTS = d.items || [];
      box.innerHTML = PRODUCTS.length ? `
        <table><thead><tr><th>商品</th><th>分类</th><th>价格</th><th>发货方式</th><th>库存</th><th>状态</th><th>操作</th></tr></thead>
        <tbody>${PRODUCTS.map((p) => `<tr>
          <td><div class="td-name">${esc(p.name)}</div><div class="td-sub">${esc(p.id)} · ${esc(p.format || '')}</div></td>
          <td>${esc(p.category || '—')}</td><td>${money(p.price)}</td>
          <td>${(p.delivery || []).map((m) => `<span class="tag">${esc(METHOD_NAMES[m] || m)}</span>`).join('') || '—'}</td>
          <td>${Number(p.stock) === -1 ? '∞' : esc(p.stock)}</td>
          <td><span class="tag ${p.hidden ? 'off' : 'ok'}">${p.hidden ? '下架' : '上架'}</span></td>
          <td><div class="row-btns">
            <button data-edit="${esc(p.id)}">编辑</button>
            <button class="del" data-delete="${esc(p.id)}">删除</button></div></td></tr>`).join('')}</tbody></table>`
        : '<div class="empty">还没有商品，点「新增商品」开始。</div>';
    } catch (e) { box.innerHTML = '<div class="empty">加载失败：' + esc(e.message) + '</div>'; }
  }

  function clearForm() {
    ['f-id', 'f-name', 'f-subtitle', 'f-description', 'f-category', 'f-format',
     'f-size', 'f-author', 'f-badge', 'f-cover', 'f-fileUrl', 'f-linkUrl',
     'f-linkCode', 'f-codePool', 'f-content', 'f-sample'].forEach((k) => { $(k).value = ''; });
    $('f-price').value = '0'; $('f-stock').value = '-1'; $('f-hidden').value = '0';
    document.querySelectorAll('#f-delivery input').forEach((c) => {
      c.checked = c.value === 'doc';
    });
    $('form-msg').textContent = '';
    $('form-title').textContent = '新增商品';
  }
  function openForm(p) {
    $('product-form-panel').hidden = false;
    clearForm();
    if (p) {
      $('form-title').textContent = '编辑商品 · ' + p.name;
      const map = {
        'f-id': p.id, 'f-name': p.name, 'f-subtitle': p.subtitle,
        'f-description': p.description, 'f-price': p.price, 'f-category': p.category,
        'f-format': p.format, 'f-size': p.size, 'f-author': p.author,
        'f-badge': p.badge, 'f-stock': p.stock, 'f-hidden': p.hidden,
        'f-cover': p.cover, 'f-fileUrl': p.fileUrl, 'f-linkUrl': p.linkUrl,
        'f-linkCode': p.linkCode, 'f-content': p.content, 'f-sample': p.sample,
      };
      Object.keys(map).forEach((k) => { if (map[k] != null) $(k).value = map[k]; });
      $('f-codePool').value = (p.codePool || []).join(', ');
      const enabled = p.delivery || [];
      document.querySelectorAll('#f-delivery input').forEach((c) => { c.checked = enabled.indexOf(c.value) >= 0; });
    }
    $('product-form-panel').scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
  function formPayload() {
    return {
      name: $('f-name').value.trim(), subtitle: $('f-subtitle').value.trim(),
      description: $('f-description').value.trim(), price: Number($('f-price').value || 0),
      category: $('f-category').value.trim() || '数字文件',
      format: $('f-format').value.trim(), size: $('f-size').value.trim(),
      author: $('f-author').value.trim(), badge: $('f-badge').value.trim(),
      stock: Number($('f-stock').value || -1), hidden: Number($('f-hidden').value),
      delivery: Array.from(document.querySelectorAll('#f-delivery input:checked')).map((c) => c.value),
      cover: $('f-cover').value.trim(), fileUrl: $('f-fileUrl').value.trim(),
      linkUrl: $('f-linkUrl').value.trim(), linkCode: $('f-linkCode').value.trim(),
      codePool: $('f-codePool').value.split(/[,\n]/).map((s) => s.trim()).filter(Boolean),
      content: $('f-content').value, sample: $('f-sample').value.trim(),
    };
  }

  // ---------------- orders ----------------
  async function loadOrders() {
    const box = $('order-table');
    box.innerHTML = '<div class="empty">加载中…</div>';
    try {
      const d = await api('/api/admin/orders');
      const rows = d.items || [];
      box.innerHTML = rows.length ? `
        <table><thead><tr><th>订单号</th><th>用户 / 目标</th><th>商品</th><th>发货</th><th>交付凭证</th><th>金额</th><th>状态</th><th>操作</th></tr></thead>
        <tbody>${rows.map((o) => `<tr>
          <td><div class="td-name">${esc(o.id)}</div><div class="td-sub">${esc(o.createdAt || '')}</div></td>
          <td>${esc(o.email)}<div class="td-sub">${esc(o.deliveryTarget || '')}</div></td>
          <td>${(o.items || []).map((i) => esc(i.name) + ' ×' + i.qty).join('<br>')}</td>
          <td>${esc(METHOD_NAMES[o.deliveryMethod] || o.deliveryMethod || '—')}</td>
          <td>${(o.deliveries || []).map((x) => `<span class="tag">${esc(METHOD_NAMES[x.method] || x.kind || '')}</span>`).join('') || '—'}</td>
          <td>${money(o.total)}</td>
          <td><span class="tag ${o.status === 'delivered' ? 'ok' : 'warn'}">${esc(o.status === 'delivered' ? '已交付' : o.status || '')}</span></td>
          <td><div class="row-btns">
            <button data-order="${esc(o.id)}" data-status="${o.status === 'delivered' ? 'pending' : 'delivered'}">${o.status === 'delivered' ? '标记待处理' : '标记已交付'}</button>
          </div></td></tr>`).join('')}</tbody></table>`
        : '<div class="empty">还没有订单。</div>';
    } catch (e) { box.innerHTML = '<div class="empty">加载失败：' + esc(e.message) + '</div>'; }
  }

  // ---------------- media ----------------
  async function loadMedia() {
    const box = $('media-grid');
    box.innerHTML = '<div class="empty">加载中…</div>';
    try {
      const d = await api('/api/admin/uploads');
      const items = d.items || [];
      box.innerHTML = items.length ? items.map((f) => {
        const isImg = /\.(png|jpe?g|webp|gif|svg|ico)$/i.test(f.name);
        return `<div class="media-item">
          <div class="media-thumb">${isImg ? `<img src="${esc(f.url)}" alt="${esc(f.name)}" />` : '<span>📄</span>'}</div>
          <div class="media-info"><b title="${esc(f.name)}">${esc(f.name)}</b>${(f.size / 1024).toFixed(1)} KB<br>
            <button class="link-btn" data-copy="${esc(f.url)}">复制 URL</button></div></div>`;
      }).join('') : '<div class="empty">还没有上传素材。</div>';
    } catch (e) { box.innerHTML = '<div class="empty">加载失败：' + esc(e.message) + '</div>'; }
  }

  async function uploadFile(file, targetInput) {
    const msg = $('upload-msg');
    msg.textContent = '正在上传 ' + file.name + ' …';
    try {
      const b64 = await new Promise((resolve, reject) => {
        const r = new FileReader();
        r.onload = () => resolve(String(r.result).split(',')[1]);
        r.onerror = reject;
        r.readAsDataURL(file);
      });
      const d = await post('/api/admin/upload', { filename: file.name, data: b64 });
      msg.textContent = '已上传：' + d.url;
      if (targetInput) $(targetInput).value = d.url;
      toast('上传成功');
      loadMedia();
    } catch (e) {
      msg.textContent = '上传失败：' + e.message;
      toast('上传失败：' + e.message);
    }
  }

  // ---------------- events ----------------
  document.addEventListener('DOMContentLoaded', () => {
    boot();

    // login
    $('login-form').addEventListener('submit', async (e) => {
      e.preventDefault();
      const btn = $('login-btn'); btn.disabled = true; btn.textContent = '登录中…';
      $('login-msg').textContent = '';
      try {
        const d = await post('/api/admin/login', {
          username: $('login-user').value.trim(), password: $('login-pass').value,
        });
        $('login-pass').value = '';
        enterApp(d.user);
        toast('欢迎回来，' + d.user);
      } catch (err) { $('login-msg').textContent = err.message || '登录失败'; }
      finally { btn.disabled = false; btn.textContent = '登录'; }
    });
    $('btn-logout').addEventListener('click', async () => {
      await post('/api/admin/logout', {});
      $('app-view').hidden = true; $('login-view').hidden = false;
      $('login-msg').textContent = '';
      toast('已退出登录');
    });

    // nav
    document.querySelectorAll('.side-item').forEach((b) =>
      b.addEventListener('click', () => switchView(b.dataset.view)));
    document.querySelectorAll('[data-goto]').forEach((b) =>
      b.addEventListener('click', () => switchView(b.dataset.goto)));

    // products
    $('btn-new-product').addEventListener('click', () => openForm(null));
    ['btn-cancel-form', 'btn-cancel-form-2'].forEach((id) =>
      $(id).addEventListener('click', () => { $('product-form-panel').hidden = true; clearForm(); }));
    $('product-table').addEventListener('click', (e) => {
      const ed = e.target.closest('[data-edit]');
      if (ed) { openForm(PRODUCTS.find((p) => p.id === ed.dataset.edit)); return; }
      const dl = e.target.closest('[data-delete]');
      if (dl && confirm('确定删除这个商品吗？此操作不可撤销。')) {
        del('/api/admin/products/' + encodeURIComponent(dl.dataset.delete))
          .then(() => { toast('已删除'); loadProducts(); })
          .catch((err) => toast(err.message));
      }
    });
    $('product-form').addEventListener('submit', async (e) => {
      e.preventDefault();
      const payload = formPayload();
      if (!payload.name) { $('form-msg').textContent = '请填写商品名称'; return; }
      if (!payload.delivery.length) { $('form-msg').textContent = '至少选择一种发货方式'; return; }
      const btn = $('btn-save-product'); btn.disabled = true; btn.textContent = '保存中…';
      $('form-msg').textContent = '';
      try {
        const id = $('f-id').value.trim();
        if (id) await put('/api/admin/products/' + encodeURIComponent(id), payload);
        else await post('/api/admin/products', payload);
        toast('商品已保存');
        $('product-form-panel').hidden = true;
        clearForm(); loadProducts();
      } catch (err) { $('form-msg').textContent = err.message || '保存失败'; }
      finally { btn.disabled = false; btn.textContent = '保存商品'; }
    });

    // upload buttons inside product form
    document.querySelectorAll('[data-upload-for]').forEach((b) =>
      b.addEventListener('click', () => {
        const inp = document.createElement('input');
        inp.type = 'file';
        inp.accept = b.dataset.uploadFor === 'f-cover'
          ? 'image/*' : '.png,.jpg,.jpeg,.webp,.svg,.pdf,.md,.txt,.zip,.csv,.json,.doc,.docx,.xls,.xlsx';
        inp.onchange = () => { if (inp.files[0]) uploadFile(inp.files[0], b.dataset.uploadFor); };
        inp.click();
      }));

    // orders
    $('btn-refresh-orders').addEventListener('click', loadOrders);
    $('order-table').addEventListener('click', (e) => {
      const b = e.target.closest('[data-order]'); if (!b) return;
      put('/api/admin/orders/' + encodeURIComponent(b.dataset.order), { status: b.dataset.status })
        .then(() => { toast('状态已更新'); loadOrders(); })
        .catch((err) => toast(err.message));
    });

    // media
    $('btn-refresh-media').addEventListener('click', loadMedia);
    const dz = $('dropzone');
    ['dragenter', 'dragover'].forEach((ev) => dz.addEventListener(ev, (e) => {
      e.preventDefault(); dz.classList.add('drag');
    }));
    ['dragleave', 'drop'].forEach((ev) => dz.addEventListener(ev, (e) => {
      e.preventDefault(); dz.classList.remove('drag');
    }));
    dz.addEventListener('drop', (e) => {
      const files = Array.from(e.dataTransfer.files || []);
      files.forEach((f) => uploadFile(f, null));
    });
    $('file-input').addEventListener('change', (e) => {
      Array.from(e.target.files || []).forEach((f) => uploadFile(f, null));
      e.target.value = '';
    });
    $('media-grid').addEventListener('click', (e) => {
      const c = e.target.closest('[data-copy]'); if (!c) return;
      const text = c.dataset.copy;
      (navigator.clipboard ? navigator.clipboard.writeText(text) : Promise.reject())
        .then(() => toast('已复制 URL')).catch(() => toast(text));
    });

    // settings
    $('password-form').addEventListener('submit', async (e) => {
      e.preventDefault();
      const old = $('pw-old').value, nw = $('pw-new').value, nw2 = $('pw-new2').value;
      if (nw !== nw2) { $('pw-msg').textContent = '两次输入的新密码不一致'; return; }
      $('pw-msg').textContent = '';
      try {
        const d = await post('/api/admin/password', { old, new: nw });
        if (!d.ok) { $('pw-msg').textContent = d.msg || '修改失败'; return; }
        $('password-form').reset();
        $('pw-msg').style.color = '#248a3d';
        $('pw-msg').textContent = '密码已更新，请牢记新密码。';
        toast('密码已更新');
        setTimeout(() => { $('pw-msg').style.color = ''; }, 4000);
      } catch (err) { $('pw-msg').textContent = err.message || '修改失败'; }
    });

    // global copy (delegated)
    document.addEventListener('click', (e) => {
      const c = e.target.closest('[data-copy]');
      if (c && !c.closest('#media-grid')) return;
    });
  });
})();
