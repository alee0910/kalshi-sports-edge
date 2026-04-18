// Dashboard client. Reads static JSON from /data written by the scanner.

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

function fmtPct(p, d = 3) { return (p * 100).toFixed(1) + '%'; }
function cls(cents) {
  if (cents > 100) return 'ev-positive';
  if (cents > 0) return 'ev-marginal';
  return 'ev-negative';
}

// -----------------------------------------------------------------------
// Tabs
// -----------------------------------------------------------------------
document.addEventListener('click', (e) => {
  const tab = e.target.closest('.tab-btn');
  if (!tab) return;
  $$('.tab-btn').forEach(b => b.classList.toggle('active', b === tab));
  const name = tab.dataset.tab;
  $$('.tab-panel').forEach(p => p.classList.toggle('active', p.id === `tab-${name}`));
});

// -----------------------------------------------------------------------
// Render
// -----------------------------------------------------------------------
function renderCandidates(tableSel, rows, {shadow=false} = {}) {
  const tb = $(tableSel + ' tbody');
  tb.innerHTML = '';
  if (!rows || rows.length === 0) {
    tb.innerHTML = `<tr><td colspan="9" style="color:#9aa3b2">No candidates at current threshold.</td></tr>`;
    return;
  }
  for (const c of rows) {
    const tr = document.createElement('tr');
    if (shadow) tr.classList.add('shadow-row');
    tr.innerHTML = `
      <td><code>${c.strategy_id}</code> ${c.strategy_name}</td>
      <td>${c.sport.toUpperCase()}</td>
      <td>${c.event_label}</td>
      <td>${c.suggested_side.toUpperCase()} (${c.suggested_role})</td>
      <td>${(c.model_p_yes*100).toFixed(1)}¢</td>
      <td>${(c.market_yes_ask*100).toFixed(1)}¢</td>
      <td>${c.edge_pp.toFixed(2)}</td>
      <td class="${cls(c.net_edge_after_fee_cents)}">${c.net_edge_after_fee_cents}</td>
      <td>${c.suggested_contracts}</td>`;
    tb.appendChild(tr);
  }
}

function renderSkipped(rows) {
  const tb = $('#skipped-table tbody');
  tb.innerHTML = '';
  if (!rows || rows.length === 0) {
    tb.innerHTML = `<tr><td colspan="2" style="color:#9aa3b2">None.</td></tr>`;
    return;
  }
  for (const s of rows) {
    const tr = document.createElement('tr');
    tr.innerHTML = `<td>${s.ticker}</td><td>${s.reason}</td>`;
    tb.appendChild(tr);
  }
}

function renderBacktest(rows) {
  const tb = $('#backtest-table tbody');
  tb.innerHTML = '';
  if (!rows) { tb.innerHTML = `<tr><td colspan="8">Loading…</td></tr>`; return; }
  for (const r of rows) {
    const ci = r.ci95_mean_return_pct || [0,0];
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td><code>${r.strategy_id}</code></td>
      <td>${r.n_trades}</td>
      <td>${(r.hit_rate*100).toFixed(1)}%</td>
      <td class="${r.avg_return_per_trade_pct > 0 ? 'ev-positive' : 'ev-negative'}">${r.avg_return_per_trade_pct.toFixed(2)}%</td>
      <td>${r.sharpe_annualized.toFixed(2)}</td>
      <td>${r.profit_factor.toFixed(2)}</td>
      <td>${(r.max_drawdown_pct*100).toFixed(1)}%</td>
      <td>${ci[0].toFixed(2)}% … ${ci[1].toFixed(2)}%</td>`;
    tb.appendChild(tr);
  }
}

function renderCalibration(data) {
  $('#cal-meta').textContent =
    `Window: ${data?.window_days || 30}d · last refresh ${data?.refreshed_at || '—'} · ${data?.n_scans_settled || 0} settled scans`;
  const tb = $('#cal-table tbody');
  tb.innerHTML = '';
  if (!data || !data.per_strategy) {
    tb.innerHTML = `<tr><td colspan="7" style="color:#9aa3b2">No calibration data yet. The daily calibration job emits to <code>dashboard/data/calibration.json</code>.</td></tr>`;
    return;
  }
  for (const [sid, s] of Object.entries(data.per_strategy)) {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td><code>${sid}</code></td>
      <td>${s.n_scans}</td>
      <td>${s.n_settled}</td>
      <td>${(s.avg_model_p*100).toFixed(1)}%</td>
      <td>${(s.realized_rate*100).toFixed(1)}%</td>
      <td>${s.log_loss.toFixed(3)}</td>
      <td>${s.brier.toFixed(3)}</td>`;
    tb.appendChild(tr);
  }
}

// -----------------------------------------------------------------------
// Fetchers
// -----------------------------------------------------------------------
async function load(url) {
  try {
    const r = await fetch(url + '?t=' + Date.now());
    if (!r.ok) throw new Error(r.status);
    return await r.json();
  } catch (e) {
    console.warn('load failed', url, e);
    return null;
  }
}

async function bootstrap() {
  const latest = await load('data/latest.json');
  if (latest) {
    $('#live-meta').textContent =
      `Last scan ${latest.scanned_at} · ${latest.n_markets_scanned} markets · ${latest.n_live_candidates} live candidates, ${latest.n_shadow_candidates} shadow.`;
    $('#last-scan').textContent = latest.scanned_at || '—';
    $('#scanner-version').textContent = latest.version || '—';
    renderCandidates('#live-table', latest.top_live);
    renderCandidates('#shadow-table', latest.top_shadow, {shadow: true});
    renderSkipped(latest.skipped);
  } else {
    $('#live-meta').textContent = 'No scan data yet. Scanner cron publishes every ~20min.';
  }

  const bt = await load('data/backtest_summary.json');
  renderBacktest(bt);

  const cal = await load('data/calibration.json');
  renderCalibration(cal);
}

bootstrap();
