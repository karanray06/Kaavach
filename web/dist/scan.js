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
function clearSelectedImage() {
    if (imageInput)
        imageInput.value = '';
    if (imagePreview) {
        imagePreview.src = '';
        imagePreview.style.display = 'none';
    }
    if (dropText)
        dropText.style.display = 'block';
}
// --- Image Upload ---
if (dropzone && imageInput) {
    dropzone.addEventListener('click', (e) => {
        // If clicking on a clear button, do not re-trigger file picker
        if (e.target.id === 'clearImageBtn') {
            e.stopPropagation();
            clearSelectedImage();
            return;
        }
        imageInput.click();
    });
    imageInput.addEventListener('change', (e) => {
        const target = e.target;
        if (target.files && target.files[0]) {
            const reader = new FileReader();
            reader.onload = (readerEvent) => {
                if (readerEvent.target?.result && imagePreview && dropText) {
                    imagePreview.src = readerEvent.target.result;
                    imagePreview.style.display = 'block';
                    dropText.style.display = 'none';
                }
            };
            reader.readAsDataURL(target.files[0]);
        }
    });
}
// --- Form Submission ---
const scanForm = document.getElementById('scanForm');
if (scanForm) {
    scanForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const textInput = document.getElementById('textInput');
        const text = textInput ? textInput.value.trim() : '';
        const file = imageInput?.files?.[0];
        const langRadio = document.querySelector('input[name="lang"]:checked');
        const lang = langRadio ? langRadio.value : 'en';
        if (!text && !file) {
            alert('Please provide text or an image.');
            return;
        }
        // C.6: Clear any previously selected image when user submits text only
        if (text && !file) {
            clearSelectedImage();
        }
        const timeline = document.getElementById('timeline');
        const resultPanel = document.getElementById('resultPanel');
        if (timeline)
            timeline.style.display = 'flex';
        if (resultPanel)
            resultPanel.style.display = 'none';
        const stages = ['ingest', 'extract', 'rules', 'classify', 'explain'];
        let currentStageIdx = 0;
        const progressInterval = window.setInterval(() => {
            if (currentStageIdx < stages.length) {
                const row = document.getElementById(`stage-${stages[currentStageIdx]}`);
                if (row) {
                    row.classList.add('active');
                    const statusSpan = row.querySelector('.status');
                    if (statusSpan)
                        statusSpan.innerText = 'DONE';
                }
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
                if (row) {
                    row.classList.add('active');
                    const statusSpan = row.querySelector('.status');
                    if (statusSpan)
                        statusSpan.innerText = 'DONE';
                }
            });
            showScanResults(data);
        }
        catch {
            clearInterval(progressInterval);
            alert('Error during scan processing');
        }
    });
}
// --- Result Rendering ---
function showScanResults(data) {
    const resultPanel = document.getElementById('resultPanel');
    if (!resultPanel)
        return;
    resultPanel.style.display = 'flex';
    // Visible banner when AI analysis is unavailable (C.4)
    const aiBanner = document.getElementById('aiUnavailableBanner');
    if (aiBanner) {
        if (data.ai_available === false || data.verdict === 'UNCERTAIN') {
            aiBanner.style.display = 'block';
        }
        else {
            aiBanner.style.display = 'none';
        }
    }
    const vText = document.getElementById('verdictText');
    if (vText) {
        const verdictDisplay = data.verdict === 'NO_RED_FLAGS' ? 'NO RED FLAGS FOUND' : data.verdict.replace(/_/g, ' ');
        vText.innerText = verdictDisplay;
        if (data.verdict === 'LIKELY_SCAM')
            vText.style.color = 'var(--warn)';
        else if (data.verdict === 'UNCERTAIN' || data.verdict === 'COULD_NOT_ASSESS')
            vText.style.color = 'var(--neutral)';
        else if (data.verdict === 'NO_RED_FLAGS')
            vText.style.color = 'var(--ink)';
        else
            vText.style.color = 'var(--neutral)';
    }
    const riskMeter = document.getElementById('riskMeter');
    if (riskMeter) {
        riskMeter.style.width = `${Math.min(Math.max((data.risk_score || 0) * 100, 0), 100)}%`;
    }
    // Tactics
    const tCont = document.getElementById('tacticsContainer');
    if (tCont) {
        tCont.innerHTML = '<div class="mono" style="margin: 12px 0;">DETECTED TACTICS</div>';
        if (data.tactics && data.tactics.length > 0) {
            data.tactics.forEach((t) => {
                const row = document.createElement('div');
                row.className = 'data-row';
                row.innerHTML = `<span class="mono">${scanEscapeHtml(t.code || '')}</span><span class="mono val text-neutral">${scanEscapeHtml(t.evidence || '')}</span>`;
                tCont.appendChild(row);
            });
        }
        else {
            tCont.innerHTML += '<div class="mono" style="color:var(--grey); padding:8px 0;">NONE DETECTED</div>';
        }
    }
    // Indicators
    const iCont = document.getElementById('indicatorsContainer');
    if (iCont) {
        iCont.innerHTML = '<div class="mono" style="margin: 12px 0;">INDICATORS</div>';
        if (data.indicators && data.indicators.length > 0) {
            data.indicators.forEach((ind) => {
                const row = document.createElement('div');
                row.className = 'data-row';
                row.innerHTML = `<span class="mono">${scanEscapeHtml(ind.type || '')}: ${scanEscapeHtml(ind.display || '')}</span><span class="mono val text-warn">SEEN ${scanEscapeHtml(String(ind.seen_before || 0))} TIMES</span>`;
                iCont.appendChild(row);
            });
        }
        else {
            iCont.innerHTML += '<div class="mono" style="color:var(--grey); padding:8px 0;">NONE FOUND</div>';
        }
    }
    // Explanation
    const exp = document.getElementById('explanationText');
    if (exp) {
        exp.innerText = data.explanation || '';
        if (data.lang === 'hi')
            exp.style.fontFamily = "'Noto Sans Devanagari', sans-serif";
        else if (data.lang === 'bn')
            exp.style.fontFamily = "'Noto Sans Bengali', sans-serif";
        else
            exp.style.fontFamily = 'var(--font-archivo)';
    }
    // Actions
    const aList = document.getElementById('actionsList');
    if (aList) {
        aList.innerHTML = '';
        if (data.actions && data.actions.length > 0) {
            data.actions.forEach((a) => {
                aList.innerHTML += `<li>${scanEscapeHtml(a)}</li>`;
            });
        }
    }
    // Campaign
    const campaignStrap = document.getElementById('campaignStrap');
    if (campaignStrap) {
        if (data.campaign) {
            campaignStrap.innerText = `CAMPAIGN ${data.campaign.id}, VARIANT ${data.campaign.variant_no}`;
        }
        else {
            campaignStrap.innerText = '';
        }
    }
    const modelStrap = document.getElementById('modelStrap');
    if (modelStrap) {
        modelStrap.innerText = `MODEL ${data.model}`;
    }
    // Reveal animations
    setTimeout(() => {
        document.querySelectorAll('.split-rev span, [data-rev]').forEach((el) => {
            el.style.opacity = '1';
            el.style.transform = 'translateY(0)';
        });
    }, 100);
}
//# sourceMappingURL=scan.js.map