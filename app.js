const App = (() => {
  const TITLES = {
    dashboard: ['Dashboard', 'Overview of your inventory, expiry risk and sales forecast'],
    inventory: ['Inventory', 'Add, edit, search and track your products'],
    expiry: ['Expiry Alerts', 'Products expiring soon, with smart selling strategies'],
    sales: ['Sales', 'Record product sales — stock updates automatically'],
    forecast: ['Sales Forecasting', 'Store & department sales analysis and ML forecast (dataset-level)'],
    reorder: ['Reorder Recommendations', 'What to restock, how much, and why'],
    reports: ['Reports', 'Download CSV or PDF reports'],
    settings: ['Settings', 'Store details and calculation settings'],
  };
  const inited = new Set();
  function show() {
    const p = (location.hash || '#dashboard').slice(1); const page = TITLES[p] ? p : 'dashboard';
    $$('.page').forEach(s => s.classList.toggle('active', s.id === 'page-' + page));
    $$('#nav a').forEach(a => a.classList.toggle('active', a.dataset.page === page));
    $('#page-title').textContent = TITLES[page][0]; $('#page-sub').textContent = TITLES[page][1];
    $('#sidebar').classList.remove('open');
    if (!inited.has(page)) { inited.add(page); Pages[page].init && Pages[page].init(); }
    Pages[page].load();
  }
  async function refreshBadge() {
    try {
      const d = await api('/expiry?period=all'); const n = d.summary.urgent + d.summary.expired, el = $('#nav-expiry');
      el.hidden = !n; el.textContent = n;
    } catch (e) { /* ignore */ }
  }
  function boot() {
    $$('#nav a').forEach(a => a.onclick = () => { location.hash = a.dataset.page; });
    $('#menu-btn').onclick = () => $('#sidebar').classList.toggle('open');
    window.addEventListener('hashchange', show);
    show(); refreshBadge();
  }
  return { boot, refreshBadge };
})();
document.addEventListener('DOMContentLoaded', App.boot);
