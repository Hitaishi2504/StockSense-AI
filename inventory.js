Pages.inventory = (() => {
  let sort = 'product_id', dir = 'asc', page = 1, items = [], editing = null;
  const PER = 15;
  const COLS = [['product_id', 'ID'], ['product_name', 'Product'], ['category', 'Category'], ['stock_quantity', 'Stock', 'num'], ['min_stock_level', 'Min', 'num'],
    ['purchase_price', 'Buy', 'num'], ['selling_price', 'Sell', 'num'], ['supplier', 'Supplier'], ['expiry_date', 'Expiry'], ['days_to_expiry', 'Expiry status'], ['stock_status', 'Stock status']];

  async function load() {
    $('#inv-head').innerHTML = '<tr>' + COLS.map(([k, h, c]) => `<th class="sortable ${c || ''}" data-k="${k}">${h}${sort === k ? (dir === 'asc' ? ' ▲' : ' ▼') : ''}</th>`).join('') + '<th></th></tr>';
    $$('#inv-head th.sortable').forEach(th => th.onclick = () => { const k = th.dataset.k; dir = sort === k && dir === 'asc' ? 'desc' : 'asc'; sort = k; load(); });
    const q = new URLSearchParams({ q: $('#inv-q').value, category: $('#inv-cat').value, stock_status: $('#inv-stock').value, expiry_status: $('#inv-exp').value, sort, dir });
    $('#inv-body').innerHTML = `<tr><td colspan="12">${loadingHtml()}</td></tr>`;
    try { items = (await api('/products?' + q)).items; } catch (e) { $('#inv-body').innerHTML = `<tr><td colspan="12">${notice('bad', esc(e.message))}</td></tr>`; return; }
    refreshCategories(); render();
  }
  async function refreshCategories() {
    const cats = await api('/categories'); fillSelect($('#inv-cat'), cats, 'All categories');
    $('#cat-list').innerHTML = cats.map(c => `<option value="${esc(c)}">`).join('');
    const sup = await api('/suppliers'); $('#sup-list').innerHTML = sup.map(c => `<option value="${esc(c)}">`).join('');
  }
  function render() {
    const pages = Math.max(1, Math.ceil(items.length / PER)); page = Math.min(page, pages);
    const slice = items.slice((page - 1) * PER, page * PER);
    $('#inv-body').innerHTML = slice.length ? slice.map(p => `<tr>
      <td>${p.product_id}${p.is_sample ? ' ' + badge('sample') : ''}</td><td><b>${esc(p.product_name)}</b></td><td>${esc(p.category)}</td>
      <td class="num">${p.stock_quantity}</td><td class="num">${p.min_stock_level}</td><td class="num">${fmt.money(p.purchase_price)}</td><td class="num">${fmt.money(p.selling_price)}</td>
      <td>${esc(p.supplier || '–')}</td><td>${fmt.date(p.expiry_date)}</td><td>${expiryBadge(p.expiry_status, p.days_to_expiry)}</td><td>${stockBadge(p.stock_status)}</td>
      <td><button class="btn sm" data-edit="${p.product_id}" title="Edit"><i class="bi bi-pencil"></i></button> <button class="btn sm danger" data-del="${p.product_id}" title="Delete"><i class="bi bi-trash"></i></button></td></tr>`).join('')
      : `<tr><td colspan="12">${emptyHtml('No products match. Use “Add product” to create one.')}</td></tr>`;
    $$('#inv-body [data-edit]').forEach(b => b.onclick = () => openModal(items.find(p => p.product_id == b.dataset.edit)));
    $$('#inv-body [data-del]').forEach(b => b.onclick = () => del(items.find(p => p.product_id == b.dataset.del)));
    $('#inv-pager').innerHTML = `${items.length} product(s) · page ${page}/${pages} <button class="btn sm" id="pg-prev" ${page <= 1 ? 'disabled' : ''}>Prev</button><button class="btn sm" id="pg-next" ${page >= pages ? 'disabled' : ''}>Next</button>`;
    $('#pg-prev').onclick = () => { page--; render(); }; $('#pg-next').onclick = () => { page++; render(); };
  }
  function openModal(p) {
    editing = p || null; $('#prod-title').textContent = p ? `Edit product #${p.product_id}` : 'Add product'; $('#prod-err').style.display = 'none';
    const v = (id, val) => $(id).value = val ?? '';
    v('#f-name', p?.product_name); v('#f-category', p?.category); v('#f-supplier', p?.supplier); v('#f-stock', p?.stock_quantity ?? 0); v('#f-min', p?.min_stock_level ?? 0);
    v('#f-buy', p?.purchase_price); v('#f-sell', p?.selling_price); v('#f-mfg', p?.manufacturing_date); v('#f-exp', p?.expiry_date);
    $('#prod-modal').classList.add('open'); $('#f-name').focus();
  }
  const closeModal = () => $('#prod-modal').classList.remove('open');
  async function save() {
    const body = { product_name: $('#f-name').value, category: $('#f-category').value, supplier: $('#f-supplier').value, stock_quantity: $('#f-stock').value,
      min_stock_level: $('#f-min').value, purchase_price: $('#f-buy').value, selling_price: $('#f-sell').value, manufacturing_date: $('#f-mfg').value, expiry_date: $('#f-exp').value };
    try {
      const r = editing ? await api('/products/' + editing.product_id, { method: 'PUT', body }) : await api('/products', { method: 'POST', body });
      toast(r.message, 'ok'); closeModal(); load(); App.refreshBadge();
    } catch (e) { const el = $('#prod-err'); el.textContent = e.message; el.style.display = 'block'; }
  }
  async function del(p) {
    if (!confirm(`Delete “${p.product_name}”? Its sales history will also be deleted.`)) return;
    try { toast((await api('/products/' + p.product_id, { method: 'DELETE' })).message, 'ok'); load(); App.refreshBadge(); } catch (e) { toast(e.message, 'err'); }
  }
  function init() {
    $('#inv-add').onclick = () => openModal(null);
    $('#prod-cancel').onclick = closeModal; $('#prod-save').onclick = save;
    $('#prod-modal').onclick = e => { if (e.target.id === 'prod-modal') closeModal(); };
    const reload = () => { page = 1; load(); };
    $('#inv-q').oninput = debounce(reload); ['#inv-cat', '#inv-stock', '#inv-exp'].forEach(s => $(s).onchange = reload);
  }
  return { load, init };
})();
