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
  try {
    const res: Response = await fetch('/api/trends');
    const data = await res.json();
    cachedTrends = data.trends || [];
    sourceEl.innerText = data.source === 'snowflake' ? 'SNOWFLAKE LIVE' : 'MEMORY CACHE';
    if (cachedTrends.length === 0) {
      container.innerHTML = '<div class="mono" style="color:var(--neutral)">NO TRENDING DATA YET</div>';
      return;
    }
    const maxCount: number = Math.max(...cachedTrends.map((t: RadarTrendItem) => t.count || 1), 1);
    container.innerHTML = cachedTrends.map((t: RadarTrendItem): string => {
      const pct: number = Math.min(Math.round((t.count / maxCount) * 100), 100);
      const deltaStr: string = t.delta !== undefined ? (t.delta >= 0 ? `+${t.delta}%` : `${t.delta}%`) : `${t.count} hits`;
      return `<div class="bar-row"><span class="mono" style="min-width:100px;">${radarEscapeHtml(t.tactic || 'UNKNOWN')}</span><div class="bar-container"><div class="bar-fill" style="width:${pct}%;"></div></div><span class="mono text-neutral">${radarEscapeHtml(deltaStr)}</span></div>`;
    }).join('');
  } catch {
    container.innerHTML = '<div class="mono text-warn">FAILED TO LOAD TRENDS</div>';
  }
}

// --- Campaigns ---

async function loadCampaigns(): Promise<void> {
  const container = document.getElementById('campaignsList') as HTMLDivElement;
  const sourceEl = document.getElementById('campaignsSource') as HTMLDivElement;
  try {
    const res: Response = await fetch('/api/campaigns');
    const data = await res.json();
    cachedCampaigns = data.campaigns || [];
    sourceEl.innerText = data.source === 'snowflake' ? 'SNOWFLAKE ACTIVE' : 'ACTIVE CAMPAIGNS';
    if (cachedCampaigns.length === 0) {
      container.innerHTML = '<div class="mono" style="color:var(--neutral)">NO CAMPAIGNS RECORDED</div>';
      return;
    }
    container.innerHTML = cachedCampaigns.map((c: RadarCampaignItem): string =>
      `<div style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid var(--grid);"><span class="mono">${radarEscapeHtml(c.campaign_id || '')}</span><span class="mono text-warn">${radarEscapeHtml(String(c.variant_count || 1))} VARIANTS</span></div>`
    ).join('');
  } catch {
    container.innerHTML = '<div class="mono text-warn">FAILED TO LOAD CAMPAIGNS</div>';
  }
}

// --- NLQ Query ---

function handleQuery(): void {
  const input = document.getElementById('queryInput') as HTMLInputElement;
  const resp = document.getElementById('queryResponse') as HTMLDivElement;
  const q: string = input.value.trim().toLowerCase();
  if (!q) { resp.style.display = 'none'; return; }
  resp.style.display = 'block';
  const matchedTrend: RadarTrendItem | undefined = cachedTrends.find((t: RadarTrendItem) => t.tactic?.toLowerCase().includes(q));
  const matchedCamp: RadarCampaignItem | undefined = cachedCampaigns.find((c: RadarCampaignItem) => c.campaign_id?.toLowerCase().includes(q) || c.primary_tactic?.toLowerCase().includes(q));
  if (matchedTrend) resp.innerText = `QUERY RESULT: Tactic ${matchedTrend.tactic} observed with ${matchedTrend.count} recorded scans.`;
  else if (matchedCamp) resp.innerText = `QUERY RESULT: Campaign ${matchedCamp.campaign_id} (${matchedCamp.primary_tactic}) has ${matchedCamp.variant_count} tracked variants.`;
  else resp.innerText = `QUERY RESULT: No direct record matching "${input.value}". Monitored tactics: ${cachedTrends.map((t: RadarTrendItem) => t.tactic).join(', ') || 'None'}.`;
}

(document.getElementById('queryBtn') as HTMLButtonElement).addEventListener('click', handleQuery);
(document.getElementById('queryInput') as HTMLInputElement).addEventListener('keydown', (e: KeyboardEvent): void => {
  if (e.key === 'Enter') handleQuery();
});

// --- Campaign Graph ---

function drawCampaignGraph(): void {
  const canvas = document.getElementById('campaignGraph') as HTMLCanvasElement;
  const ctx = canvas.getContext('2d');
  if (!ctx || !canvas.parentElement) return;
  canvas.width = canvas.parentElement.clientWidth;
  canvas.height = canvas.parentElement.clientHeight;
  const w: number = canvas.width;
  const h: number = canvas.height;
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
loadTrends();
loadCampaigns();
drawCampaignGraph();
