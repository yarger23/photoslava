(() => {
  'use strict';
  const menu = document.querySelector('.mobile-menu');
  const toggle = document.querySelector('.menu-btn');
  const background = [...document.querySelectorAll('main, .footer')];
  function setMenu(open) {
    if (!menu || !toggle) return;
    document.body.classList.toggle('menu-open', open);
    toggle.setAttribute('aria-expanded', String(open));
    toggle.setAttribute('aria-label', open ? 'Закрыть меню' : 'Открыть меню');
    menu.setAttribute('aria-hidden', String(!open));
    menu.inert = !open;
    background.forEach(el => { el.inert = open; });
    if (open) menu.querySelector('a')?.focus();
  }
  if (menu && toggle) {
    menu.id = 'mobile-navigation';
    toggle.setAttribute('aria-controls', menu.id);
    menu.inert = true;
    toggle.addEventListener('click', () => setMenu(toggle.getAttribute('aria-expanded') !== 'true'));
    menu.querySelectorAll('a').forEach(a => a.addEventListener('click', () => setMenu(false)));
    document.addEventListener('keydown', event => {
      if (!document.body.classList.contains('menu-open')) return;
      if (event.key === 'Escape') { setMenu(false); toggle.focus(); }
      if (event.key === 'Tab') {
        const links = [toggle, ...menu.querySelectorAll('a[href],button:not([disabled])')];
        const first = links[0], last = links.at(-1);
        if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
        else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
      }
    });
    window.matchMedia('(min-width:980px)').addEventListener('change', event => { if (event.matches) setMenu(false); });
  }
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
  document.querySelectorAll('[data-story-slider]').forEach(slider => {
    const track = slider.querySelector('[data-story-track]');
    const slides = [...track.children];
    const prev = slider.querySelector('[data-story-prev]');
    const next = slider.querySelector('[data-story-next]');
    const count = slider.querySelector('[data-story-current]');
    const step = () => slides[0].getBoundingClientRect().width + (parseFloat(getComputedStyle(track).gap) || 0);
    function update() {
      const max = Math.max(0, track.scrollWidth - track.clientWidth);
      prev.disabled = track.scrollLeft < 2;
      next.disabled = track.scrollLeft >= max - 2;
      count.textContent = String(Math.round(track.scrollLeft / step()) + 1).padStart(2, '0');
    }
    function move(dir) { track.scrollBy({left:dir * step(), behavior:reduced.matches ? 'instant' : 'smooth'}); }
    prev.addEventListener('click', () => move(-1)); next.addEventListener('click', () => move(1));
    track.addEventListener('scroll', update, {passive:true});
    window.addEventListener('resize', update, {passive:true});
    update();
  });
  document.querySelectorAll('[data-package]').forEach(link => link.addEventListener('click', () => {
    const message = document.querySelector('[data-message]');
    if (message && !message.value.trim()) message.value = `Здравствуйте! Интересует ${link.dataset.package.toLowerCase()}.`;
  }));
  document.querySelectorAll('[data-telegram-form]').forEach(form => {
    form.addEventListener('submit', event => {
      event.preventDefault();
      if (!form.reportValidity()) return;
      const name = form.querySelector('[data-name]').value.trim();
      const idea = form.querySelector('[data-message]').value.trim();
      const contact = form.querySelector('[data-contact]')?.value.trim();
      const message = [name ? `Здравствуйте! Меня зовут ${name}.` : 'Здравствуйте!', idea || 'Хочу обсудить портретную съёмку.', contact ? `Для связи: ${contact}` : ''].filter(Boolean).join('\n\n');
      const destination = new URL(form.action);
      // Official Telegram username deep link: text is a draft, not an automatic send.
      destination.searchParams.set('text', message);
      window.location.assign(destination.href);
    });
  });
})();
