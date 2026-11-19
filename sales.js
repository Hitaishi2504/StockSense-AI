Pages.sales = (() => {
  let products = [];
  const label = p => `${p.product_name} (ID ${p.product_id})`;
  const matched = () => products.find(p => label(p) === $('#sale-product').value.trim());

  async function load() {
    $('#sale-date').value = $('#sale-date').value || todayStr(); $('#sale-date').max = todayStr();
    try {
      products = (await api('/products?sort=product_name')).items;
      $('#sale-products').innerHTML = products.map(p => `<option value="${esc(label(p))}">`).join('');
      const start = new Date(Date.now() - 29 * 864e5).toISOString().slice(0, 10);
      const [recent, last30] = await Promise.all([api('/sales?limit=100'), api('/sales?limit=2000&start=' + start)]);
      $('#sale-body').innerHTML = recent.items.length ? recent.items.map(s => `<tr><td>${fmt.date(s.sale_date)}</td><td>${esc(s.product_name)}</td><td>${esc(s.category)}</td>
        <td class="num">${s.quantity_sold}</td><td class="num">${fmt.money(s.selling_price)}</td><td class="num">${fmt.money(s.total)}</td>
        <td>${s.is_sample ? badge('sample', 'grey') : badge('entered', 'info')}</td><td><button class="btn sm danger" data-undo="${s.sale_id}" title="Undo this sale"><i class="bi bi-arrow-counterclockwise"></i></button></td></tr>`).join('')
        : `<tr><td colspan="8">${emptyHtml('No sales yet. Record your first sale above.')}</td></tr>`;
      $$('#sale-body [data-undo]').forEach(b => b.onclick = () => undo(b.dataset.undo));
      const items = last30.items, units = items.reduce((a, s) => a + s.quantity_sold, 0), rev = items.reduce((a, s) => a + s.total, 0);
      const by = {}; items.forEach(s => by[s.product_name] = (by[s.product_name] || 0) + s.quantity_sold);
      const top = Object.entries(by).sort((a, b) => b[1] - a[1]).slice(0, 5);
      $('#sale-summary').className = '';
      $('#sale-summary').innerHTML = `<dl class="kv"><dt>Units sold</dt><dd>${fmt.n(units)}</dd><dt>Revenue</dt><dd>${fmt.money(rev)}</dd><dt>Transactions</dt><dd>${items.length}</dd></dl>
        <h4 style="margin:14px 0 6px">Top sellers</h4>${top.length ? top.map(([n, q]) => `<div class="small" style="display:flex;gap:8px;align-items:center;margin-bottom:5px"><span style="width:150px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(n)}</span><div class="bar" style="flex:1"><i style="width:${q / top[0][1] * 100}%"></i></div><b>${q}</b></div>`).join('') : '<span class="muted small">No sales in the last 30 days.</span>'}`;
    } catch (e) { toast(e.message, 'err'); }
  }
  async function save() {
    const err = $('#sale-err'); err.style.display = 'none';
    const m = matched();
    const body = { product: m ? m.product_id : $('#sale-product').value, quantity_sold: $('#sale-qty').value, sale_date: $('#sale-date').value, selling_price: $('#sale-price').value };
    $('#sale-save').disabled = true;
    try {
      const r = await api('/sales', { method: 'POST', body }); toast(r.message, 'ok');
      $('#sale-product').value = ''; $('#sale-qty').value = 1; $('#sale-price').value = ''; load(); App.refreshBadge();
    } catch (e) { err.textContent = e.message; err.style.display = 'block'; }
    $('#sale-save').disabled = false;
  }
  async function undo(id) {
    if (!confirm('Remove this sale? Stock will be restored for sales you entered.')) return;
    try { toast((await api('/sales/' + id, { method: 'DELETE' })).message, 'ok'); load(); App.refreshBadge(); } catch (e) { toast(e.message, 'err'); }
  }
  function init() {
    $('#sale-save').onclick = save;
    $('#sale-product').oninput = () => { const m = matched(); $('#sale-price').placeholder = m ? `${m.selling_price} (stock: ${m.stock_quantity})` : 'Default: product price'; };
  }
  return { load, init };
})();
