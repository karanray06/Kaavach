document.addEventListener('DOMContentLoaded', () => {
  // Split words for text reveal
  const splitTargets = document.querySelectorAll('.split-rev');
  splitTargets.forEach(target => {
    const text = target.innerText;
    target.innerHTML = '';
    const words = text.split(' ');
    words.forEach((word, i) => {
      const span = document.createElement('span');
      span.innerText = word + ' ';
      span.style.transitionDelay = `${i * 36}ms`;
      target.appendChild(span);
    });
  });

  // Intersection Observer for revealing elements
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
        
        // Handle custom delay for data-rev elements
        if (entry.target.hasAttribute('data-rev')) {
          const delay = entry.target.style.getPropertyValue('--d') || '0ms';
          entry.target.style.transitionDelay = delay;
        }
      }
    });
  }, { threshold: 0.12 });

  document.querySelectorAll('.split-rev, [data-rev]').forEach(el => {
    observer.observe(el);
  });
});
