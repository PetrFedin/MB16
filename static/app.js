const tg = window.Telegram?.WebApp;
if (tg) {
  tg.ready();
  tg.expand();
}

const $ = id => document.getElementById(id);
const content = $('content');
const nav = $('bottomNav');
const modal = $('modalBackdrop');
const body = $('modalBody');
const state = {me: null, view: 'catalog', tab: 'products', products: [], adminProducts: [], selection: [], fittings: []};
const debug = new URLSearchParams(location.search).get('debug_user');

function headers(json = false) {
  const h = {};
  if (tg?.initData) h['X-Telegram-Init-Data'] = tg.initData;
  if (debug) h['X-Debug-User-Id'] = debug;
  if (json) h['Content-Type'] = 'application/json';
  return h;
}

async function api(path, o = {}) {
  const r = await fetch(path, {
    ...o,
    headers: {...headers(!!o.json), ...(o.headers || {})},
    body: o.json ? JSON.stringify(o.json) : o.body,
  });
  if (!r.ok) {
    let m = `Ошибка ${r.status}`;
    try {
      m = (await r.json()).detail || m;
    } catch {}
    throw Error(m);
  }
  return r.json();
}

const esc = v => String(v ?? '').replace(/[&<>'"]/g, c => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;',
}[c]));
const money = v => new Intl.NumberFormat('ru-RU', {style: 'currency', currency: 'RUB', maximumFractionDigits: 0}).format(+v || 0);
const img = m => (m || []).find(x => x.type === 'image')?.url || '';

function localDateISO() {
  const d = new Date();
  const p = n => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}

function toast(t) {
  const n = $('toast');
  n.textContent = t;
  n.classList.remove('hidden');
  clearTimeout(toast.t);
  toast.t = setTimeout(() => n.classList.add('hidden'), 2200);
}

function open(title, sub, html) {
  $('modalTitle').textContent = title;
  $('modalEyebrow').textContent = sub || '';
  body.innerHTML = html;
  modal.classList.remove('hidden');
  document.body.style.overflow = 'hidden';
}

function close() {
  modal.classList.add('hidden');
  body.innerHTML = '';
  document.body.style.overflow = '';
}

$('modalClose').onclick = close;
modal.onclick = e => {
  if (e.target === modal) close();
};

const status = s => ({
  available: 'В продаже',
  hidden: 'Скрыт',
  sold: 'Продан',
  new: 'Новая',
  confirmed: 'Подтверждена',
  completed: 'Клиент пришёл',
  declined: 'Отклонена',
  cancelled: 'Отменена',
})[s] || s;
const av = s => ({pending: 'Не проверено', available: 'Есть', unavailable: 'Нет'})[s] || s;

function head(t, s = '', a = '') {
  return `<div class="section-head"><div><h1>${esc(t)}</h1>${s ? `<p>${esc(s)}</p>` : ''}</div>${a}</div>`;
}

function thumb(p) {
  const u = img(p.media);
  return u ? `<img src="${esc(u)}" alt="${esc(p.name)}">` : 'Нет фото';
}

function navRender() {
  const n = [
    ['catalog', '⌂', 'Каталог'],
    ['selection', '♡', 'Подборка'],
    ['fittings', '◷', 'Примерки'],
    ['purchases', '✓', 'Покупки'],
  ];
  if (state.me?.is_admin) n.push(['admin', '⚙', 'Админ']);
  nav.style.setProperty('--nav-count', n.length);
  nav.innerHTML = n.map(x => `<button class="nav-btn ${state.view === x[0] ? 'active' : ''}" data-v="${x[0]}"><span class="nav-icon">${x[1]}</span>${x[2]}</button>`).join('');
  nav.querySelectorAll('[data-v]').forEach(b => b.onclick = () => show(b.dataset.v));
}

async function show(v) {
  state.view = v;
  navRender();
  content.innerHTML = '<div class="empty">Загрузка…</div>';
  try {
    if (v === 'catalog') await catalog();
    if (v === 'selection') await selection();
    if (v === 'fittings') await fittings();
    if (v === 'purchases') await purchases();
    if (v === 'admin') await admin();
  } catch (e) {
    content.innerHTML = `<div class="empty"><strong>Не получилось загрузить</strong>${esc(e.message)}</div>`;
  }
}

async function catalog() {
  state.products = await api('/api/products');
  content.innerHTML = head('Каталог', `${state.products.length} доступно`) + (state.products.length
    ? `<div class="grid">${state.products.map(p => `<article class="product-card" data-p="${p.id}"><div class="product-image">${thumb(p)}${p.media.length > 1 ? `<span class="media-count">${p.media.length}</span>` : ''}</div><div class="product-copy"><div class="product-name">${esc(p.name)}</div><div class="product-meta"><span>${esc(p.article)}</span><span>${esc(p.category)}</span></div><div class="price">${money(p.price)}</div></div></article>`).join('')}</div>`
    : '<div class="empty"><strong>Пока пусто</strong>Карточек ещё нет.</div>');
  content.querySelectorAll('[data-p]').forEach(c => c.onclick = () => product(+c.dataset.p));
}

function product(id) {
  const p = state.products.find(x => x.id === id);
  const gallery = p.media.map(m => m.type === 'video'
    ? `<video controls playsinline src="${esc(m.url)}"></video>`
    : `<img src="${esc(m.url)}" alt="${esc(p.name)}">`).join('');
  open(p.name, `${p.category} · ${p.article}`, `<div class="gallery">${gallery}</div><div class="window"><div class="price">${money(p.price)}</div>${p.description ? `<p>${esc(p.description)}</p>` : ''}<div class="field"><label>Цвет</label><select class="input" id="pc">${p.colors.map(x => `<option>${esc(x)}</option>`).join('')}</select></div><div class="field"><label>Размер</label><select class="input" id="ps">${p.sizes.map(x => `<option>${esc(x)}</option>`).join('')}</select></div><button class="btn full" id="add">Добавить в подборку</button></div>`);
  $('add').onclick = async () => {
    try {
      await api('/api/selection', {method: 'POST', json: {product_id: p.id, color: $('pc').value, size: $('ps').value}});
      tg?.HapticFeedback?.notificationOccurred('success');
      toast('Добавлено');
      close();
    } catch (e) {
      toast(e.message);
    }
  };
}

async function selection() {
  state.selection = await api('/api/selection');
  const total = state.selection.reduce((a, x) => a + x.product.price, 0);
  content.innerHTML = head('Подборка', state.selection.length ? `${state.selection.length} вещей · ${money(total)}` : 'Выберите вещи', state.selection.length ? '<button class="btn small" id="book">Примерить</button>' : '') + (state.selection.length
    ? state.selection.map(i => `<div class="window window-row"><div class="thumb">${thumb(i.product)}</div><div class="grow"><div class="row-title">${esc(i.product.name)}</div><div class="row-sub">${esc(i.color)} · ${esc(i.size)}</div><div class="row-price">${money(i.product.price)}</div></div><button class="icon-btn" data-del="${i.id}">×</button></div>`).join('')
    : '<div class="empty"><strong>Подборка пустая</strong>Откройте карточку, выберите цвет и размер.</div>');
  content.querySelectorAll('[data-del]').forEach(b => b.onclick = async () => {
    try {
      await api('/api/selection/' + b.dataset.del, {method: 'DELETE'});
      await selection();
    } catch (e) {
      toast(e.message);
    }
  });
  if ($('book')) $('book').onclick = book;
}

function book() {
  const d = localDateISO();
  open('Запрос на примерку', `${state.selection.length} вещей`, `<div class="window"><div class="two-col"><div class="field"><label>Дата</label><input class="input" id="fd" type="date" min="${d}" value="${d}"></div><div class="field"><label>Время</label><input class="input" id="ft" type="time" value="14:00"></div></div><div class="field"><label>Комментарий</label><textarea class="input" id="fc" placeholder="Необязательно"></textarea></div><div class="inline-note">Администратор проверит наличие и подтвердит время.</div><button class="btn full" id="sendFit">Отправить запрос</button></div>`);
  $('sendFit').onclick = async () => {
    try {
      await api('/api/fittings', {method: 'POST', json: {date: $('fd').value, time: $('ft').value + ':00', comment: $('fc').value}});
      close();
      toast('Запрос отправлен');
      show('fittings');
    } catch (e) {
      toast(e.message);
    }
  };
}

async function fittings() {
  state.fittings = await api('/api/fittings/my');
  content.innerHTML = head('Примерки', 'Запросы и подтверждения') + (state.fittings.length
    ? state.fittings.map(r => `<div class="window"><div class="request-head"><div><div class="row-title">Примерка #${r.id}</div><div class="row-sub">${r.confirmed_date || r.requested_date} · ${r.confirmed_time || r.requested_time}</div></div><span class="status ${r.status === 'confirmed' ? 'good' : ''}">${status(r.status)}</span></div>${r.admin_note ? `<div class="inline-note">${esc(r.admin_note)}</div>` : ''}<div class="request-items">${r.items.map(i => `<div class="request-item"><div class="row-title">${esc(i.name)}</div><div class="row-sub">${esc(i.color)} · ${esc(i.size)} · ${av(i.availability)}</div></div>`).join('')}</div>${r.status === 'confirmed' ? '<div class="inline-note">После визита администратор отметит, что вы пришли. Затем можно будет зафиксировать покупки.</div>' : ''}${r.status === 'completed' ? `<button class="btn full" data-buy="${r.id}">Отметить, что купил</button>` : ''}</div>`).join('')
    : '<div class="empty"><strong>Запросов нет</strong></div>');
  content.querySelectorAll('[data-buy]').forEach(b => b.onclick = () => buy(+b.dataset.buy));
}

function buy(id) {
  const r = state.fittings.find(x => x.id === id);
  const items = r.items.filter(i => i.availability === 'available');
  open('Что купили?', 'Отметка клиента', `<div class="window">${items.map(i => `<label class="request-item" style="display:block"><input type="checkbox" data-ci="${i.id}" ${i.purchased_claimed ? 'checked' : ''} ${i.sold_confirmed ? 'disabled' : ''}> ${esc(i.name)} · ${esc(i.color)} · ${esc(i.size)}${i.sold_confirmed ? ' · подтверждено' : ''}</label>`).join('')}<button class="btn full" id="saveBuy">Сохранить</button></div>`);
  $('saveBuy').onclick = async () => {
    const item_ids = [...body.querySelectorAll('[data-ci]:checked')].map(x => +x.dataset.ci);
    try {
      await api(`/api/fittings/${id}/purchases`, {method: 'POST', json: {item_ids}});
      close();
      toast('Сохранено');
      show('purchases');
    } catch (e) {
      toast(e.message);
    }
  };
}

async function purchases() {
  const p = await api('/api/purchases/my');
  content.innerHTML = head('Покупки', 'История в личном кабинете') + (p.length
    ? p.map(i => `<div class="window window-row"><div class="thumb">${thumb({name: i.name, media: i.media})}</div><div class="grow"><div class="row-title">${esc(i.name)}</div><div class="row-sub">${esc(i.article)} · ${esc(i.color)} · ${esc(i.size)}</div><div class="row-price">${money(i.price)}</div><div class="row-sub">${i.date} · ${i.confirmed ? 'подтверждено' : 'ожидает подтверждения'}</div></div></div>`).join('')
    : '<div class="empty"><strong>История пустая</strong></div>');
}

async function admin() {
  if (!state.me.is_admin) return;
  const tabs = `<div class="tabs"><button class="tab ${state.tab === 'products' ? 'active' : ''}" data-tab="products">Карточки</button><button class="tab ${state.tab === 'requests' ? 'active' : ''}" data-tab="requests">Запросы</button></div>`;
  if (state.tab === 'products') {
    const p = await api('/api/admin/products');
    state.adminProducts = p;
    content.innerHTML = head('Админ', 'Товары и примерки', '<button class="btn small" id="newP">+ Карточка</button>') + tabs + `<div class="kpi-row"><div class="kpi"><strong>${p.length}</strong><span>всего</span></div><div class="kpi"><strong>${p.filter(x => x.status === 'available').length}</strong><span>доступно</span></div><div class="kpi"><strong>${p.filter(x => x.status === 'sold').length}</strong><span>продано</span></div></div>` + p.map(x => `<div class="window window-row"><div class="thumb">${thumb(x)}</div><div class="grow"><div class="row-title">${esc(x.name)}</div><div class="row-sub">${esc(x.article)} · ${esc(x.colors.join(', '))} · ${esc(x.sizes.join(', '))}</div><div class="row-price">${money(x.price)}</div></div><div><span class="status">${status(x.status)}</span><div class="admin-checks" style="margin-top:7px"><button class="btn small secondary" data-edit="${x.id}">Изменить</button>${x.status !== 'available' ? `<button class="btn small secondary" data-st="${x.id}:available">Вернуть</button>` : `<button class="btn small secondary" data-st="${x.id}:hidden">Скрыть</button>`}${x.status !== 'sold' ? `<button class="btn small danger" data-st="${x.id}:sold">Продано</button>` : ''}</div></div></div>`).join('');
    $('newP').onclick = newProduct;
    content.querySelectorAll('[data-edit]').forEach(b => b.onclick = () => editProduct(+b.dataset.edit));
    content.querySelectorAll('[data-st]').forEach(b => b.onclick = async () => {
      const [id, s] = b.dataset.st.split(':');
      try {
        await api(`/api/admin/products/${id}/status`, {method: 'PATCH', json: {status: s}});
        await admin();
      } catch (e) {
        toast(e.message);
      }
    });
  } else {
    const rs = await api('/api/admin/fittings');
    content.innerHTML = head('Админ', 'Проверка запросов') + tabs + (rs.length ? rs.map(requestAdmin).join('') : '<div class="empty"><strong>Запросов нет</strong></div>');
    bindRequests();
  }
  content.querySelectorAll('[data-tab]').forEach(b => b.onclick = () => {
    state.tab = b.dataset.tab;
    admin();
  });
}

function newProduct() {
  open('Новая карточка', '3–5 фото, видео опционально', `<div class="window"><div class="field"><label>Название</label><input class="input" id="pn"></div><div class="two-col"><div class="field"><label>Артикул</label><input class="input" id="pa"></div><div class="field"><label>Цена, ₽</label><input class="input" id="pp" type="number"></div></div><div class="field"><label>Категория</label><select class="input" id="pk"><option>Одежда</option><option>Обувь</option><option>Сумки</option><option>Аксессуары</option></select></div><div class="field"><label>Цвета через запятую</label><input class="input" id="pc2" placeholder="Черный, Бежевый"></div><div class="field"><label>Размеры через запятую</label><input class="input" id="ps2" placeholder="46, 48, 50"></div><div class="field"><label>Описание</label><textarea class="input" id="pd"></textarea></div><div class="field"><label>Фото 3–5</label><input class="input" id="pi" type="file" accept="image/jpeg,image/png,image/webp" multiple><div id="ipreview" style="display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin-top:8px"></div></div><div class="field"><label>Видео, необязательно</label><input class="input" id="pv" type="file" accept="video/mp4,video/quicktime,video/webm"></div><button class="btn full" id="publish">Опубликовать</button></div>`);
  $('pi').onchange = () => {
    const files = [...$('pi').files];
    $('ipreview').innerHTML = files.map(f => `<img src="${URL.createObjectURL(f)}" alt="Предпросмотр" style="width:100%;aspect-ratio:3/4;object-fit:cover;border-radius:10px">`).join('');
  };
  $('publish').onclick = publish;
}

async function publish() {
  const images = [...$('pi').files];
  if (images.length < 3 || images.length > 5) return toast('Нужно 3–5 фото');
  if (!$('pn').value || !$('pa').value || !$('pp').value || !$('pc2').value || !$('ps2').value) return toast('Заполните обязательные поля');
  const f = new FormData();
  [['name', 'pn'], ['article', 'pa'], ['price', 'pp'], ['category', 'pk'], ['colors', 'pc2'], ['sizes', 'ps2'], ['description', 'pd']].forEach(([k, id]) => f.append(k, $(id).value));
  images.forEach(x => f.append('images', x));
  if ($('pv').files[0]) f.append('video', $('pv').files[0]);
  $('publish').disabled = true;
  try {
    await api('/api/admin/products', {method: 'POST', body: f});
    close();
    toast('Опубликовано');
    admin();
  } catch (e) {
    toast(e.message);
    $('publish').disabled = false;
  }
}

function editProduct(id) {
  const p = state.adminProducts.find(x => x.id === id);
  if (!p) return;
  open('Изменить карточку', p.article, `<div class="window"><div class="field"><label>Название</label><input class="input" id="en" value="${esc(p.name)}"></div><div class="two-col"><div class="field"><label>Артикул</label><input class="input" id="ea" value="${esc(p.article)}"></div><div class="field"><label>Цена, ₽</label><input class="input" id="ep" type="number" value="${p.price}"></div></div><div class="field"><label>Категория</label><input class="input" id="ek" value="${esc(p.category)}"></div><div class="field"><label>Цвета через запятую</label><input class="input" id="ec" value="${esc(p.colors.join(', '))}"></div><div class="field"><label>Размеры через запятую</label><input class="input" id="es" value="${esc(p.sizes.join(', '))}"></div><div class="field"><label>Информация</label><textarea class="input" id="ed">${esc(p.description || '')}</textarea></div><div class="inline-note">Фото и видео в этой версии остаются без изменений.</div><button class="btn full" id="saveEdit">Сохранить</button></div>`);
  $('saveEdit').onclick = async () => {
    const j = {
      name: $('en').value.trim(),
      article: $('ea').value.trim(),
      price: +$('ep').value,
      category: $('ek').value.trim(),
      colors: $('ec').value.split(',').map(x => x.trim()).filter(Boolean),
      sizes: $('es').value.split(',').map(x => x.trim()).filter(Boolean),
      description: $('ed').value.trim(),
    };
    if (!j.name || !j.article || !j.price || !j.colors.length || !j.sizes.length) return toast('Заполните обязательные поля');
    try {
      await api(`/api/admin/products/${id}`, {method: 'PATCH', json: j});
      close();
      toast('Карточка обновлена');
      admin();
    } catch (e) {
      toast(e.message);
    }
  };
}

function requestAdmin(r) {
  const who = r.client.username ? '@' + r.client.username : r.client.name || r.client.telegram_id;
  const checks = r.status === 'new';
  const date = r.confirmed_date || r.requested_date;
  const time = r.confirmed_time || r.requested_time;
  const actions = r.status === 'new'
    ? `<button class="btn" data-up="${r.id}:confirmed">Подтвердить</button><button class="btn danger" data-up="${r.id}:declined">Отклонить</button>`
    : r.status === 'confirmed'
      ? `<button class="btn secondary" data-reschedule="${r.id}">Сохранить время</button><button class="btn" data-up="${r.id}:completed">Клиент пришёл</button><button class="btn danger" data-up="${r.id}:cancelled">Отменить</button>`
      : '';
  return `<div class="window" data-r="${r.id}"><div class="request-head"><div><div class="row-title">${esc(who)} · #${r.id}</div><div class="row-sub">Запрос: ${r.requested_date} · ${r.requested_time}</div></div><span class="status ${['confirmed', 'completed'].includes(r.status) ? 'good' : ''}">${status(r.status)}</span></div>${r.comment ? `<div class="inline-note">${esc(r.comment)}</div>` : ''}<div class="request-items">${r.items.map(i => `<div class="request-item"><div class="row-title">${esc(i.name)}</div><div class="row-sub">${esc(i.article)} · ${esc(i.color)} · ${esc(i.size)}</div><div class="admin-checks">${checks ? `<button class="btn small ${i.availability === 'available' ? '' : 'secondary'}" data-av="${r.id}:${i.id}:available">Есть</button><button class="btn small ${i.availability === 'unavailable' ? 'danger' : 'secondary'}" data-av="${r.id}:${i.id}:unavailable">Нет</button>` : `<span class="status ${i.availability === 'available' ? 'good' : i.availability === 'unavailable' ? 'bad' : ''}">${av(i.availability)}</span>`}${i.purchased_claimed && !i.sold_confirmed ? `<button class="btn small" data-sale="${r.id}:${i.id}">Продано</button>` : ''}${i.sold_confirmed ? '<span class="status good">Продажа подтверждена</span>' : ''}</div></div>`).join('')}</div>${['new', 'confirmed'].includes(r.status) ? `<div class="two-col"><div class="field"><label>Дата</label><input class="input" data-date="${r.id}" type="date" value="${date}"></div><div class="field"><label>Время</label><input class="input" data-time="${r.id}" type="time" value="${time}"></div></div>` : ''}<div class="field"><label>Комментарий клиенту</label><input class="input" data-note="${r.id}" value="${esc(r.admin_note || '')}" ${r.status === 'completed' ? 'disabled' : ''}></div>${actions ? `<div class="button-row">${actions}</div>` : ''}</div>`;
}

function bindRequests() {
  content.querySelectorAll('[data-av]').forEach(b => b.onclick = async () => {
    const [r, i, a] = b.dataset.av.split(':');
    try {
      await api(`/api/admin/fittings/${r}/items/${i}`, {method: 'PATCH', json: {availability: a}});
      admin();
    } catch (e) {
      toast(e.message);
    }
  });

  content.querySelectorAll('[data-reschedule]').forEach(b => b.onclick = async () => {
    const r = b.dataset.reschedule;
    const j = {
      confirmed_date: content.querySelector(`[data-date="${r}"]`).value,
      confirmed_time: content.querySelector(`[data-time="${r}"]`).value,
      admin_note: content.querySelector(`[data-note="${r}"]`)?.value || '',
    };
    try {
      await api(`/api/admin/fittings/${r}`, {method: 'PATCH', json: j});
      toast('Время обновлено');
      admin();
    } catch (e) {
      toast(e.message);
    }
  });

  content.querySelectorAll('[data-up]').forEach(b => b.onclick = async () => {
    const [r, s] = b.dataset.up.split(':');
    const j = {status: s, admin_note: content.querySelector(`[data-note="${r}"]`)?.value || ''};
    if (s === 'confirmed') {
      j.confirmed_date = content.querySelector(`[data-date="${r}"]`).value;
      j.confirmed_time = content.querySelector(`[data-time="${r}"]`).value;
    }
    try {
      await api(`/api/admin/fittings/${r}`, {method: 'PATCH', json: j});
      toast('Обновлено');
      admin();
    } catch (e) {
      toast(e.message);
    }
  });

  content.querySelectorAll('[data-sale]').forEach(b => b.onclick = async () => {
    const [r, i] = b.dataset.sale.split(':');
    try {
      await api(`/api/admin/fittings/${r}/items/${i}/confirm-sale`, {method: 'POST'});
      toast('Продажа подтверждена');
      admin();
    } catch (e) {
      toast(e.message);
    }
  });
}

$('profileButton').onclick = () => state.me && open(
  state.me.name || state.me.username || 'Профиль',
  state.me.is_admin ? 'Администратор' : 'Клиент',
  `<div class="window"><div class="row-title">Telegram ID</div><div class="row-sub">${state.me.telegram_id}</div></div>`,
);

(async () => {
  try {
    state.me = await api('/api/me');
    $('brandTitle').textContent = state.me.app_name || 'MB16';
    $('profileButton').textContent = state.me.is_admin ? 'Админ' : (state.me.name || 'Профиль');
    navRender();
    show('catalog');
  } catch (e) {
    nav.innerHTML = '';
    content.innerHTML = `<div class="empty"><strong>Не удалось войти</strong>${esc(e.message)}</div>`;
  }
})();
