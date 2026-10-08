/**
 * reveal.ts — Scroll-triggered text reveal and intersection observer animations.
 */

document.addEventListener('DOMContentLoaded', (): void => {
  // Split words for text reveal
  const splitTargets = document.querySelectorAll<HTMLElement>('.split-rev');
  splitTargets.forEach((target: HTMLElement): void => {
    const text: string = target.innerText;
    target.innerHTML = '';
    const words: string[] = text.split(' ');
    words.forEach((word: string, i: number): void => {
      const span: HTMLSpanElement = document.createElement('span');
      span.innerText = word + ' ';
      span.style.transitionDelay = `${i * 36}ms`;
      target.appendChild(span);
    });
  });

  // Intersection Observer for revealing elements
  const observer = new IntersectionObserver(
    (entries: IntersectionObserverEntry[]): void => {
      entries.forEach((entry: IntersectionObserverEntry): void => {
        if (entry.isIntersecting) {
          (entry.target as HTMLElement).classList.add('visible');

          // Handle custom delay for data-rev elements
          if (entry.target.hasAttribute('data-rev')) {
            const delay: string =
              (entry.target as HTMLElement).style.getPropertyValue('--d') || '0ms';
            (entry.target as HTMLElement).style.transitionDelay = delay;
          }
        }
      });
    },
    { threshold: 0.12 }
  );

  document.querySelectorAll<HTMLElement>('.split-rev, [data-rev]').forEach(
    (el: HTMLElement): void => {
      observer.observe(el);
    }
  );
});
