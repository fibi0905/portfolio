(() => {
  'use strict';

  const page = document.body.dataset.page;

  const getJSON = async (url) => {
    const res = await fetch(url, { cache: 'no-cache' });
    if (!res.ok) throw new Error(`${url}: ${res.status}`);
    return res.json();
  };

  const el = (tag, props = {}, ...children) => {
    const node = document.createElement(tag);
    for (const [key, value] of Object.entries(props)) {
      if (value == null || value === false) continue;
      if (key === 'class') node.className = value;
      else if (key === 'text') node.textContent = value;
      else node.setAttribute(key, value === true ? '' : value);
    }
    node.append(...children.flat().filter(Boolean));
    return node;
  };

  const bareUrl = (url) => url.replace(/^https?:\/\/(www\.)?/, '').replace(/\/$/, '');

  const initials = (name) => {
    const words = (name.match(/[\p{L}\p{N}]+/gu) || []).filter((w) => w.length > 2);
    const pick = (words.length ? words : name.match(/[\p{L}\p{N}]+/gu) || ['?']).slice(0, 2);
    return pick.map((w) => w[0]).join('').toUpperCase();
  };

  /* ---------- Dati del sito ---------- */
  const fillSite = (site) => {
    const titles = {
      home: `${site.name} | ${site.role}`,
      projects: `Progetti | ${site.name}`,
      contact: `Contatti | ${site.name}`,
    };
    if (titles[page]) document.title = titles[page];

    document.querySelectorAll('[data-text]').forEach((node) => {
      const value = site[node.dataset.text];
      if (value) node.textContent = value;
    });

    document.querySelectorAll('[data-href]').forEach((node) => {
      const value = site[node.dataset.href];
      if (!value) { node.hidden = true; return; }
      node.href = value;
      if ('show' in node.dataset) node.textContent = bareUrl(value);
    });

    document.querySelectorAll('[data-mail]').forEach((node) => {
      node.href = `mailto:${site.email}`;
      if ('show' in node.dataset) node.textContent = site.email;
    });

    const phoneRow = document.querySelector('[data-optional="phone"]');
    if (phoneRow && site.phone) {
      const link = phoneRow.querySelector('[data-phone]');
      link.href = `tel:${site.phone.replace(/[^\d+]/g, '')}`;
      link.textContent = site.phone;
      phoneRow.hidden = false;
    }

    document.querySelectorAll('[data-year]').forEach((node) => {
      node.textContent = new Date().getFullYear();
    });

    const skills = document.getElementById('skills');
    if (skills) skills.replaceChildren(...(site.skills || []).map((s) => el('li', { text: s })));
  };

  /* ---------- Progetti ---------- */
  const tagList = (items) => el('ul', { class: 'tags' }, items.map((t) => el('li', { text: t })));

  const metaRow = (label, items) =>
    items && items.length ? el('div', {}, el('dt', { text: label }), el('dd', {}, tagList(items))) : null;

  const projectEl = (p) => {
    const media = el('div', { class: 'project-media' });
    if (p.image) {
      media.append(el('img', {
        src: p.image,
        alt: `Anteprima del progetto ${p.name}`,
        loading: 'lazy',
        decoding: 'async',
      }));
    } else {
      media.append(el('div', { class: 'placeholder', 'aria-hidden': 'true', text: initials(p.name) }));
    }

    return el('article', { class: 'project' },
      media,
      el('div', { class: 'project-body' },
        el('h3', { class: 'project-title', text: p.name }),
        el('p', { class: 'project-desc', text: p.description }),
        el('dl', { class: 'project-meta' },
          metaRow('Tecnologie', p.technologies),
          metaRow('Linguaggi', p.languages)),
        el('div', { class: 'project-actions' },
          el('a', { class: 'btn btn-primary', href: p.repo, target: '_blank', rel: 'noopener noreferrer', text: 'Vedi repository' }),
          el('a', { class: 'repo-link', href: p.repo, target: '_blank', rel: 'noopener noreferrer', text: bareUrl(p.repo) }))));
  };

  const renderProjects = (projects) => {
    const list = document.getElementById('projects');
    if (list) list.replaceChildren(...projects.map(projectEl));

    const featured = document.getElementById('featured');
    if (featured) {
      const main = projects.find((p) => p.featured) || projects[0];
      if (main) featured.replaceChildren(projectEl(main));
    }
  };

  /* ---------- Form contatti ---------- */
  const initForm = (site) => {
    const form = document.getElementById('contact-form');
    if (!form) return;
    const status = document.getElementById('form-status');
    const button = form.querySelector('button[type="submit"]');

    const setStatus = (text, state) => {
      status.textContent = text;
      status.dataset.state = state || '';
    };

    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      if (!form.reportValidity()) return;

      button.disabled = true;
      setStatus('Invio in corso…', 'pending');

      try {
        const res = await fetch('/api/contact', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(Object.fromEntries(new FormData(form))),
        });
        const data = await res.json().catch(() => ({}));
        if (res.status === 429) throw new Error('Troppi invii ravvicinati. Riprova tra qualche minuto.');
        if (!res.ok || !data.ok) throw new Error(data.error || '');
        form.reset();
        setStatus('Messaggio inviato. Ti risponderò appena possibile.', 'ok');
      } catch (err) {
        setStatus(err.message || `Invio non riuscito. Riprova tra poco o scrivi a ${site.email}.`, 'error');
      } finally {
        button.disabled = false;
      }
    });
  };

  /* ---------- Avvio ---------- */
  const start = async () => {
    try {
      const needsProjects = page === 'home' || page === 'projects';
      const [site, projects] = await Promise.all([
        getJSON('/content/site.json'),
        needsProjects ? getJSON('/content/projects.json') : Promise.resolve([]),
      ]);
      fillSite(site);
      if (needsProjects) renderProjects(projects);
      initForm(site);
    } catch (err) {
      console.error(err);
      const target = document.getElementById('projects') || document.getElementById('featured');
      if (target) target.textContent = 'Impossibile caricare i contenuti. Riprova più tardi.';
    }
  };

  start();
})();
