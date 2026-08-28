// Mobile nav toggle
document.addEventListener('DOMContentLoaded', () => {
  const toggle = document.querySelector('.menu-toggle');
  const nav = document.querySelector('.masthead nav');
  if (toggle && nav) {
    toggle.addEventListener('click', () => {
      const open = nav.classList.toggle('open');
      toggle.setAttribute('aria-expanded', open);
    });
  }

  // Set today's date in masthead
  const dateEl = document.querySelector('[data-today]');
  if (dateEl) {
    const lang = document.documentElement.lang || 'ar';
    const locale = lang === 'ar' ? 'ar-EG' : 'en-GB';
    const now = new Date();
    try {
      dateEl.textContent = now.toLocaleDateString(locale, {
        weekday: 'long', day: 'numeric', month: 'long', year: 'numeric'
      });
    } catch (e) {
      dateEl.textContent = now.toDateString();
    }
  }

  // Contact form
  const form = document.querySelector('.contact-form form');
  if (form) {
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      const status = form.querySelector('.form-status');
      const isAr = document.documentElement.lang === 'ar';
      // Build mailto with form values
      const name = form.querySelector('[name=name]').value;
      const email = form.querySelector('[name=email]').value;
      const subject = form.querySelector('[name=subject]').value;
      const message = form.querySelector('[name=message]').value;
      const body = `${message}\n\n--\n${name}\n${email}`;
      window.location.href = `mailto:ahmed.m.ragab@proton.me?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
      status.textContent = isAr
        ? 'يتم فتح تطبيق البريد لديك — شكراً على رسالتك'
        : 'Your email client is opening — thanks for reaching out.';
      status.className = 'form-status show success';
    });
  }
});
