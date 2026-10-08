/**
 * radar.ts — Kavach radar page logic.
 */

// --- Type Definitions ---

interface RadarTrendItem {
  tactic: string;
  count: number;
  delta?: number;
  is_demo?: boolean;
}

interface RadarCampaignItem {
  campaign_id: string;
  primary_tactic: string;
  variant_count: number;
  first_seen?: string;
  is_demo?: boolean;
}

// --- State ---

let cachedTrends: RadarTrendItem[] = [];
let cachedCampaigns: RadarCampaignItem[] = [];

// --- Utilities ---

function radarEscapeHtml(str: string): string {
  const div: HTMLDivElement = document.createElement('div');
  div.appendChild(document.createTextNode(str));
  return div.innerHTML;
}

// --- Trends ---

async function loadTrends(): Promise<void> {
  const container = document.getElementById('trendsList') as HTMLDivElement;
  const sourceEl = document.getElementById('trendsSource') as HTMLDivElement;
  if (!container || !sourceEl) return;

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 10000);

  try {
    const res: Response = await fetch('/api/trends', { signal: controller.signal });
    clearTimeout(timeoutId);
    if (!res.ok) throw new Error(`HTTP error ${res.status}`);
    const data = await res.json();
    cachedTrends = data.trends || [];
    sourceEl.innerText = data.source === 'snowflake' ? 'SNOWFLAKE LIVE' : 'MEMORY CACHE';

    if (cachedTrends.length === 0) {
      container.innerHTML = '<div class="mono" style="color:var(--grey)">No scans yet</div>';
      return;
    }

    const maxCount: number = Math.max(...cachedTrends.map((t: RadarTrendItem) => t.count || 1), 1);
    container.innerHTML = cachedTrends.map((t: RadarTrendItem): string => {
      const pct: number = Math.min(Math.round((t.count / maxCount) * 100), 100);
      const deltaStr: string = t.delta !== undefined ? (t.delta >= 0 ? `+${t.delta}%` : `${t.delta}%`) : `${t.count} hits`;
      return `<div class="bar-row"><span class="mono" style="min-width:100px;">${radarEscapeHtml(t.tactic || 'UNKNOWN')}</span><div class="bar-container"><div class="bar-fill" style="width:${pct}%;"></div></div><span class="mono text-neutral">${radarEscapeHtml(deltaStr)}</span></div>`;
    }).join('');
  } catch (err) {
    clearTimeout(timeoutId);
    sourceEl.innerText = 'OFFLINE';
    container.innerHTML = '<div class="mono text-warn">No scans yet (offline / error)</div>';
  }
}

// --- Campaigns ---

async function loadCampaigns(): Promise<void> {
  const container = document.getElementById('campaignsList') as HTMLDivElement;
  const sourceEl = document.getElementById('campaignsSource') as HTMLDivElement;
  if (!container || !sourceEl) return;

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 10000);

  try {
    const res: Response = await fetch('/api/campaigns', { signal: controller.signal });
    clearTimeout(timeoutId);
    if (!res.ok) throw new Error(`HTTP error ${res.status}`);
    const data = await res.json();
    cachedCampaigns = data.campaigns || [];
    sourceEl.innerText = data.source === 'snowflake' ? 'SNOWFLAKE ACTIVE' : 'ACTIVE CAMPAIGNS';

    if (cachedCampaigns.length === 0) {
      container.innerHTML = '<div class="mono" style="color:var(--grey)">No campaigns yet</div>';
      return;
    }

    container.innerHTML = cachedCampaigns.map((c: RadarCampaignItem): string =>
      `<div style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid var(--grid);"><span class="mono">${radarEscapeHtml(c.campaign_id || '')}</span><span class="mono text-warn">${radarEscapeHtml(String(c.variant_count || 1))} VARIANTS</span></div>`
    ).join('');
  } catch (err) {
    clearTimeout(timeoutId);
    sourceEl.innerText = 'OFFLINE';
    container.innerHTML = '<div class="mono text-warn">No campaigns yet (offline / error)</div>';
  }
}

// --- Local Filter Query ---

function handleQuery(): void {
  const input = document.getElementById('queryInput') as HTMLInputElement;
  const resp = document.getElementById('queryResponse') as HTMLDivElement;
  if (!input || !resp) return;

  const q: string = input.value.trim().toLowerCase();
  if (!q) {
    resp.style.display = 'none';
    return;
  }
  resp.style.display = 'block';
  const matchedTrend: RadarTrendItem | undefined = cachedTrends.find((t: RadarTrendItem) => t.tactic?.toLowerCase().includes(q));
  const matchedCamp: RadarCampaignItem | undefined = cachedCampaigns.find((c: RadarCampaignItem) => c.campaign_id?.toLowerCase().includes(q) || c.primary_tactic?.toLowerCase().includes(q));

  if (matchedTrend) {
    resp.innerText = `FILTER MATCH: Tactic ${matchedTrend.tactic} observed with ${matchedTrend.count} recorded scans.`;
  } else if (matchedCamp) {
    resp.innerText = `FILTER MATCH: Campaign ${matchedCamp.campaign_id} (${matchedCamp.primary_tactic}) has ${matchedCamp.variant_count} tracked variants.`;
  } else {
    resp.innerText = `FILTER MATCH: No direct match for "${input.value}". Monitored tactics: ${cachedTrends.map((t: RadarTrendItem) => t.tactic).join(', ') || 'None'}.`;
  }
}

// --- Campaign Graph ---

function drawCampaignGraph(): void {
  const canvas = document.getElementById('campaignGraph') as HTMLCanvasElement;
  if (!canvas || !canvas.parentElement) return;
  const ctx = canvas.getContext('2d');
  if (!ctx) return;

  const w: number = (canvas.width = canvas.parentElement.clientWidth || 400);
  const h: number = (canvas.height = canvas.parentElement.clientHeight || 400);
  ctx.fillStyle = 'rgba(17,16,16,0.16)';
  for (let i = 0; i < 30; i++) {
    ctx.beginPath();
    ctx.arc(Math.random() * w, Math.random() * h, Math.random() * 15 + 5, 0, Math.PI * 2);
    ctx.fill();
    if (i > 0) {
      ctx.beginPath();
      ctx.moveTo(Math.random() * w, Math.random() * h);
      ctx.lineTo(Math.random() * w, Math.random() * h);
      ctx.lineWidth = 1;
      ctx.strokeStyle = 'rgba(17,16,16,0.08)';
      ctx.stroke();
    }
  }
}

// --- Init ---

function initRadar(): void {
  loadTrends();
  loadCampaigns();
  drawCampaignGraph();

  const queryBtn = document.getElementById('queryBtn') as HTMLButtonElement;
  if (queryBtn) queryBtn.addEventListener('click', handleQuery);

  const queryInput = document.getElementById('queryInput') as HTMLInputElement;
  if (queryInput) {
    queryInput.addEventListener('keydown', (e: KeyboardEvent): void => {
      if (e.key === 'Enter') handleQuery();
    });
  }
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initRadar);
} else {
  initRadar();
}
