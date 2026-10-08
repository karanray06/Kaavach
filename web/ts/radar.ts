/**
 * radar.ts — Kavach radar page telemetry and threat topology logic.
 */

// --- Type Definitions ---

interface RadarTrendItem {
  tactic: string;
  count: number;
  share_pct: number;
  prev_count: number;
  change_pct: number | null;
  is_new?: boolean;
  flag?: string | null;
}

interface RadarTrendsResponse {
  source: string;
  updated_at: string;
  total_scans: number;
  ai_unavailable_count: number;
  trends: RadarTrendItem[];
}

interface RadarCampaignItem {
  campaign_id: string;
  variant_count: number;
  top_tactic?: string;
  primary_tactic?: string;
  first_seen?: string;
  last_seen?: string;
}

interface RadarCampaignsResponse {
  source: string;
  campaigns: RadarCampaignItem[];
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
  const metaEl = document.getElementById('trendsMeta') as HTMLDivElement;
  if (!container || !sourceEl) return;

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 10000);

  try {
    const res: Response = await fetch('/api/trends', { signal: controller.signal });
    clearTimeout(timeoutId);
    if (!res.ok) throw new Error(`HTTP error ${res.status}`);
    const data: RadarTrendsResponse = await res.json();
    cachedTrends = data.trends || [];
    sourceEl.innerText = data.source === 'snowflake' ? 'SNOWFLAKE LIVE' : 'LOCAL MEMORY';

    if (metaEl) {
      let metaText = `TOTAL SCANS: ${data.total_scans ?? 0} | UPDATED: ${data.updated_at || '--'}`;
      if (data.ai_unavailable_count && data.ai_unavailable_count > 0) {
        metaText += ` | AI UNAVAIL: ${data.ai_unavailable_count}`;
      }
      metaEl.innerText = metaText;
    }

    if (cachedTrends.length === 0) {
      container.innerHTML = '<div class="mono text-neutral" style="padding:16px 0;">No scans yet</div>';
      return;
    }

    container.innerHTML = cachedTrends.map((t: RadarTrendItem): string => {
      const barWidth = Math.min(Math.max(t.share_pct, 1), 100);
      let badgeHtml = '';
      if (t.is_new || t.flag === 'new' || (t.prev_count === 0 && t.count > 0)) {
        badgeHtml = '<span class="trend-badge badge-new">NEW</span>';
      } else if (t.change_pct !== null && t.change_pct !== undefined) {
        if (t.change_pct > 0) {
          badgeHtml = `<span class="trend-badge badge-up">▲ ${t.change_pct}%</span>`;
        } else if (t.change_pct < 0) {
          badgeHtml = `<span class="trend-badge badge-down">▼ ${Math.abs(t.change_pct)}%</span>`;
        } else {
          badgeHtml = '<span class="trend-badge badge-flat">—</span>';
        }
      } else {
        badgeHtml = '<span class="trend-badge badge-flat">—</span>';
      }

      return `
        <div class="bar-row">
          <div class="bar-header">
            <div class="bar-meta">
              <span class="mono" style="font-weight:600;">${radarEscapeHtml(t.tactic || 'UNKNOWN')}</span>
              <span class="mono text-neutral" style="font-size:11px;">(${t.count} hits)</span>
            </div>
            <div class="bar-meta">
              <span class="mono" style="font-weight:700;">${t.share_pct}%</span>
              ${badgeHtml}
            </div>
          </div>
          <div class="bar-container">
            <div class="bar-fill" style="width:${barWidth}%;"></div>
          </div>
        </div>
      `;
    }).join('');
  } catch (err) {
    clearTimeout(timeoutId);
    sourceEl.innerText = 'OFFLINE';
    container.innerHTML = '<div class="mono text-warn" style="padding:16px 0;">Failed to load telemetry (offline / timeout)</div>';
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
    const data: RadarCampaignsResponse = await res.json();
    cachedCampaigns = data.campaigns || [];
    sourceEl.innerText = data.source === 'snowflake' ? 'SNOWFLAKE ACTIVE' : 'ACTIVE CAMPAIGNS';

    if (cachedCampaigns.length === 0) {
      container.innerHTML = '<div class="mono text-neutral" style="padding:16px 0;">No campaigns yet</div>';
      drawCampaignGraph();
      return;
    }

    container.innerHTML = cachedCampaigns.map((c: RadarCampaignItem): string => {
      const tactic = c.top_tactic || c.primary_tactic || 'CLUSTER';
      return `
        <div style="display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid var(--grid);">
          <div style="display:flex;flex-direction:column;gap:2px;">
            <span class="mono" style="font-weight:600;">${radarEscapeHtml(c.campaign_id || '')}</span>
            <span class="mono text-neutral" style="font-size:10px;">${radarEscapeHtml(tactic)}</span>
          </div>
          <span class="mono text-warn">${radarEscapeHtml(String(c.variant_count || 1))} VARIANTS</span>
        </div>
      `;
    }).join('');

    drawCampaignGraph();
  } catch (err) {
    clearTimeout(timeoutId);
    sourceEl.innerText = 'OFFLINE';
    container.innerHTML = '<div class="mono text-warn" style="padding:16px 0;">Failed to load campaigns (offline / timeout)</div>';
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
  const matchedCamp: RadarCampaignItem | undefined = cachedCampaigns.find((c: RadarCampaignItem) =>
    c.campaign_id?.toLowerCase().includes(q) ||
    (c.top_tactic || c.primary_tactic)?.toLowerCase().includes(q)
  );

  if (matchedTrend) {
    const badgeText = matchedTrend.is_new ? 'NEW' : (matchedTrend.change_pct !== null ? `${matchedTrend.change_pct}% WoW` : 'baseline');
    resp.innerText = `FILTER MATCH: Tactic ${matchedTrend.tactic} accounts for ${matchedTrend.share_pct}% share (${matchedTrend.count} scans, ${badgeText}).`;
  } else if (matchedCamp) {
    const tactic = matchedCamp.top_tactic || matchedCamp.primary_tactic || 'UNKNOWN';
    resp.innerText = `FILTER MATCH: Campaign ${matchedCamp.campaign_id} (${tactic}) tracks ${matchedCamp.variant_count} observed variants.`;
  } else {
    const known = cachedTrends.map((t: RadarTrendItem) => t.tactic).join(', ') || 'None';
    resp.innerText = `FILTER MATCH: No direct match for "${input.value}". Monitored tactics: ${known}.`;
  }
}

// --- Campaign Graph (Illustrative / Variant-Sized) ---

function drawCampaignGraph(): void {
  const canvas = document.getElementById('campaignGraph') as HTMLCanvasElement;
  if (!canvas || !canvas.parentElement) return;
  const ctx = canvas.getContext('2d');
  if (!ctx) return;

  const w: number = (canvas.width = canvas.parentElement.clientWidth || 400);
  const h: number = (canvas.height = canvas.parentElement.clientHeight || 400);
  ctx.clearRect(0, 0, w, h);

  // Background radar grid lines
  ctx.strokeStyle = 'rgba(58, 58, 56, 0.15)';
  ctx.lineWidth = 1;
  const cx = w / 2;
  const cy = h / 2;
  const maxR = Math.min(w, h) * 0.42;

  for (let r = 40; r <= maxR; r += 40) {
    ctx.beginPath();
    ctx.arc(cx, cy, r, 0, Math.PI * 2);
    ctx.stroke();
  }
  ctx.beginPath();
  ctx.moveTo(cx, 0); ctx.lineTo(cx, h);
  ctx.moveTo(0, cy); ctx.lineTo(w, cy);
  ctx.stroke();

  if (cachedCampaigns.length === 0) {
    // Illustrative ambient nodes if no active campaigns yet
    ctx.fillStyle = 'rgba(26, 60, 43, 0.15)';
    for (let i = 0; i < 6; i++) {
      const angle = (i / 6) * Math.PI * 2;
      const x = cx + Math.cos(angle) * (maxR * 0.7);
      const y = cy + Math.sin(angle) * (maxR * 0.7);
      ctx.beginPath();
      ctx.arc(x, y, 8, 0, Math.PI * 2);
      ctx.fill();
    }
    return;
  }

  // Position nodes for real active campaigns
  const nodeCoords: { x: number; y: number; r: number; cid: string; variants: number }[] = [];
  const count = cachedCampaigns.length;

  cachedCampaigns.forEach((camp, idx) => {
    const angle = (idx / count) * Math.PI * 2 - Math.PI / 2;
    const distance = maxR * 0.65;
    const x = cx + Math.cos(angle) * distance;
    const y = cy + Math.sin(angle) * distance;
    // Variant-sized radius: 14 to 34 px
    const nodeR = Math.min(Math.max((camp.variant_count || 1) * 5 + 12, 14), 34);
    nodeCoords.push({ x, y, r: nodeR, cid: camp.campaign_id, variants: camp.variant_count || 1 });
  });

  // Connecting mesh edges
  ctx.strokeStyle = 'rgba(26, 60, 43, 0.25)';
  ctx.lineWidth = 1.5;
  for (let i = 0; i < nodeCoords.length; i++) {
    for (let j = i + 1; j < nodeCoords.length; j++) {
      ctx.beginPath();
      ctx.moveTo(nodeCoords[i].x, nodeCoords[i].y);
      ctx.lineTo(nodeCoords[j].x, nodeCoords[j].y);
      ctx.stroke();
    }
  }

  // Draw campaign nodes
  nodeCoords.forEach((node) => {
    // Outer glow ring
    ctx.beginPath();
    ctx.arc(node.x, node.y, node.r + 4, 0, Math.PI * 2);
    ctx.strokeStyle = 'rgba(255, 140, 105, 0.4)';
    ctx.lineWidth = 2;
    ctx.stroke();

    // Node body
    ctx.beginPath();
    ctx.arc(node.x, node.y, node.r, 0, Math.PI * 2);
    ctx.fillStyle = 'rgba(26, 60, 43, 0.85)';
    ctx.fill();

    // Center dot
    ctx.beginPath();
    ctx.arc(node.x, node.y, 3, 0, Math.PI * 2);
    ctx.fillStyle = '#9EFFBF';
    ctx.fill();

    // Node label
    ctx.fillStyle = 'var(--ink, #1A3C2B)';
    ctx.font = '10px JetBrains Mono, monospace';
    ctx.textAlign = 'center';
    ctx.fillText(`${node.cid} (${node.variants}v)`, node.x, node.y + node.r + 14);
  });
}

// --- Init & Refresh Loop ---

function refreshAll(): void {
  loadTrends();
  loadCampaigns();
}

function initRadar(): void {
  refreshAll();

  // 30-second auto-refresh
  setInterval(refreshAll, 30000);

  // Manual refresh button
  const refreshBtn = document.getElementById('refreshBtn') as HTMLButtonElement;
  if (refreshBtn) {
    refreshBtn.addEventListener('click', () => {
      refreshBtn.innerText = 'SYNCING...';
      refreshAll();
      setTimeout(() => { refreshBtn.innerText = 'REFRESH'; }, 1000);
    });
  }

  // Filter interaction
  const queryBtn = document.getElementById('queryBtn') as HTMLButtonElement;
  if (queryBtn) queryBtn.addEventListener('click', handleQuery);

  const queryInput = document.getElementById('queryInput') as HTMLInputElement;
  if (queryInput) {
    queryInput.addEventListener('keydown', (e: KeyboardEvent): void => {
      if (e.key === 'Enter') handleQuery();
    });
  }

  window.addEventListener('resize', () => {
    drawCampaignGraph();
  });
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initRadar);
} else {
  initRadar();
}
