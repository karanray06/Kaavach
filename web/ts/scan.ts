/**
 * scan.ts — Kavach scan page logic.
 */

// --- Type Definitions ---

interface ScanTactic {
  code: string;
  evidence: string;
}

interface ScanIndicator {
  type: string;
  display: string;
  seen_before: number;
}

interface ScanCampaign {
  id: string;
  variant_no: number;
  first_seen: string;
  variants: number;
}

interface ScanResult {
  scan_id: string;
  verdict: 'LIKELY_SCAM' | 'SUSPICIOUS' | 'NO_RED_FLAGS' | 'COULD_NOT_ASSESS';
  risk_score: number;
  confidence: number;
  tactics: ScanTactic[];
  indicators: ScanIndicator[];
  explanation: string;
  actions: string[];
  campaign: ScanCampaign | null;
  lang: string;
  timings_ms: Record<string, number>;
  model: string;
}

// --- Utilities ---

function scanEscapeHtml(str: string): string {
  const div: HTMLDivElement = document.createElement('div');
  div.appendChild(document.createTextNode(str));
  return div.innerHTML;
}

// --- DOM References ---

const dropzone = document.getElementById('dropzone') as HTMLDivElement;
const imageInput = document.getElementById('imageInput') as HTMLInputElement;
const imagePreview = document.getElementById('imagePreview') as HTMLImageElement;
const dropText = document.getElementById('dropText') as HTMLSpanElement;

// --- Image Upload ---

dropzone.addEventListener('click', (): void => imageInput.click());

imageInput.addEventListener('change', (e: Event): void => {
  const target = e.target as HTMLInputElement;
  if (target.files && target.files[0]) {
    const reader = new FileReader();
    reader.onload = (readerEvent: ProgressEvent<FileReader>): void => {
      if (readerEvent.target?.result) {
        imagePreview.src = readerEvent.target.result as string;
        imagePreview.style.display = 'block';
        dropText.style.display = 'none';
      }
    };
    reader.readAsDataURL(target.files[0]);
  }
});

// --- Form Submission ---

const scanForm = document.getElementById('scanForm') as HTMLFormElement;

scanForm.addEventListener('submit', async (e: Event): Promise<void> => {
  e.preventDefault();

  const textInput = document.getElementById('textInput') as HTMLTextAreaElement;
  const text: string = textInput.value;
  const file: File | undefined = imageInput.files?.[0];
  const langRadio = document.querySelector('input[name="lang"]:checked') as HTMLInputElement;
  const lang: string = langRadio.value;

  if (!text && !file) {
    alert('Please provide text or an image.');
    return;
  }

  const timeline = document.getElementById('timeline') as HTMLDivElement;
  const resultPanel = document.getElementById('resultPanel') as HTMLDivElement;
  timeline.style.display = 'flex';
  resultPanel.style.display = 'none';

  const stages: string[] = ['ingest', 'extract', 'rules', 'classify', 'explain'];
  let currentStageIdx = 0;

  const progressInterval: number = window.setInterval((): void => {
    if (currentStageIdx < stages.length) {
      const row = document.getElementById(`stage-${stages[currentStageIdx]}`) as HTMLDivElement;
      row.classList.add('active');
      (row.querySelector('.status') as HTMLSpanElement).innerText = 'DONE';
      currentStageIdx++;
    }
  }, 800);

  const formData = new FormData();
  if (text) formData.append('text', text);
  if (file) formData.append('image', file);
  formData.append('lang', lang);

  try {
    const response: Response = await fetch('/api/scan', { method: 'POST', body: formData });
    const data: ScanResult = await response.json();
    clearInterval(progressInterval);
    stages.forEach((s: string): void => {
      const row = document.getElementById(`stage-${s}`) as HTMLDivElement;
      row.classList.add('active');
      (row.querySelector('.status') as HTMLSpanElement).innerText = 'DONE';
    });
    showScanResults(data);
  } catch {
    clearInterval(progressInterval);
    alert('Error during scan');
  }
});

// --- Result Rendering ---

function showScanResults(data: ScanResult): void {
  const resultPanel = document.getElementById('resultPanel') as HTMLDivElement;
  resultPanel.style.display = 'flex';

  const vText = document.getElementById('verdictText') as HTMLDivElement;
  const verdictDisplay: string =
    data.verdict === 'NO_RED_FLAGS' ? 'NO RED FLAGS FOUND' : data.verdict.replace(/_/g, ' ');
  vText.innerText = verdictDisplay;

  if (data.verdict === 'LIKELY_SCAM') vText.style.color = 'var(--warn)';
  else if (data.verdict === 'COULD_NOT_ASSESS') vText.style.color = 'var(--neutral)';
  else if (data.verdict === 'NO_RED_FLAGS') vText.style.color = 'var(--ink)';
  else vText.style.color = 'var(--neutral)';

  (document.getElementById('riskMeter') as HTMLDivElement).style.width =
    `${Math.min(Math.max(data.risk_score * 100, 0), 100)}%`;

  // Tactics
  const tCont = document.getElementById('tacticsContainer') as HTMLDivElement;
  tCont.innerHTML = '<div class="mono" style="margin: 12px 0;">DETECTED TACTICS</div>';
  if (data.tactics && data.tactics.length > 0) {
    data.tactics.forEach((t: ScanTactic): void => {
      const row = document.createElement('div');
      row.className = 'data-row';
      row.innerHTML = `<span class="mono">${scanEscapeHtml(t.code || '')}</span><span class="mono val text-neutral">${scanEscapeHtml(t.evidence || '')}</span>`;
      tCont.appendChild(row);
    });
  } else {
    tCont.innerHTML += '<div class="mono" style="color:var(--grey); padding:8px 0;">NONE DETECTED</div>';
  }

  // Indicators
  const iCont = document.getElementById('indicatorsContainer') as HTMLDivElement;
  iCont.innerHTML = '<div class="mono" style="margin: 12px 0;">INDICATORS</div>';
  if (data.indicators && data.indicators.length > 0) {
    data.indicators.forEach((ind: ScanIndicator): void => {
      const row = document.createElement('div');
      row.className = 'data-row';
      row.innerHTML = `<span class="mono">${scanEscapeHtml(ind.type || '')}: ${scanEscapeHtml(ind.display || '')}</span><span class="mono val text-warn">SEEN ${scanEscapeHtml(String(ind.seen_before || 0))} TIMES</span>`;
      iCont.appendChild(row);
    });
  } else {
    iCont.innerHTML += '<div class="mono" style="color:var(--grey); padding:8px 0;">NONE FOUND</div>';
  }

  // Explanation
  const exp = document.getElementById('explanationText') as HTMLParagraphElement;
  exp.innerText = data.explanation || '';
  if (data.lang === 'hi') exp.style.fontFamily = "'Noto Sans Devanagari', sans-serif";
  else if (data.lang === 'bn') exp.style.fontFamily = "'Noto Sans Bengali', sans-serif";
  else exp.style.fontFamily = 'var(--font-archivo)';

  // Actions
  const aList = document.getElementById('actionsList') as HTMLOListElement;
  aList.innerHTML = '';
  if (data.actions && data.actions.length > 0) {
    data.actions.forEach((a: string): void => {
      aList.innerHTML += `<li>${scanEscapeHtml(a)}</li>`;
    });
  }

  // Campaign
  const campaignStrap = document.getElementById('campaignStrap') as HTMLSpanElement;
  if (data.campaign) {
    campaignStrap.innerText = `CAMPAIGN ${data.campaign.id}, VARIANT ${data.campaign.variant_no}`;
  } else {
    campaignStrap.innerText = '';
  }
  (document.getElementById('modelStrap') as HTMLSpanElement).innerText = `MODEL ${data.model}`;

  // Reveal animations
  setTimeout((): void => {
    document.querySelectorAll<HTMLElement>('.split-rev span, [data-rev]').forEach((el: HTMLElement): void => {
      el.style.opacity = '1';
      el.style.transform = 'translateY(0)';
    });
  }, 100);
}
