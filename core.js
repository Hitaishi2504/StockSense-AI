/* Shared helpers */
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const Pages = {};

async function api(path, opts = {}) {
  const init = { method: opts.method || 'GET', headers: {} };
  if (opts.body !== undefined) { init.headers['Content-Type'] = 'application/json'; init.body = JSON.stringify(opts.body); }
  let res;
  try { res = await fetch('/api' + path, init); }
  catch (e) { throw new Error('Cannot reach the server. Is "python run.py" still running?'); }
  let data = null;
  try { data = await res.json(); } catch (e) { /* not json */ }
  if (!res.ok) { const err = new Error((data && data.error) || res.statusText); err.status = res.status; err.code = data && data.code; throw err; }
  return data;
}

function toast(msg, type = '') {
  const t = document.createElement('div');
  t.className = 'toast ' + type; t.textContent = msg;
  $('#toasts').appendChild(t);
  setTimeout(() => t.remove(), type === 'err' ? 6500 : 3500);
}

const fmt = {
  n: v => v == null ? '–' : Number(v).toLocaleString(),
  money: v => v == null ? '–' : Number(v).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }),
  compact: v => v == null ? '–' : new Intl.NumberFormat('en', { notation: 'compact', maximumFractionDigits: 1 }).format(v),
  pct: (v, d = 1) => v == null ? '–' : (v > 0 ? '+' : '') + Number(v).toFixed(d) + '%',
  date: s => s ? new Date(s + 'T00:00:00').toLocaleDateString(undefined, { day: '2-digit', month: 'short', year: 'numeric' }) : '–',
};

const badge = (t, k = 'grey') => `<span class="badge b-${k}">${esc(t)}</span>`;
function expiryBadge(status, days) {
  const k = { Expired: 'bad', Urgent: 'bad', 'Expiring Soon': 'warn', Safe: 'ok' }[status] || 'grey';
  const label = status === 'Expired' ? `Expired (${-days}d ago)` : status === 'Safe' ? 'Safe' : `${status} · ${days}d`;
  return badge(label, k);
}
const stockBadge = s => badge(s, { 'Out of Stock': 'bad', Critical: 'bad', Low: 'warn', Adequate: 'ok', Overstocked: 'info' }[s] || 'grey');
const riskBadge = s => badge(s === 'Expired' ? 'Expired' : s + ' risk', { Expired: 'bad', High: 'bad', Medium: 'warn', Low: 'ok' }[s] || 'grey');
const loadingHtml = (m = 'Loading…') => `<div class="loading"><span class="spin"></span>${esc(m)}</div>`;
const emptyHtml = m => `<div class="empty">${esc(m)}</div>`;
const notice = (kind, html, icon = 'info-circle') => `<div class="notice ${kind}"><i class="bi bi-${icon}"></i><div>${html}</div></div>`;

function statCard(icon, color, value, label, sub = '', go = '') {
  return `<div class="card stat" ${go ? `data-go="${go}" style="cursor:pointer"` : ''}><div class="ico i-${color}"><i class="bi bi-${icon}"></i></div>
    <div><div class="v">${value}</div><div class="l">${label}</div>${sub ? `<div class="s">${sub}</div>` : ''}</div></div>`;
}

const PALETTE = ['#2f5bea', '#12a37f', '#f59e0b', '#e5484d', '#8b5cf6', '#06b6d4', '#ec4899', '#84cc16'];
const _charts = {};
function makeChart(id, config) {
  if (_charts[id]) _charts[id].destroy();
  const canvas = document.getElementById(id);
  if (typeof Chart === 'undefined') { canvas.parentElement.innerHTML = '<div class="empty">Chart.js could not load (check your internet connection).</div>'; return null; }
  const dark = matchMedia('(prefers-color-scheme: dark)').matches;
  Chart.defaults.color = dark ? '#9aa6c2' : '#667085';
  Chart.defaults.borderColor = dark ? '#2a3558' : '#e4e8f0';
  Chart.defaults.font.family = 'Inter, system-ui, sans-serif';
  config.options = Object.assign({ responsive: true, maintainAspectRatio: false }, config.options || {});
  _charts[id] = new Chart(canvas, config);
  return _charts[id];
}
const lineOpts = (extra = {}) => Object.assign({
  interaction: { mode: 'index', intersect: false },
  scales: { x: { ticks: { maxTicksLimit: 10, maxRotation: 0 }, grid: { display: false } }, y: { ticks: { callback: v => fmt.compact(v) } } },
  plugins: { tooltip: { callbacks: { label: c => `${c.dataset.label}: ${fmt.compact(c.parsed.y)}` } } }
}, extra);

function fillSelect(sel, values, firstLabel, keepValue = true) {
  const cur = sel.value;
  sel.innerHTML = `<option value="all">${esc(firstLabel)}</option>` + values.map(v => `<option>${esc(v)}</option>`).join('');
  if (keepValue && values.map(String).includes(cur)) sel.value = cur;
}
const todayStr = () => new Date().toISOString().slice(0, 10);
function debounce(fn, ms = 250) { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); }; }
function table(cols, rows, emptyMsg = 'Nothing to show.') {
  if (!rows.length) return emptyHtml(emptyMsg);
  return `<div class="table-wrap" style="border:0"><table><thead><tr>${cols.map(c => `<th class="${c.cls || ''}">${c.h}</th>`).join('')}</tr></thead><tbody>${rows.join('')}</tbody></table></div>`;
}
