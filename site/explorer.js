(function () {
  'use strict';

  const descriptions = {
    L0: { name: 'Always hold', text: 'Predicts no change at every meeting. A simple reference for how much the market already knows.' },
    L1: { name: 'Market pricing', text: 'An OIS-based proxy using a fixed move-size assumption. Historical reads clip to the first one-month node; archive dates do not verify public release timing. This is the v1 benchmark to beat.' },
    L2: { name: 'Market model', text: 'Learns from earlier market pricing and decisions to assign cut, hold and hike probabilities. This checks whether a fitted model improves on the market proxy itself.' },
    L3: { name: 'Market + tone', text: 'Adds the previous minutes\' tone index and vote skew to market pricing. Both communication measures are available before the forecast decision.' },
    L4: { name: 'Member votes', text: 'Blends market pricing with patterns in members\' previous votes, then simulates the committee decision. It uses no tone. Its majority-to-hold mapping and historical roster availability are limitations, described in the methodology.' },
  };
  const metrics = {
    brier: { field: 'mean_brier', label: 'Mean Brier score', key: 'Average squared probability error across cut, hold and hike. Lower is better.' },
    log: { field: 'mean_log_score', label: 'Mean log score', key: 'Lower is better. Confident mistakes are penalised especially heavily.' },
    skill: { field: 'skill_vs_l1', label: 'Skill versus market', key: 'Improvement in Brier score relative to the market: zero is a tie, positive is better, negative is worse.' },
  };

  ladderPromise.then(data => {
    const scores = data.headline_scores_scheduled_only;
    const tool = document.getElementById('comparison-tool');
    const bars = document.getElementById('model-bars');
    const insight = document.getElementById('model-insight');
    const baseline = document.getElementById('show-baseline');
    let metric = 'brier';
    let selected = 'L3';

    function draw() {
      const spec = metrics[metric];
      const models = baseline.checked ? ['L0', 'L1', 'L2', 'L3', 'L4'] : ['L1', 'L2', 'L3', 'L4'];
      if (!models.includes(selected)) selected = 'L3';
      const limit = Math.max(...models.map(model => Math.abs(scores[model][spec.field] || 0)), Number.EPSILON);
      document.getElementById('comparison-key').textContent = spec.key;
      bars.replaceChildren();
      for (const model of models) {
        const value = scores[model][spec.field];
        const label = value == null ? (model === 'L1' && metric === 'skill' ? 'baseline' : '\u2014') : fmtScore(value);
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'model-bar';
        button.dataset.model = model;
        button.setAttribute('aria-pressed', String(model === selected));
        button.setAttribute('aria-label', `${model}, ${descriptions[model].name}: ${spec.label} ${label}`);
        button.innerHTML = '<span class="model-bar-label"><strong></strong><span></span></span><span class="model-bar-track"><span class="model-bar-fill"></span></span><span class="model-bar-value"></span>';
        button.querySelector('strong').textContent = model;
        button.querySelector('.model-bar-label > span').textContent = descriptions[model].name;
        button.querySelector('.model-bar-value').textContent = label;
        const track = button.querySelector('.model-bar-track');
        if (metric === 'skill') track.classList.add('skill-track');
        const fill = button.querySelector('.model-bar-fill');
        fill.style.width = `${Math.abs(value || 0) / limit * 100}%`;
        fill.hidden = value == null || value === 0;
        button.addEventListener('click', () => {
          selected = model;
          for (const row of bars.children) row.setAttribute('aria-pressed', String(row.dataset.model === selected));
          describe();
        });
        bars.appendChild(button);
      }
      describe();
    }

    function describe() {
      const spec = metrics[metric];
      const score = scores[selected][spec.field];
      const definition = descriptions[selected];
      insight.innerHTML = '<span class="eyebrow"></span><h3></h3><p class="insight-description"></p><p class="insight-value"></p><p class="insight-label"></p><p class="insight-sample"></p>';
      insight.querySelector('.eyebrow').textContent = selected === 'L1' ? 'The benchmark' : 'Selected model';
      insight.querySelector('h3').textContent = definition.name;
      insight.querySelector('.insight-description').textContent = definition.text;
      insight.querySelector('.insight-value').textContent = score == null ? (selected === 'L1' && metric === 'skill' ? 'Benchmark' : 'Not reported') : fmtScore(score);
      insight.querySelector('.insight-label').textContent = spec.label;
      insight.querySelector('.insight-sample').textContent = `${scores[selected].n} scheduled decisions; trained only on earlier meetings.`;
    }

    for (const button of tool.querySelectorAll('[data-metric]')) {
      button.addEventListener('click', () => {
        metric = button.dataset.metric;
        for (const tab of tool.querySelectorAll('[data-metric]')) tab.setAttribute('aria-pressed', String(tab === button));
        draw();
      });
    }
    baseline.addEventListener('change', draw);
    tool.hidden = false;
    draw();
  }).catch(() => {}); // The published score table remains available on failure.

  Promise.all([indexPromise, contextPromise.catch(() => null)]).then(([data, context]) => {
    const select = document.getElementById('meeting-select');
    const period = document.getElementById('period-select');
    const facts = document.getElementById('meeting-facts');
    const svg = document.getElementById('chart');
    let visible = data.documents;
    let selected = visible[visible.length - 1];

    function populate() {
      select.replaceChildren();
      for (const doc of [...visible].reverse()) select.add(new Option(fmtDate(doc.published), doc.doc_id));
      select.value = selected.doc_id;
    }

    function highlight() {
      svg.querySelector('[data-inspector-marker]')?.remove();
      const line = svg.querySelector(':scope > polyline');
      const index = visible.indexOf(selected);
      if (!line || index < 0) return;
      const point = line.getAttribute('points').trim().split(/\s+/)[index];
      if (!point) return;
      const [x, y] = point.split(',');
      svg.appendChild(svgNode('circle', { cx: x, cy: y, r: 5, fill: 'var(--paper)', stroke: 'var(--accent)', 'stroke-width': 2.5, 'data-inspector-marker': '', 'pointer-events': 'none' }));
    }

    function inspect() {
      renderLatest(data, selected);
      const next = data.documents[data.documents.indexOf(selected) + 1];
      const items = [
        ['Dictionary matches', String(selected.abg_hawk + selected.abg_dove), `${selected.abg_hawk} hawkish / ${selected.abg_dove} dovish`],
        ['Vote at this meeting', formatVote(selected.vote), selected.vote ? 'Decision published with these minutes' : 'Vote split not parsed; see the source document'],
        ['Decision that followed', next ? classifyDecision(next.decision) : 'Not yet observed', next ? fmtDate(next.published) : 'Latest published minutes'],
      ];
      facts.replaceChildren();
      for (const [label, value, note] of items) {
        const item = document.createElement('div');
        const dt = document.createElement('dt');
        const dd = document.createElement('dd');
        const small = document.createElement('small');
        dt.textContent = label;
        dd.textContent = value;
        small.textContent = note;
        dd.appendChild(small);
        item.append(dt, dd);
        facts.appendChild(item);
      }
      highlight();
    }

    select.addEventListener('change', () => {
      selected = visible.find(doc => doc.doc_id === select.value);
      inspect();
    });
    period.addEventListener('change', () => {
      if (period.value === 'recent') visible = data.documents.slice(-24);
      else if (period.value === 'post') visible = data.documents.filter(doc => doc.published >= document.getElementById('chart-wrap').dataset.fragilityStart);
      else visible = data.documents;
      if (!visible.includes(selected)) selected = visible[visible.length - 1];
      populate();
      renderChart({ ...data, documents: visible }, context);
      const heading = document.querySelector('#index-history .subhead');
      heading.textContent = `A&BG index, ${fmtMonth(visible[0].published)} to ${fmtMonth(visible[visible.length - 1].published)}`;
      inspect();
    });
    svg.addEventListener('click', event => {
      const line = svg.querySelector(':scope > polyline');
      if (!line) return;
      const bounds = svg.getBoundingClientRect();
      const target = (event.clientX - bounds.left) / bounds.width * svg.viewBox.baseVal.width;
      const points = line.getAttribute('points').trim().split(/\s+/);
      let nearest = 0;
      for (let i = 1; i < points.length; i++) {
        if (Math.abs(Number(points[i].split(',')[0]) - target) < Math.abs(Number(points[nearest].split(',')[0]) - target)) nearest = i;
      }
      selected = visible[nearest];
      select.value = selected.doc_id;
      inspect();
    });
    svg.addEventListener('keydown', event => {
      if (!['ArrowLeft', 'ArrowRight'].includes(event.key)) return;
      event.preventDefault();
      const offset = event.key === 'ArrowLeft' ? -1 : 1;
      selected = visible[Math.max(0, Math.min(visible.length - 1, visible.indexOf(selected) + offset))];
      select.value = selected.doc_id;
      inspect();
    });
    document.addEventListener('mpc-chart-rendered', highlight);
    document.getElementById('explorer-toolbar').hidden = false;
    facts.hidden = false;
    populate();
    inspect();
  }).catch(() => {}); // The latest static reading survives a failed fetch.

  inferencePromise.then(data => {
    const full = data.full_sample.spec3_surprise_on_lagged_index;
    const frag = data.fragility_check_subsample;
    const discrete = data.full_sample.spec2_ordered_logit_lr_test;
    const tests = [
      ['Rate surprises: full history', full.coefficients.lagged_index.p, 'Evidence of an association in the historical sample; not evidence of better forecasts.'],
      ['Rate surprises: later period', frag.results.spec3_surprise_on_lagged_index.coefficients.lagged_index.p, 'Same direction, greater uncertainty. This smaller sample cannot rule out no relationship.'],
      ['Cut, hold or hike', discrete.p_value, 'Adding tone does not significantly improve the model\'s historical fit.'],
    ];
    const container = document.getElementById('evidence-tests');
    for (const [title, p, note] of tests) {
      const item = document.createElement('div');
      item.className = 'evidence-test';
      const h = document.createElement('h4');
      const value = document.createElement('p');
      const description = document.createElement('p');
      h.textContent = title;
      value.className = 'test-p';
      value.textContent = `p = ${p.toFixed(4)}`;
      description.textContent = note;
      item.append(h, value, description);
      container.appendChild(item);
    }
    container.hidden = false;
  }).catch(() => {});

  const steps = document.querySelector('#how-it-works .mechanism-list');
  const example = document.getElementById('scoring-lab');
  const probability = document.getElementById('example-hold');
  function scoreExample() {
    const hold = Number(probability.value) / 100;
    const forecast = { cut: 0, hold, hike: 1 - hold };
    const outcome = example.querySelector('input[name="example-outcome"]:checked').value;
    const errors = Object.entries(forecast).map(([label, p]) => (p - Number(label === outcome)) ** 2);
    document.getElementById('example-probability').textContent = `${probability.value}%`;
    probability.setAttribute('aria-valuetext', `${probability.value}% hold`);
    document.getElementById('example-score').textContent = errors.reduce((sum, value) => sum + value, 0).toFixed(4);
    document.getElementById('example-breakdown').textContent =
      `Cut ${errors[0].toFixed(4)} + hold ${errors[1].toFixed(4)} + hike ${errors[2].toFixed(4)}`;
  }
  example.addEventListener('input', scoreExample);
  example.hidden = false;
  scoreExample();
  const tabs = document.createElement('div');
  tabs.className = 'segmented method-tabs';
  tabs.setAttribute('role', 'tablist');
  tabs.setAttribute('aria-label', 'How the test works');
  const names = ['Language', 'Market', 'Models', 'Scores'];
  const panels = Array.from(steps.children);
  const buttons = names.map((name, i) => {
    const button = document.createElement('button');
    button.type = 'button';
    button.id = `method-tab-${name.toLowerCase()}`;
    button.textContent = name;
    button.setAttribute('role', 'tab');
    button.setAttribute('aria-controls', `method-panel-${name.toLowerCase()}`);
    panels[i].id = `method-panel-${name.toLowerCase()}`;
    panels[i].setAttribute('role', 'tabpanel');
    panels[i].setAttribute('aria-labelledby', button.id);
    panels[i].tabIndex = 0;
    button.addEventListener('click', () => chooseStep(i));
    button.addEventListener('keydown', event => {
      let next;
      if (event.key === 'ArrowRight') next = (i + 1) % names.length;
      else if (event.key === 'ArrowLeft') next = (i + names.length - 1) % names.length;
      else if (event.key === 'Home') next = 0;
      else if (event.key === 'End') next = names.length - 1;
      else return;
      event.preventDefault();
      chooseStep(next);
      buttons[next].focus();
    });
    tabs.appendChild(button);
    return button;
  });
  function chooseStep(index) {
    buttons.forEach((button, i) => {
      button.setAttribute('aria-selected', String(i === index));
      button.tabIndex = i === index ? 0 : -1;
      panels[i].hidden = i !== index;
    });
  }
  steps.before(tabs);
  steps.classList.add('interactive');
  chooseStep(0);

  if ('IntersectionObserver' in window) {
    const links = Array.from(document.querySelectorAll('.reader-nav a[href^="#"]'));
    const observer = new IntersectionObserver(entries => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue;
        for (const link of links) {
          if (link.hash === `#${entry.target.id}`) link.setAttribute('aria-current', 'location');
          else link.removeAttribute('aria-current');
        }
      }
    }, { rootMargin: '-90px 0px -60% 0px' });
    links.forEach(link => observer.observe(document.querySelector(link.hash)));
  }
})();
