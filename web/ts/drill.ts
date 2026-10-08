/**
 * drill.ts — Kavach drill (inoculation) page logic.
 */

function drillReveal(guessedScam: boolean): void {
  const btnGroup = document.getElementById('btnGroup') as HTMLDivElement;
  btnGroup.style.display = 'none';

  const rev = document.getElementById('revealSection') as HTMLDivElement;
  rev.style.display = 'block';

  const title = document.getElementById('revealTitle') as HTMLDivElement;
  if (guessedScam) {
    title.innerText = "CORRECT. IT'S A SCAM.";
    title.style.color = 'var(--warn)';
  } else {
    title.innerText = "CAREFUL. IT'S A SCAM.";
    title.style.color = 'var(--ink)';
  }
}
