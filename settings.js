Pages.settings = (() => {
  const FIELDS = [
    ['store_name', 'Store name', 'text', 'Shown on PDF reports.'],
    ['lead_time_days', 'Supplier lead time (days)', 'number', 'Days between ordering and delivery.'],
    ['cover_days', 'Days of sales to cover per order', 'number', 'Reorder quantity covers lead time + this many days of sales.'],
    ['assumed_cover_days', 'Assumed days of cover at minimum stock', 'number', 'ASSUMPTION used only for products without sales history: daily sales = minimum stock ÷ this.'],
    ['basic_target_multiplier', 'Basic reorder: refill to × minimum', 'number', 'Used only when a product has no sales history.'],
    ['overstock_multiplier', 'Overstocked above × minimum', 'number', 'Stock above this multiple of the minimum is labeled Overstocked.'],
  ];
  async function load() {
    try {
      const d = await api('/settings');
      $('#set-form').innerHTML = FIELDS.map(([k, l, t, h]) => `<div class="field ${k === 'store_name' ? 'full' : ''}"><label>${l}</label><input id="s-${k}" type="${t}" step="any" value="${esc(d.settings[k])}"><span class="muted small">${h}</span></div>`).join('');
      $('#set-data').innerHTML = `<dl class="kv"><dt>Products in database</dt><dd>${d.total_products}</dd><dt>Sample products</dt><dd>${d.sample_products}</dd><dt>Sample sales rows</dt><dd>${d.sample_sales}</dd></dl>
        <p class="muted small mt">Sample data is flagged and kept separate from your own entries and from the forecasting CSV files. Remove it when you are ready to use real products; your own products and sales are not touched.</p>
        <button class="btn danger" id="clear-sample" ${d.sample_products + d.sample_sales ? '' : 'disabled'}><i class="bi bi-trash"></i>Remove sample data</button>
        <hr style="border:0;border-top:1px solid var(--line);margin:18px 0"><h4 style="margin:0 0 6px">Fixed rules</h4>
        <p class="muted small" style="margin:0">Expiry alerts: Urgent ≤ 7 days · Expiring Soon ≤ 30 days · Expired = past expiry date. Sales rates use the last 30 days of recorded sales.</p>`;
      $('#clear-sample').onclick = async () => { if (!confirm('Remove all sample products and sample sales?')) return; try { toast((await api('/settings/clear-sample', { method: 'POST' })).message, 'ok'); load(); App.refreshBadge(); } catch (e) { toast(e.message, 'err'); } };
    } catch (e) { $('#set-form').innerHTML = notice('bad', esc(e.message)); }
  }
  return { load, init() {
    $('#set-save').onclick = async () => {
      const body = {}; FIELDS.forEach(([k]) => body[k] = $('#s-' + k).value);
      try { toast((await api('/settings', { method: 'PUT', body })).message, 'ok'); } catch (e) { toast(e.message, 'err'); }
    };
  } };
})();
