Pages.forecast = (() => {
  let meta = null;
  const FRIENDLY = { sd_mean: 'Store+department sales level', is_holiday: 'Holiday week', holiday_code: 'Which holiday', month: 'Month', week_of_year: 'Week of year',
    quarter: 'Quarter', season_code: 'Season', store_id: 'Store', department: 'Department' };
  const params = () => new URLSearchParams({ store: $('#fc-store').value, department: $('#fc-dept').value, start: $('#fc-start').value, end: $('#fc-end').value, weeks: $('#fc-weeks').value });

  async function load() {
    if (!meta) {
      $('#fc-status').innerHTML = loadingHtml('Reading CSV files…');
      try { meta = await api('/forecast/meta'); } catch (e) {
        $('#fc-status').innerHTML = notice('bad', `<b>Dataset problem:</b> ${esc(e.message)}<br>Put <code>sales.csv</code> and <code>features.csv</code> in the <code>data</code> folder and reload.`, 'x-octagon'); return;
      }
      fillSelect($('#fc-store'), meta.stores.map(s => s), 'All stores'); fillSelect($('#fc-dept'), meta.departments, 'All departments');
      $('#fc-start').min = $('#fc-end').min = meta.date_min; $('#fc-start').max = $('#fc-end').max = meta.date_max;
    }
    renderStatus(); refresh();
  }
  function renderStatus() {
    const m = meta.model, rep = meta.dataset_report;
    let h = '';
    if (!m) h += notice('warn', '<b>No model has been trained yet.</b> Historical analysis below is real data, but <b>no predictions are shown</b> until you click “Train / retrain model”. (Training takes about 15–60 seconds.)', 'cpu');
    else h += notice('ok', `<b>Model: ${esc(m.model_name)}</b> · trained ${esc(m.trained_at.replace('T', ' '))} on ${fmt.n(m.train_rows)} rows · tested on the last ${m.test_weeks} weeks (${m.test_period[0]} → ${m.test_period[1]}) that it never saw during training.`, 'check-circle');
    if (rep.warnings.length) h += notice('info', rep.warnings.map(esc).join('<br>'));
    $('#fc-status').innerHTML = h;
  }
  async function refresh() {
    const p = params();
    $('#fc-cards').innerHTML = loadingHtml();
    try {
      const [s, a] = await Promise.all([api('/forecast/series?' + p), api('/forecast/analysis?' + p)]);
      if (s.error) { $('#fc-cards').innerHTML = notice('warn', esc(s.error)); return; }
      renderSeries(s); renderAnalysis(a); renderModel();
    } catch (e) {
      $('#fc-cards').innerHTML = notice('bad', esc(e.message), 'x-octagon');
    }
  }
  function renderSeries(s) {
    const hm = s.holdout && s.holdout.metrics;
    $('#fc-scope1').textContent = s.scope;
    $('#fc-cards').innerHTML =
      statCard('calendar3', 'blue', fmt.n(s.actual.length), 'Weeks of history', s.scope) +
      statCard('graph-up-arrow', 'green', s.future_total != null ? fmt.compact(s.future_total) : '–', `Predicted next ${$('#fc-weeks').value} weeks`, s.model_ready ? 'model forecast' : 'train model first') +
      statCard('bullseye', 'amber', hm && hm.mape != null ? hm.mape.toFixed(1) + '%' : '–', 'Test MAPE (this selection)', hm ? `WAPE ${hm.wape.toFixed(1)}%` : '') +
      statCard('percent', 'grey', hm && hm.r2 != null ? hm.r2.toFixed(3) : '–', 'Test R² (this selection)', hm ? `${s.holdout.weeks} test weeks` : '');
    makeChart('ch-fc-hist', { type: 'line', data: { labels: s.actual.map(x => x.date), datasets: [{ label: 'Actual weekly sales', data: s.actual.map(x => x.value), borderColor: '#2f5bea', backgroundColor: '#2f5bea1f', fill: true, tension: .2, pointRadius: 0 }] }, options: lineOpts() });

    if (!s.model_ready) {
      makeChart('ch-fc-pred', { type: 'line', data: { labels: [], datasets: [] }, options: {} });
      $('#fc-pred-note').innerHTML = 'No predictions yet — train the model first. Nothing is simulated or pre-filled.';
      $('#fc-future').innerHTML = `<tr><td colspan="4">${emptyHtml('Train the model to see predicted demand.')}</td></tr>`; return;
    }
    const tail = s.actual.slice(-52), hp = (s.holdout && s.holdout.points) || [], fu = s.future || [];
    const labels = [...new Set([...tail.map(x => x.date), ...hp.map(x => x.date), ...fu.map(x => x.date)])].sort();
    const map = (arr, k) => { const m = {}; arr.forEach(x => m[x.date] = x[k] ?? x.value); return labels.map(l => m[l] ?? null); };
    makeChart('ch-fc-pred', { type: 'line', data: { labels, datasets: [
      { label: 'Actual', data: map(tail, 'value'), borderColor: '#2f5bea', tension: .2, pointRadius: 0 },
      { label: 'Model on test weeks (unseen data)', data: map(hp, 'predicted'), borderColor: '#f59e0b', borderDash: [5, 4], tension: .2, pointRadius: 2 },
      { label: 'Future forecast', data: map(fu, 'predicted'), borderColor: '#12a37f', tension: .2, pointRadius: 3, borderWidth: 2.5 },
      { label: '_upper', data: map(fu, 'upper'), borderColor: 'transparent', pointRadius: 0, backgroundColor: 'transparent' },
      { label: '_lower', data: map(fu, 'lower'), borderColor: 'transparent', pointRadius: 0, backgroundColor: 'rgba(18,163,127,.18)', fill: '-1' }] },
      options: lineOpts({ plugins: { legend: { labels: { filter: i => !i.text.startsWith('_') } }, tooltip: { filter: i => !i.dataset.label.startsWith('_'), callbacks: { label: c => `${c.dataset.label}: ${fmt.compact(c.parsed.y)}` } } } }) });
    $('#fc-pred-note').textContent = s.interval_note;
    $('#fc-future').innerHTML = fu.map(f => `<tr><td>${fmt.date(f.date)}</td><td class="num"><b>${fmt.n(Math.round(f.predicted))}</b></td><td class="num">${fmt.compact(f.lower)} – ${fmt.compact(f.upper)}</td>
      <td>${f.holiday ? badge(f.holiday + ' (inferred)', 'info') : '–'}</td></tr>`).join('');
  }
  function renderAnalysis(a) {
    const g = a.yoy_growth.map(y => statCard(y.pct >= 0 ? 'arrow-up-right' : 'arrow-down-right', y.pct >= 0 ? 'green' : 'red', fmt.pct(y.pct), `Avg weekly sales ${y.from} → ${y.to}`)).join('');
    const rt = a.recent_trend ? statCard(a.recent_trend.pct >= 0 ? 'arrow-up-right' : 'arrow-down-right', a.recent_trend.pct >= 0 ? 'green' : 'red', fmt.pct(a.recent_trend.pct), 'Last 13 vs previous 13 weeks', 'includes holiday season') : '';
    $('#fc-growth').innerHTML = g + rt + statCard('cash-stack', 'blue', fmt.compact(a.avg_weekly_sales), 'Avg weekly sales', a.scope) +
      (a.recent_trend ? `<div class="notice warn" style="grid-column:1/-1;margin:0"><i class="bi bi-info-circle"></i><div>${esc(a.recent_trend.note)} Year-over-year growth is essentially flat in this data.</div></div>` : '');
    makeChart('ch-monthly', { type: 'bar', data: { labels: a.monthly_trend.map(x => x.month), datasets: [{ label: 'Total sales', data: a.monthly_trend.map(x => x.total), backgroundColor: '#2f5bea', borderRadius: 4 }] }, options: lineOpts({ plugins: { legend: { display: false }, tooltip: { callbacks: { label: c => fmt.compact(c.parsed.y) } } } }) });
    makeChart('ch-weekly', { type: 'line', data: { labels: a.week_of_year.map(x => 'W' + x.week), datasets: [{ label: 'Avg weekly sales', data: a.week_of_year.map(x => x.avg_weekly), borderColor: '#8b5cf6', backgroundColor: '#8b5cf61f', fill: true, tension: .25, pointRadius: 0 }] }, options: lineOpts({ plugins: { legend: { display: false } } }) });
    const h = a.holiday;
    makeChart('ch-holiday', { type: 'bar', data: { labels: ['Holiday weeks', 'Non-holiday weeks'], datasets: [{ data: [h.holiday_avg, h.non_holiday_avg], backgroundColor: ['#f59e0b', '#2f5bea'], borderRadius: 6 }] }, options: { plugins: { legend: { display: false }, tooltip: { callbacks: { label: c => fmt.compact(c.parsed.y) } } }, scales: { y: { ticks: { callback: v => fmt.compact(v) } } } } });
    $('#fc-holiday-table').innerHTML = (h.uplift_pct != null ? `<p style="margin-top:0"><b>${fmt.pct(h.uplift_pct)}</b> average uplift in holiday weeks (${h.holiday_weeks} holiday vs ${h.non_holiday_weeks} normal weeks).</p>` : '') +
      table([{ h: 'Holiday' }, { h: 'Weeks', cls: 'num' }, { h: 'Avg weekly sales', cls: 'num' }, { h: 'vs normal week', cls: 'num' }],
        a.holiday_by_name.map(x => `<tr><td>${esc(x.name)}</td><td class="num">${x.weeks}</td><td class="num">${fmt.compact(x.avg_weekly)}</td><td class="num"><b>${fmt.pct(x.vs_normal_pct)}</b></td></tr>`), 'No holiday weeks in this range.');
    makeChart('ch-month-index', { type: 'bar', data: { labels: a.month_of_year.map(x => x.month), datasets: [{ label: 'Seasonality index', data: a.month_of_year.map(x => x.index), backgroundColor: a.month_of_year.map(x => x.index >= 100 ? '#12a37f' : '#f59e0b'), borderRadius: 4 }] }, options: { plugins: { legend: { display: false } }, scales: { y: { suggestedMin: 60 } } } });
    const idx = arr => ({ type: 'bar', data: { labels: arr.map(x => x.season), datasets: [{ data: arr.map(x => x.index), backgroundColor: PALETTE, borderRadius: 6 }] }, options: { plugins: { legend: { display: false } }, scales: { y: { suggestedMin: 60 } } } });
    makeChart('ch-ds-season', idx(a.dataset_seasons)); makeChart('ch-in-season', idx(a.indian_seasons_assumed));
    $('#fc-insights').innerHTML = a.insights.map(i => `<li class="${i.kind}"><span class="tag">${i.kind === 'data' ? '✔ Dataset-supported' : '⚠ Assumption'}</span>${esc(i.text)}</li>`).join('');
  }
  function renderModel() {
    const m = meta.model, rep = meta.dataset_report;
    let h = `<div class="card mb"><h3>Data used</h3><dl class="kv"><dt>Files</dt><dd>${rep.files_used.join(', ')}</dd><dt>Rows</dt><dd>${fmt.n(rep.rows)} (${rep.stores} stores × ${rep.departments} departments × ${rep.weeks} weeks)</dd><dt>Period</dt><dd>${rep.date_min} → ${rep.date_max}</dd></dl></div>`;
    if (!m) { $('#fc-model').innerHTML = h + notice('warn', 'Train the model to see accuracy metrics.'); return; }
    const names = Object.keys(m.results), f = x => x == null ? '–' : Math.round(x).toLocaleString();
    const row = n => { const r = m.results[n], a = r.row_level, t = r.weekly_total; return `<tr><td><b>${esc(n)}</b> ${n === m.model_name ? badge('chosen', 'ok') : n.startsWith('Baseline') ? badge('baseline', 'grey') : ''}</td>
      <td class="num">${f(a.mae)}</td><td class="num">${f(a.rmse)}</td><td class="num">${a.mape.toFixed(1)}%</td><td class="num">${a.r2.toFixed(3)}</td>
      <td class="num">${t.mape.toFixed(2)}%</td><td class="num">${t.r2.toFixed(3)}</td></tr>`; };
    const best = m.results[m.model_name], base = m.results['Baseline: store+dept average'];
    const gain = (1 - best.row_level.mae / base.row_level.mae) * 100, ab = m.ablation, d = (1 - ab.calendar_plus_external.mae / ab.calendar_only.mae) * 100;
    const maxI = Math.max(...m.importance.map(i => i.importance), 1);
    h += `<div class="card mb"><h3>Evaluation on unseen test weeks <span class="hint">time-based split: train on the past, test on the final ${m.test_weeks} weeks</span></h3>
      <div class="table-wrap" style="border:0"><table><thead><tr><th>Model</th><th class="num">MAE</th><th class="num">RMSE</th><th class="num">MAPE</th><th class="num">R²</th><th class="num">Weekly-total MAPE</th><th class="num">Weekly-total R²</th></tr></thead><tbody>${names.map(row).join('')}</tbody></table></div>
      <p class="small muted">Left four columns: accuracy for each individual store-department-week. Last two: accuracy after adding all stores/departments into one weekly total.</p></div>
      <div class="grid g2 mb"><div class="card"><h3>How to read this</h3><ul class="insights">
        <li>${esc(m.model_name)} cuts the per store-dept-week MAE by <b>${gain.toFixed(1)}%</b> versus the “store+department average” baseline.</li>
        <li class="${best.row_level.r2 < .7 ? 'assumption' : ''}">Individual store-department weeks are <b>noisy</b> (MAPE ${best.row_level.mape.toFixed(0)}%, R² ${best.row_level.r2.toFixed(2)}): a single week for one department can miss by a lot. Treat those forecasts as a rough level, not an exact number.</li>
        <li>Adding many store-departments together averages out the noise: the weekly total is predicted with MAPE ${best.weekly_total.mape.toFixed(1)}% (R² ${best.weekly_total.r2.toFixed(3)}). Use all-store views for planning.</li>
        <li>Weather, fuel price, CPI, unemployment and markdowns were tested: MAE changed by ${d.toFixed(2)}% — ${Math.abs(d) < 1 ? '<b>no meaningful gain</b>, and these values are unknown for future weeks anyway, so the production model uses only calendar, holiday, store and department information.' : 'see notes.'}</li>
        <li>Future holiday weeks are <b>inferred</b> from when holidays fell in 2022–2024.</li></ul></div>
        <div class="card"><h3>What drives the forecast <span class="hint">permutation importance</span></h3>${m.importance.slice(0, 6).map(i => `<div class="small" style="display:flex;gap:8px;align-items:center;margin-bottom:6px"><span style="width:170px">${esc(FRIENDLY[i.feature] || i.feature)}</span><div class="bar" style="flex:1"><i style="width:${Math.max(1, i.importance / maxI * 100)}%"></i></div></div>`).join('')}</div></div>`;
    $('#fc-model').innerHTML = h;
  }
  function init() {
    $('#fc-apply').onclick = refresh;
    ['#fc-store', '#fc-dept', '#fc-weeks'].forEach(s => $(s).onchange = refresh);
    $$('#fc-tabs button').forEach(b => b.onclick = () => {
      $$('#fc-tabs button').forEach(x => x.classList.toggle('active', x === b));
      $$('.tabpane').forEach(p => p.classList.toggle('active', p.id === b.dataset.tab));
      window.dispatchEvent(new Event('resize'));
    });
    $('#fc-train').onclick = async () => {
      const btn = $('#fc-train'); btn.disabled = true;
      $('#fc-status').innerHTML = loadingHtml('Training and evaluating models on the real CSV data… (15–60 seconds)');
      try { const r = await api('/forecast/train', { method: 'POST' }); toast(r.message, 'ok'); meta = null; await load(); App.refreshBadge(); }
      catch (e) { $('#fc-status').innerHTML = notice('bad', esc(e.message), 'x-octagon'); }
      btn.disabled = false;
    };
  }
  return { load, init };
})();
