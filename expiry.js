Pages.expiry = (() => {
  async function load() {
    const cat = $('#exp-cat').value, per = $('#exp-period').value;
    $('#exp-body').innerHTML = `<tr><td colspan="9">${loadingHtml()}</td></tr>`;
    try {
      const [cats, d, r] = await Promise.all([api('/categories'), api(`/expiry?category=${encodeURIComponent(cat)}&period=${per}`), api(`/expiry/recommendations?category=${encodeURIComponent(cat)}`)]);
      fillSelect($('#exp-cat'), cats, 'All categories');
      const s = d.summary;
      $('#exp-cards').innerHTML = statCard('x-octagon', 'red', s.expired, 'Already expired') + statCard('lightning-charge', 'red', s.urgent, 'Urgent (≤ 7 days)') +
        statCard('hourglass-split', 'amber', s.soon, 'Expiring within 30 days') + statCard('shield-exclamation', 'amber', s.high_risk, 'High expiry risk') +
        statCard('cash-coin', 'grey', fmt.money(s.value_at_risk), 'Est. value at risk', 'at purchase price');
      $('#exp-head').innerHTML = '<tr><th>Product</th><th>Category</th><th class="num">Stock</th><th>Expiry date</th><th>Status</th><th>Risk</th><th class="num">Units at risk</th><th class="num">Value at risk</th><th>Sales-rate basis</th></tr>';
      $('#exp-body').innerHTML = d.items.length ? d.items.map(p => `<tr><td><b>${esc(p.product_name)}</b></td><td>${esc(p.category)}</td><td class="num">${p.stock_quantity}</td>
        <td>${fmt.date(p.expiry_date)}</td><td>${expiryBadge(p.expiry_status, p.days_to_expiry)}</td><td>${riskBadge(p.risk_level)}</td><td class="num">${p.units_at_risk}</td>
        <td class="num">${fmt.money(p.value_at_risk)}</td><td>${p.rate_basis === 'sales history' ? badge('sales history', 'ok') : badge('assumption', 'warn')} <span class="muted small">${p.daily_rate}/day</span></td></tr>`).join('')
        : `<tr><td colspan="9">${emptyHtml('No products match this filter. 🎉')}</td></tr>`;
      const wanted = new Set(d.items.map(p => p.product_id));
      const cards = r.items.filter(c => wanted.has(c.product_id));
      $('#exp-recs').innerHTML = cards.length ? cards.map(card).join('') : emptyHtml('No recommendations needed for this filter.');
    } catch (e) { $('#exp-body').innerHTML = `<tr><td colspan="9">${notice('bad', esc(e.message))}</td></tr>`; }
  }
  function card(c) {
    const meta = c.days_to_expiry < 0 ? `Stock ${c.stock_quantity} · expired ${fmt.date(c.expiry_date)}` :
      `Stock ${c.stock_quantity} · expires ${fmt.date(c.expiry_date)} · est. to sell before expiry: <b>${c.expected_sold_before_expiry}</b> · must sell <b>${c.must_sell_per_day}/day</b> to clear (current ≈ ${c.daily_rate}/day, ${c.rate_basis})`;
    return `<div class="rec"><header><b>${esc(c.product_name)}</b><span>${expiryBadge(c.expiry_status, c.days_to_expiry)} ${riskBadge(c.risk_level)}</span></header>
      <div class="meta">${esc(c.category)} · ${meta}</div>
      <ul>${c.actions.map(a => `<li><div class="t">${esc(a.type)}</div><div>${esc(a.action)}</div><div class="why">Why: ${esc(a.reason)}</div></li>`).join('')}</ul></div>`;
  }
  function init() { $('#exp-cat').onchange = load; $('#exp-period').onchange = load; }
  return { load, init };
})();
