Pages.dashboard = {
  async load() {
    $('#dash-cards').innerHTML = loadingHtml();
    try {
      const d = await api('/dashboard'); const c = d.cards;
      const ps = c.predicted_sales;
      $('#dash-cards').innerHTML =
        statCard('box-seam', 'blue', fmt.n(c.total_products), 'Total products', '', 'inventory') +
        statCard('stack', 'green', fmt.n(c.total_stock), 'Total stock (units)', '', 'inventory') +
        statCard('hourglass-split', 'amber', fmt.n(c.expiring_soon), 'Expiring soon (≤30d)', `${c.urgent} urgent (≤7 days)`, 'expiry') +
        statCard('x-octagon', 'red', fmt.n(c.expired), 'Expired (in stock)', `~${fmt.money(c.value_at_risk)} value at risk`, 'expiry') +
        statCard('exclamation-triangle', 'amber', fmt.n(c.low_stock), 'Low-stock products', '', 'reorder') +
        statCard('graph-up-arrow', 'blue', ps.available ? fmt.compact(ps.next4_total) : '–', 'Predicted sales', ps.available ? 'Next 4 weeks · dataset stores' : esc(ps.reason || 'Train model first'), 'forecast');
      $$('#dash-cards [data-go]').forEach(e => e.onclick = () => location.hash = e.dataset.go);

      makeChart('ch-category', { type: 'bar', data: { labels: d.category_chart.map(x => x.category),
        datasets: [{ label: 'Units in stock', data: d.category_chart.map(x => x.units), backgroundColor: PALETTE, borderRadius: 6 }] },
        options: { plugins: { legend: { display: false } }, scales: { x: { grid: { display: false } } } } });
      makeChart('ch-expiry', { type: 'doughnut', data: { labels: d.expiry_chart.map(x => x.status),
        datasets: [{ data: d.expiry_chart.map(x => x.count), backgroundColor: ['#e5484d', '#f97316', '#f59e0b', '#12a37f'], borderWidth: 0 }] },
        options: { cutout: '62%', plugins: { legend: { position: 'bottom' } } } });

      $('#dash-low').innerHTML = table([{ h: 'Product' }, { h: 'Stock', cls: 'num' }, { h: 'Min', cls: 'num' }, { h: 'Status' }],
        d.low_stock.map(p => `<tr><td>${esc(p.product_name)}</td><td class="num">${p.stock_quantity}</td><td class="num">${p.min_stock_level}</td><td>${stockBadge(p.stock_status)}</td></tr>`), 'No low-stock products 🎉');
      $('#dash-expiring').innerHTML = table([{ h: 'Product' }, { h: 'Stock', cls: 'num' }, { h: 'Status' }],
        d.expiring.map(p => `<tr><td>${esc(p.product_name)}</td><td class="num">${p.stock_quantity}</td><td>${expiryBadge(p.expiry_status, p.days_to_expiry)}</td></tr>`), 'Nothing expiring soon 🎉');
      $('#dash-recent').innerHTML = table([{ h: 'Date' }, { h: 'Product' }, { h: 'Qty', cls: 'num' }],
        d.recent_sales.map(s => `<tr><td>${fmt.date(s.sale_date)}</td><td>${esc(s.product_name)}${s.is_sample ? ' ' + badge('sample', 'grey') : ''}</td><td class="num">${s.quantity_sold}</td></tr>`), 'No sales recorded yet.');
    } catch (e) { $('#dash-cards').innerHTML = notice('bad', esc(e.message), 'x-octagon'); }
    this.loadForecast();
  },
  async loadForecast() {
    $('#dash-insights').innerHTML = loadingHtml();
    try {
      const [s, a] = await Promise.all([api('/forecast/series?store=all&department=all&weeks=8'), api('/forecast/analysis?store=all&department=all')]);
      const hist = s.actual.slice(-26);
      const labels = hist.map(x => x.date).concat((s.future || []).map(x => x.date));
      const ds = [{ label: 'Actual', data: hist.map(x => x.value).concat((s.future || []).map(() => null)), borderColor: '#2f5bea', backgroundColor: '#2f5bea22', tension: .25, pointRadius: 0, fill: true }];
      if (s.future) ds.push({ label: 'Predicted', data: hist.map(() => null).concat(s.future.map(x => x.predicted)), borderColor: '#12a37f', borderDash: [6, 4], tension: .25, pointRadius: 3 });
      makeChart('ch-dash-forecast', { type: 'line', data: { labels, datasets: ds }, options: lineOpts() });
      $('#dash-forecast-note').textContent = s.model_ready ? `Model: ${s.model_name}. Store/department-level forecast from sales.csv — it does not predict individual inventory products.` : 'No model trained yet — only actual history is shown. Train the model on the Sales Forecasting page.';
      $('#dash-insights').className = '';
      $('#dash-insights').innerHTML = '<ul class="insights">' + a.insights.slice(0, 5).map(i => `<li class="${i.kind}"><span class="tag">${i.kind === 'data' ? 'Data' : 'Assumption'}</span>${esc(i.text)}</li>`).join('') + '</ul>';
    } catch (e) {
      $('#dash-insights').className = ''; $('#dash-insights').innerHTML = notice('warn', esc(e.message));
      $('#dash-forecast-note').textContent = 'Forecast unavailable: ' + e.message;
    }
  }
};
