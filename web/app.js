/**
 * Anchor — Web Demo Application
 *
 * Connects to the model server at localhost:8000.
 * Runs the demo and renders two agent traces + drift-score chart.
 */

const API_BASE = window.location.origin;
const THRESHOLD = 0.5;

// ─── DOM refs ───
const serverStatus   = document.getElementById('server-status');
const statusDot      = serverStatus.querySelector('.status-dot');
const statusText     = serverStatus.querySelector('.status-text');
const runDemoBtn     = document.getElementById('run-demo-btn');
const demoResults    = document.getElementById('demo-results');
const demoTaskText   = document.getElementById('demo-task-text');
const vanillaTurns   = document.getElementById('vanilla-turns');
const anchorTurns    = document.getElementById('anchor-turns');
const vanillaVerdict = document.getElementById('vanilla-verdict');
const anchorVerdict  = document.getElementById('anchor-verdict');
const driftCanvas    = document.getElementById('drift-canvas');
const scoreBtn       = document.getElementById('score-btn');
const scoreResult    = document.getElementById('score-result');
const pgTask         = document.getElementById('pg-task');
const pgOutput       = document.getElementById('pg-output');


// ─── Server Health Check ───
async function checkHealth() {
  try {
    const res = await fetch(`${API_BASE}/health`);
    const data = await res.json();

    serverStatus.className = 'status-badge online';
    statusText.textContent = `${data.mode} mode`;
    runDemoBtn.disabled = false;
    scoreBtn.disabled = false;

    return true;
  } catch {
    serverStatus.className = 'status-badge offline';
    statusText.textContent = 'Server offline';
    runDemoBtn.disabled = true;
    scoreBtn.disabled = true;
    return false;
  }
}


// ─── Render Agent Turns ───
function renderTurns(turns, container, variant) {
  container.innerHTML = '';

  turns.forEach(turn => {
    const div = document.createElement('div');
    div.className = 'turn';

    const scoreDisplay = (() => {
      if (turn.drift_score === null || turn.drift_score === undefined) {
        if (variant === 'vanilla') return '<span class="score-na">no check</span>';
        return '<span class="score-na">—</span>';
      }
      const cls = turn.drift_score >= THRESHOLD ? 'score-danger' : 'score-safe';
      return `<span class="turn-score ${cls}">${turn.drift_score.toFixed(4)}</span>`;
    })();

    const blockedTag = turn.blocked
      ? '<div class="turn-blocked">⛔ BLOCKED</div>'
      : '';

    const args = Object.entries(turn.args)
      .map(([k, v]) => `${k}: ${typeof v === 'string' ? v.substring(0, 60) : v}`)
      .join(', ');

    div.innerHTML = `
      <span class="turn-number">${turn.turn}</span>
      <div class="turn-content">
        <div class="turn-action">${turn.action}()</div>
        <div class="turn-detail">${args}</div>
        ${blockedTag}
      </div>
      ${scoreDisplay}
    `;

    container.appendChild(div);
  });
}


// ─── Render Verdict ───
function renderVerdict(result, container) {
  if (result.secret_leaked) {
    container.className = 'agent-verdict verdict-leaked';
    container.textContent = '⚠ SECRET LEAKED — API key exfiltrated';
  } else if (result.blocked_action) {
    container.className = 'agent-verdict verdict-safe';
    container.textContent = `✓ Secret safe — ${result.blocked_action}() blocked by Anchor`;
  } else {
    container.className = 'agent-verdict verdict-safe';
    container.textContent = '✓ Secret safe';
  }
}


// ─── Drift Score Chart ───
function drawDriftChart(vanillaResult, anchorResult) {
  const canvas = driftCanvas;
  const dpr = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();

  canvas.width = rect.width * dpr;
  canvas.height = 200 * dpr;

  const ctx = canvas.getContext('2d');
  ctx.scale(dpr, dpr);

  const W = rect.width;
  const H = 200;
  const pad = { top: 20, right: 20, bottom: 36, left: 50 };
  const plotW = W - pad.left - pad.right;
  const plotH = H - pad.top - pad.bottom;

  // Gather all scored turns from anchor agent
  const scored = anchorResult.turns
    .filter(t => t.drift_score !== null && t.drift_score !== undefined);

  if (scored.length === 0) return;

  // Background
  ctx.fillStyle = '#0D1117';
  ctx.fillRect(0, 0, W, H);

  // Grid
  ctx.strokeStyle = '#1C2128';
  ctx.lineWidth = 1;
  for (let y = 0; y <= 1; y += 0.25) {
    const py = pad.top + plotH * (1 - y);
    ctx.beginPath();
    ctx.moveTo(pad.left, py);
    ctx.lineTo(pad.left + plotW, py);
    ctx.stroke();

    ctx.fillStyle = '#484F58';
    ctx.font = '11px "IBM Plex Mono", monospace';
    ctx.textAlign = 'right';
    ctx.fillText(y.toFixed(2), pad.left - 8, py + 4);
  }

  // Threshold line
  const threshY = pad.top + plotH * (1 - THRESHOLD);
  ctx.strokeStyle = '#D29922';
  ctx.lineWidth = 1.5;
  ctx.setLineDash([6, 4]);
  ctx.beginPath();
  ctx.moveTo(pad.left, threshY);
  ctx.lineTo(pad.left + plotW, threshY);
  ctx.stroke();
  ctx.setLineDash([]);

  ctx.fillStyle = '#D29922';
  ctx.font = '10px "IBM Plex Mono", monospace';
  ctx.textAlign = 'left';
  ctx.fillText('threshold', pad.left + plotW + 4, threshY + 3);

  // Points and lines
  const xStep = scored.length > 1 ? plotW / (scored.length - 1) : plotW / 2;

  // Line
  ctx.strokeStyle = '#58A6FF';
  ctx.lineWidth = 2;
  ctx.beginPath();
  scored.forEach((t, i) => {
    const x = pad.left + (scored.length > 1 ? i * xStep : plotW / 2);
    const y = pad.top + plotH * (1 - t.drift_score);
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();

  // Points
  scored.forEach((t, i) => {
    const x = pad.left + (scored.length > 1 ? i * xStep : plotW / 2);
    const y = pad.top + plotH * (1 - t.drift_score);
    const safe = t.drift_score < THRESHOLD;

    // Glow
    const gradient = ctx.createRadialGradient(x, y, 0, x, y, 16);
    gradient.addColorStop(0, safe ? 'rgba(63,185,80,0.3)' : 'rgba(248,81,73,0.3)');
    gradient.addColorStop(1, 'transparent');
    ctx.fillStyle = gradient;
    ctx.beginPath();
    ctx.arc(x, y, 16, 0, Math.PI * 2);
    ctx.fill();

    // Dot
    ctx.fillStyle = safe ? '#3FB950' : '#F85149';
    ctx.beginPath();
    ctx.arc(x, y, 5, 0, Math.PI * 2);
    ctx.fill();

    ctx.strokeStyle = safe ? '#3FB950' : '#F85149';
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.arc(x, y, 5, 0, Math.PI * 2);
    ctx.stroke();

    // Label
    ctx.fillStyle = '#E6EDF3';
    ctx.font = '11px "IBM Plex Mono", monospace';
    ctx.textAlign = 'center';
    ctx.fillText(t.action, x, H - pad.bottom + 16);
    ctx.fillStyle = safe ? '#3FB950' : '#F85149';
    ctx.fillText(t.drift_score.toFixed(3), x, H - pad.bottom + 28);
  });
}


// ─── Run Demo ───
async function runDemo() {
  runDemoBtn.classList.add('loading');
  runDemoBtn.disabled = true;

  try {
    const res = await fetch(`${API_BASE}/demo`, { method: 'POST' });
    const data = await res.json();

    // Show results
    demoResults.classList.remove('hidden');

    // Task
    demoTaskText.textContent = `Task: "${data.task}"`;

    // Render turns
    renderTurns(data.vanilla.turns, vanillaTurns, 'vanilla');
    renderTurns(data.anchor.turns, anchorTurns, 'anchor');

    // Verdicts
    renderVerdict(data.vanilla, vanillaVerdict);
    renderVerdict(data.anchor, anchorVerdict);

    // Chart
    requestAnimationFrame(() => drawDriftChart(data.vanilla, data.anchor));

    // Scroll to results
    demoResults.scrollIntoView({ behavior: 'smooth', block: 'start' });

  } catch (err) {
    console.error('Demo failed:', err);
    alert('Demo failed — is the server running?');
  } finally {
    runDemoBtn.classList.remove('loading');
    runDemoBtn.disabled = false;
  }
}


// ─── Score Playground ───
async function scoreOutput() {
  const task = pgTask.value.trim();
  const output = pgOutput.value.trim();
  if (!task || !output) return;

  scoreBtn.disabled = true;

  try {
    const res = await fetch(`${API_BASE}/score`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ task, tool_output: output }),
    });
    const data = await res.json();

    // Show result
    scoreResult.classList.remove('hidden');

    const fill = document.getElementById('meter-fill');
    const thresh = document.getElementById('meter-threshold');
    const value = document.getElementById('score-value');
    const verdict = document.getElementById('score-verdict-text');
    const latency = document.getElementById('score-latency');

    fill.style.width = `${data.drift_score * 100}%`;
    const safe = data.drift_score < THRESHOLD;
    fill.style.background = safe
      ? 'linear-gradient(90deg, #1a4d2e, #3FB950)'
      : 'linear-gradient(90deg, #6e201a, #F85149)';

    thresh.style.left = `${THRESHOLD * 100}%`;

    value.textContent = data.drift_score.toFixed(4);
    value.style.color = safe ? '#3FB950' : '#F85149';

    verdict.textContent = safe ? 'SAFE — drift below threshold' : 'DRIFT DETECTED — would be blocked';
    verdict.style.background = safe ? 'rgba(63,185,80,0.15)' : 'rgba(248,81,73,0.15)';
    verdict.style.color = safe ? '#3FB950' : '#F85149';

    latency.textContent = `${data.latency_ms}ms · layer ${data.layer} · ${data.mode}`;

  } catch (err) {
    console.error('Score failed:', err);
  } finally {
    scoreBtn.disabled = false;
  }
}


// ─── Event Listeners ───
runDemoBtn.addEventListener('click', runDemo);
scoreBtn.addEventListener('click', scoreOutput);

// Handle window resize for drift chart redraw
let resizeTimeout;
window.addEventListener('resize', () => {
  clearTimeout(resizeTimeout);
  resizeTimeout = setTimeout(() => {
    // If chart is visible, redraw (we'd need to store data)
  }, 250);
});

// ─── Init ───
checkHealth();
setInterval(checkHealth, 10000);
