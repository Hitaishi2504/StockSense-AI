Pages.reorder = (() => {
  const recBadge = r => badge(r, r === 'Reorder now' ? 'bad' : r === 'Reorder soon' ? 'warn' : r.startsWith('Hold') ? 'info' : 'ok');
  async function load() {
    $('#ro-body').innerHTML = `<tr><td colspan="10">${loadingHtml()}</td></tr>`;
    try {
      const all = await api('/reorder?filter=all'); const f = $('#ro-filter').value;
      const items = f === 'all' ? all.items : all.items.filter(r => f === 'reorder' ? r.recommendation.startsWith('Reorder') : r.recommendation.startsWith('Hold'));
      const need = all.items.filter(r => r.recommendation.startsWith('Reorder')), hold = all.items.filter(r => r.recommendation.startsWith('Hold'));
      const hist = all.items.filter(r => r.method.startsWith('Sales')).length;
      $('#ro-cards').innerHTML = statCard('arrow-repeat', 'red', need.length, 'Need reordering', `${all.items.filter(r => r.recommendation === 'Reorder now').length} right now`) +
        statCard('pause-circle', 'blue', hold.length, 'Hold – do not restock') + statCard('cash-coin', 'amber', fmt.money(need.reduce((a, r) => a + r.estimated_cost, 0)), 'Est. cost of reorders') +
        statCard('clock-history', 'green', `${hist}/${all.items.length}`, 'Products using sales history');
      const s = all.settings;
      $('#ro-note').innerHTML = `<b>Two clearly labeled methods.</b> <b>Sales-history based</b> (≥3 days of recorded sales in the last 30): reorder point = daily sales × ${s.lead_time_days}-day lead time + minimum stock; order enough to cover lead time + ${s.cover_days} days, capped by shelf life. <b>Basic threshold</b> (no sales history): reorder when stock ≤ minimum, refill to ${s.basic_target_multiplier}× minimum. Expired stock counts as zero. Adjust lead time/cover days in Settings. ${esc(all.note)}`;
      $('#ro-body').innerHTML = items.length ? items.map(r => `<tr><td><b>${esc(r.product_name)}</b></td><td>${esc(r.category)}</td><td class="num">${r.stock_quantity}</td><td class="num">${r.min_stock_level}</td>
        <td>${stockBadge(r.stock_status)}</td><td>${recBadge(r.recommendation)}</td><td class="num"><b>${r.recommended_qty || '–'}</b></td><td class="num">${r.recommended_qty ? fmt.money(r.estimated_cost) : '–'}</td>
        <td>${r.method.startsWith('Sales') ? badge('Sales-based', 'ok') : badge('Basic threshold', 'warn')}</td><td class="wrap">${esc(r.reason)}</td></tr>`).join('') : `<tr><td colspan="10">${emptyHtml('Nothing to show for this filter.')}</td></tr>`;
    } catch (e) { $('#ro-body').innerHTML = `<tr><td colspan="10">${notice('bad', esc(e.message))}</td></tr>`; }
  }
  return { load, init() { $('#ro-filter').onchange = load; } };
})();
