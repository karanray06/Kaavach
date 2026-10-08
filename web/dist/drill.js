"use strict";
/**
 * drill.ts — Kavach drill (inoculation) page logic.
 */
function drillReveal(guessedScam) {
    const btnGroup = document.getElementById('btnGroup');
    btnGroup.style.display = 'none';
    const rev = document.getElementById('revealSection');
    rev.style.display = 'block';
    const title = document.getElementById('revealTitle');
    if (guessedScam) {
        title.innerText = "CORRECT. IT'S A SCAM.";
        title.style.color = 'var(--red)';
    }
    else {
        title.innerText = "CAREFUL. IT'S A SCAM.";
        title.style.color = 'var(--ink)';
    }
}
//# sourceMappingURL=drill.js.map