Pages.reports = (() => {
  const R = [
    ['inventory', 'bi-box-seam', 'Inventory report', 'Every product with stock, prices, supplier, expiry date and status.'],
    ['expiry', 'bi-hourglass-split', 'Expiry report', 'Expired and expiring products, value at risk, and recommended actions with reasons.'],
    ['sales', 'bi-receipt', 'Sales analysis report', 'Units, revenue and gross profit per product for a date range (PDF also includes the store-level dataset forecast, clearly labeled).'],
    ['reorder', 'bi-arrow-repeat', 'Reorder report', 'What to order, how much, estimated cost, method used and the reason.'],
  ];
  function render() {
    const end = $('#rep-end')?.value || todayStr(), start = $('#rep-start')?.value || new Date(Date.now() - 29 * 864e5).toISOString().slice(0, 10);
    $('#rep-grid').innerHTML = R.map(([k, ic, t, d]) => `<div class="card report-card"><h3><span><i class="bi ${ic}"></i> ${t}</span></h3><p>${d}</p>
      ${k === 'sales' ? `<div class="toolbar" style="margin:0"><div class="field"><label>From</label><input type="date" id="rep-start" value="${start}"></div><div class="field"><label>To</label><input type="date" id="rep-end" value="${end}"></div></div>` : ''}
      <div style="display:flex;gap:8px"><a class="btn primary" data-k="${k}" data-f="csv"><i class="bi bi-filetype-csv"></i>Download CSV</a><a class="btn" data-k="${k}" data-f="pdf"><i class="bi bi-file-earmark-pdf"></i>Download PDF</a></div></div>`).join('');
    const setLinks = () => $$('#rep-grid a[data-k]').forEach(a => {
      let u = `/api/reports/${a.dataset.k}?format=${a.dataset.f}`;
      if (a.dataset.k === 'sales') u += `&start=${$('#rep-start').value}&end=${$('#rep-end').value}`;
      a.href = u;
    });
    setLinks(); $$('#rep-grid input').forEach(i => i.onchange = setLinks);
  }
  return { load: render, init() {} };
})();
