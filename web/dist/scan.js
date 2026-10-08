"use strict";
/**
 * scan.ts — Kavach scan page logic.
 */
// --- Utilities ---
function scanEscapeHtml(str) {
    const div = document.createElement('div');
    div.appendChild(document.createTextNode(str));
    return div.innerHTML;
}
// --- DOM References ---
const dropzone = document.getElementById('dropzone');
const imageInput = document.getElementById('imageInput');
const imagePreview = document.getElementById('imagePreview');
const dropText = document.getElementById('dropText');
// --- Image Upload ---
dropzone.addEventListener('click', () => imageInput.click());
imageInput.addEventListener('change', (e) => {
    const target = e.target;
    if (target.files && target.files[0]) {
        const reader = new FileReader();
        reader.onload = (readerEvent) => {
            if (readerEvent.target?.result) {
                imagePreview.src = readerEvent.target.result;
                imagePreview.style.display = 'block';
                dropText.style.display = 'none';
            }
        };
        reader.readAsDataURL(target.files[0]);
    }
});
// --- Form Submission ---
const scanForm = document.getElementById('scanForm');
scanForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const textInput = document.getElementById('textInput');
    const text = textInput.value;
    const file = imageInput.files?.[0];
    const langRadio = document.querySelector('input[name="lang"]:checked');
    const lang = langRadio.value;
    if (!text && !file) {
        alert('Please provide text or an image.');
        return;
    }
    const timeline = document.getElementById('timeline');
    const resultPanel = document.getElementById('resultPanel');
    timeline.style.display = 'flex';
    resultPanel.style.display = 'none';
    const stages = ['ingest', 'extract', 'rules', 'classify', 'explain'];
    let currentStageIdx = 0;
    const progressInterval = window.setInterval(() => {
        if (currentStageIdx < stages.length) {
            const row = document.getElementById(`stage-${stages[currentStageIdx]}`);
            row.classList.add('active');
            row.querySelector('.status').innerText = 'DONE';
            currentStageIdx++;
        }
    }, 800);
    const formData = new FormData();
    if (text)
        formData.append('text', text);
    if (file)
        formData.append('image', file);
    formData.append('lang', lang);
    try {
        const response = await fetch('/api/scan', { method: 'POST', body: formData });
        const data = await response.json();
        clearInterval(progressInterval);
        stages.forEach((s) => {
            const row = document.getElementById(`stage-${s}`);
            row.classList.add('active');
            row.querySelector('.status').innerText = 'DONE';
        });
        showScanResults(data);
    }
    catch {
        clearInterval(progressInterval);
        alert('Error during scan');
    }
});
// --- Result Rendering ---
function showScanResults(data) {
    const resultPanel = document.getElementById('resultPanel');
    resultPanel.style.display = 'flex';
    const vText = document.getElementById('verdictText');
    const verdictDisplay = data.verdict === 'NO_RED_FLAGS' ? 'NO RED FLAGS FOUND' : data.verdict.replace(/_/g, ' ');
    vText.innerText = verdictDisplay;
    if (data.verdict === 'LIKELY_SCAM')
        vText.style.color = 'var(--red)';
    else if (data.verdict === 'COULD_NOT_ASSESS')
        vText.style.color = 'var(--grey)';
    else if (data.verdict === 'NO_RED_FLAGS')
        vText.style.color = 'var(--ink)';
    else
        vText.style.color = 'var(--grey)';
    document.getElementById('riskMeter').style.width =
        `${Math.min(Math.max(data.risk_score * 100, 0), 100)}%`;
    // Tactics
    const tCont = document.getElementById('tacticsContainer');
    tCont.innerHTML = '<div class="mono" style="margin: 12px 0;">DETECTED TACTICS</div>';
    if (data.tactics && data.tactics.length > 0) {
        data.tactics.forEach((t) => {
            const row = document.createElement('div');
            row.className = 'data-row rule-row';
            row.innerHTML = `<span class="headline">${scanEscapeHtml(t.code || '')}</span><span class="mono">${scanEscapeHtml(t.evidence || '')}</span>`;
            tCont.appendChild(row);
        });
    }
    else {
        tCont.innerHTML += '<div class="mono" style="color:var(--grey); padding:8px 0;">NONE DETECTED</div>';
    }
    // Indicators
    const iCont = document.getElementById('indicatorsContainer');
    iCont.innerHTML = '<div class="mono" style="margin: 12px 0;">INDICATORS</div>';
    if (data.indicators && data.indicators.length > 0) {
        data.indicators.forEach((ind) => {
            const row = document.createElement('div');
            row.className = 'data-row rule-row';
            row.innerHTML = `<span class="mono">${scanEscapeHtml(ind.type || '')} : ${scanEscapeHtml(ind.display || '')}</span><span class="mono red">SEEN ${scanEscapeHtml(String(ind.seen_before || 0))} TIMES</span>`;
            iCont.appendChild(row);
        });
    }
    else {
        iCont.innerHTML += '<div class="mono" style="color:var(--grey); padding:8px 0;">NONE FOUND</div>';
    }
    // Explanation
    const exp = document.getElementById('explanationText');
    exp.innerText = data.explanation || '';
    if (data.lang === 'hi')
        exp.style.fontFamily = "'Noto Sans Devanagari', sans-serif";
    else if (data.lang === 'bn')
        exp.style.fontFamily = "'Noto Sans Bengali', sans-serif";
    else
        exp.style.fontFamily = 'var(--font-archivo)';
    // Actions
    const aList = document.getElementById('actionsList');
    aList.innerHTML = '';
    if (data.actions && data.actions.length > 0) {
        data.actions.forEach((a) => {
            aList.innerHTML += `<li>${scanEscapeHtml(a)}</li>`;
        });
    }
    // Campaign
    const campaignStrap = document.getElementById('campaignStrap');
    if (data.campaign) {
        campaignStrap.innerText = `CAMPAIGN ${data.campaign.id}, VARIANT ${data.campaign.variant_no}`;
    }
    else {
        campaignStrap.innerText = '';
    }
    document.getElementById('modelStrap').innerText = `MODEL ${data.model}`;
    // Reveal animations
    setTimeout(() => {
        document.querySelectorAll('.split-rev span, [data-rev]').forEach((el) => {
            el.style.opacity = '1';
            el.style.transform = 'translateY(0)';
        });
    }, 100);
}
//# sourceMappingURL=scan.js.map