"use strict";
/**
 * drill.ts — Kavach drill (inoculation) page logic.
 */
function drillReveal(guessedScam) {
    const btnGroup = document.getElementById('btnGroup');
    if (btnGroup)
        btnGroup.style.display = 'none';
    const rev = document.getElementById('revealSection');
    if (rev)
        rev.style.display = 'block';
    const title = document.getElementById('revealTitle');
    if (title) {
        if (guessedScam) {
            title.innerText = "CORRECT. IT'S A SCAM.";
            title.style.color = 'var(--warn)';
        }
        else {
            title.innerText = "CAREFUL. IT'S A SCAM.";
            title.style.color = 'var(--ink)';
        }
    }
}
async function loadDrillSample() {
    const msgEl = document.getElementById('messageText');
    const tacticEl = document.getElementById('drillTactic');
    const redFlagBox = document.getElementById('redFlagBox');
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
                    data.red_flags.forEach((flag) => {
                        if (flag && flaggedHtml.includes(flag)) {
                            flaggedHtml = flaggedHtml.split(flag).join(`<span class="red-flag">${flag}</span>`);
                        }
                    });
                    redFlagBox.innerHTML = flaggedHtml;
                }
            }
        }
    }
    catch {
        // Keep fallback sample
    }
}
function resetDrill() {
    const btnGroup = document.getElementById('btnGroup');
    if (btnGroup)
        btnGroup.style.display = 'flex';
    const rev = document.getElementById('revealSection');
    if (rev)
        rev.style.display = 'none';
    loadDrillSample();
}
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', loadDrillSample);
}
else {
    loadDrillSample();
}
// Attach globally for inline onclick handlers
window['drillReveal'] = drillReveal;
window['resetDrill'] = resetDrill;
//# sourceMappingURL=drill.js.map