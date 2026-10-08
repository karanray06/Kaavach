/**
 * drill.ts — Kavach drill (inoculation) page logic.
 */

function drillReveal(guessedScam: boolean): void {
  const btnGroup = document.getElementById('btnGroup') as HTMLDivElement;
  if (btnGroup) btnGroup.style.display = 'none';

  const rev = document.getElementById('revealSection') as HTMLDivElement;
  if (rev) rev.style.display = 'block';

  const title = document.getElementById('revealTitle') as HTMLDivElement;
  if (title) {
    if (guessedScam) {
      title.innerText = "CORRECT. IT'S A SCAM.";
      title.style.color = 'var(--warn)';
    } else {
      title.innerText = "CAREFUL. IT'S A SCAM.";
      title.style.color = 'var(--ink)';
    }
  }
}

async function loadDrillSample(): Promise<void> {
  const msgEl = document.getElementById('messageText') as HTMLDivElement;
  const tacticEl = document.getElementById('drillTactic') as HTMLDivElement;
  const redFlagBox = document.getElementById('redFlagBox') as HTMLDivElement;

  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 10000);
    const res = await fetch('/api/drill/sample', { signal: controller.signal });
    clearTimeout(timeoutId);

    if (res.ok) {
      const data = await res.json();
      if (data && data.text && msgEl) {
        msgEl.innerText = data.text;
        if (tacticEl && data.tactic) {
          tacticEl.innerText = `TACTIC: ${data.tactic}`;
        }
        if (redFlagBox && data.red_flags && Array.isArray(data.red_flags)) {
          let flaggedHtml = data.text;
          data.red_flags.forEach((flag: string) => {
            if (flag && flaggedHtml.includes(flag)) {
              flaggedHtml = flaggedHtml.split(flag).join(`<span class="red-flag">${flag}</span>`);
            }
          });
          redFlagBox.innerHTML = flaggedHtml;
        }
      }
    }
  } catch {
    // Keep fallback sample
  }
}

function resetDrill(): void {
  const btnGroup = document.getElementById('btnGroup') as HTMLDivElement;
  if (btnGroup) btnGroup.style.display = 'flex';
  const rev = document.getElementById('revealSection') as HTMLDivElement;
  if (rev) rev.style.display = 'none';
  loadDrillSample();
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', loadDrillSample);
} else {
  loadDrillSample();
}

// Attach globally for inline onclick handlers
(window as unknown as Record<string, unknown>)['drillReveal'] = drillReveal;
(window as unknown as Record<string, unknown>)['resetDrill'] = resetDrill;
