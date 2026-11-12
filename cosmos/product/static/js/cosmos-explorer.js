/* COSMOS-AI — globe page controller.
 *
 * Fetches GET /api/globe/objects (geometry, already labelled by cosmos/product/geometry.py) and
 * GET /api/objects/{norad} (the existing object record) and drives the globe, the object list and
 * the selected-object panel. Values are written with text nodes only, never as markup, so no
 * archived string can become HTML. Nothing is computed here: every number shown comes from one of
 * those two responses, and anything a response does not carry is rendered as "not available".
 */
(function (global) {
  'use strict';

  var doc = global.document;

  function $(id) { return doc.getElementById(id); }
  function on(el, ev, fn) { if (el) { el.addEventListener(ev, fn); } }

  function text(el, value) {
    if (!el) { return; }
    el.textContent = (value === null || value === undefined || value === '') ? '—' : String(value);
  }

  function num(value, digits, unit) {
    if (value === null || value === undefined || value === '' || isNaN(Number(value))) { return null; }
    var n = Number(value);
    var s = (digits === 0) ? Math.round(n).toLocaleString('en-GB')
                           : n.toLocaleString('en-GB', { minimumFractionDigits: digits,
                                                         maximumFractionDigits: digits });
    return unit ? s + ' ' + unit : s;
  }

  function row(dl, label, value, title) {
    var dt = doc.createElement('dt');
    dt.textContent = label;
    var dd = doc.createElement('dd');
    if (value === null || value === undefined || value === '') {
      dd.textContent = 'not available';
      dd.className = 'is-unavailable';
    } else {
      dd.textContent = String(value);
    }
    if (title) { dd.title = title; }
    dl.appendChild(dt); dl.appendChild(dd);
  }

  function clear(el) { while (el && el.firstChild) { el.removeChild(el.firstChild); } }

  // Reuses the console's one status vocabulary (.status-pass / partial / blocked / unavailable /
  // abstain / info) so a value never gets a second, competing colour language.
  function badge(label, kind) {
    var span = doc.createElement('span');
    span.className = 'status status-' + (kind || 'info');
    span.textContent = label;
    return span;
  }

  // ----------------------------------------------------------------- state
  var globe = null;
  var scene = { objects: [], geometry_basis: null };
  var selectedNorad = null;
  var config = {};

  function readConfig() {
    var node = $('globe-config');
    if (!node) { return {}; }
    try { return JSON.parse(node.textContent || '{}'); } catch (e) { return {}; }
  }

  // ----------------------------------------------------------------- object list
  function renderList() {
    var list = $('globe-list');
    if (!list) { return; }
    clear(list);
    var q = ($('globe-search') && $('globe-search').value || '').trim().toLowerCase();
    var shown = 0;
    scene.objects.forEach(function (obj) {
      var label = String(obj.norad) + ' ' + String(obj.name || '');
      if (q && label.toLowerCase().indexOf(q) < 0) { return; }
      shown++;
      var item = doc.createElement('button');
      item.type = 'button';
      item.className = 'globe-item' + (obj.norad === selectedNorad ? ' is-active' : '');
      item.setAttribute('data-norad', String(obj.norad));
      var swatch = doc.createElement('i');
      var c = (global.CosmosGlobe && global.CosmosGlobe.CLASS_COLOUR[
        String(obj.object_class || '').toUpperCase()]) || [0.58, 0.68, 0.80];
      swatch.className = 'globe-swatch';
      swatch.style.background = 'rgb(' + c.map(function (v) { return Math.round(v * 255); }).join(',') + ')';
      var main = doc.createElement('span');
      main.className = 'globe-item-main';
      var name = doc.createElement('strong');
      name.textContent = obj.name || ('NORAD ' + obj.norad);
      var meta = doc.createElement('small');
      var band = (obj.derived_elements && obj.derived_elements.altitude_band) || '';
      var p30 = obj.p_reentry_30d;
      meta.textContent = obj.norad + ' · ' + band +
        (p30 === null || p30 === undefined ? '' : ' · p(30 d) ' + Number(p30).toFixed(3));
      main.appendChild(name); main.appendChild(meta);
      item.appendChild(swatch); item.appendChild(main);
      on(item, 'click', function () { select(obj.norad, true); });
      list.appendChild(item);
    });
    text($('globe-list-count'), shown + ' of ' + scene.objects.length + ' drawn');
  }

  // ----------------------------------------------------------------- selected object panel
  function renderGeometry(obj) {
    var dl = $('twin-geometry');
    if (!dl) { return; }
    clear(dl);
    if (!obj) { row(dl, 'selection', null); return; }
    var a = obj.archived_elements || {}, d = obj.derived_elements || {};
    row(dl, 'perigee altitude', num(a.perigee_km, 1, 'km'), 'archived catalogue value');
    row(dl, 'apogee altitude', num(a.apogee_km, 1, 'km'), 'archived catalogue value');
    row(dl, 'inclination', num(a.inclination_deg, 2, '°'), 'archived catalogue value');
    row(dl, 'semi-major axis', num(d.semi_major_axis_km, 1, 'km'), 'derived from perigee and apogee');
    row(dl, 'eccentricity', num(d.eccentricity, 4), 'derived from perigee and apogee');
    row(dl, 'Keplerian period', num(d.period_min, 1, 'min'), 'two-body period from the semi-major axis');
    row(dl, 'altitude band', d.altitude_band, 'descriptive label from the perigee altitude');
    row(dl, 'node, perigee argument, phase', 'screen layout only',
        'the archive publishes none of these; the drawn orientation is a deterministic layout, not a measurement');
  }

  function renderRecord(rec) {
    var panel = $('twin-record');
    if (!panel) { return; }
    clear(panel);
    if (!rec) { return; }

    var head = doc.createElement('div');
    head.className = 'twin-head';
    var h = doc.createElement('h3');
    h.textContent = rec.name ? rec.name : ('NORAD ' + rec.norad);
    var sub = doc.createElement('p');
    sub.className = 'twin-sub';
    sub.textContent = 'NORAD ' + rec.norad + ' · ' + (rec.object_class_label || rec.object_class || '') +
      ' · ' + (rec.regime || '').replace(/_/g, ' ') + ' · snapshot ' + (rec.as_of || '');
    head.appendChild(h); head.appendChild(sub);
    var link = doc.createElement('a');
    link.className = 'btn btn-small';
    link.href = '/objects/' + rec.norad;
    link.textContent = 'full digital twin page';
    head.appendChild(link);
    panel.appendChild(head);

    var lt = rec.lifetime || {}, re = rec.reentry || {}, dp = rec.decision_priority || {},
        tw = rec.twin_state || {}, pr = rec.provenance || {};

    var groups = [
      ['Orbital lifetime', [
        ['median', lt.available ? num(lt.median_days, 1, 'days') : null],
        ['90 % interval', (lt.lo90_days !== null && lt.lo90_days !== undefined)
          ? num(lt.lo90_days, 1) + ' to ' + num(lt.hi90_days, 1, 'days') : null],
        ['horizon relation', lt.horizon_relation && lt.horizon_relation.relation],
        ['cross-horizon coherence', lt.horizon_coherence && lt.horizon_coherence.status],
        ['interval kind', lt.interval_quality && lt.interval_quality.label],
        ['subgroup coverage cue', lt.subgroup_coverage && lt.subgroup_coverage.status]
      ]],
      ['Re-entry assessment', [
        ['p(30 days)', num((re.probability_by_horizon || {})['30d'], 4)],
        ['median time', num(re.median_days, 1, 'days')],
        ['90 % interval', (re.lo90_days !== null && re.lo90_days !== undefined)
          ? num(re.lo90_days, 1) + ' to ' + num(re.hi90_days, 1, 'days') : null],
        ['interval kind', re.interval_quality && re.interval_quality.label],
        ['horizon relation', re.horizon_relation && re.horizon_relation.relation],
        ['model', re.model],
        ['evidence status', re.evidence_status]
      ]],
      ['Decision priority', [
        ['rank', (dp.rank === null || dp.rank === undefined) ? null
          : dp.rank + ' of ' + (dp.ranked_objects === null ? '?' : num(dp.ranked_objects, 0))],
        ['score', num(dp.row && dp.row.priority_score, 3)],
        ['rule', dp.rule && dp.rule.formula],
        ['from run', dp.run_id],
        ['status', dp.status]
      ]],
      ['Twin state and provenance', [
        ['source', tw.source],
        ['fallback used', tw.fallback ? String(!!tw.fallback.used) : null],
        ['snapshot artifact', pr.artifact],
        ['artifact SHA-256', pr.sha256 ? pr.sha256.slice(0, 16) + '…' : null],
        ['model version', pr.model_version && pr.model_version.status],
        ['freshness', rec.freshness && rec.freshness.live === false ? 'archived snapshot, not live' : null]
      ]]
    ];

    groups.forEach(function (group) {
      var box = doc.createElement('div');
      box.className = 'twin-group';
      var title = doc.createElement('h4');
      title.textContent = group[0];
      box.appendChild(title);
      var dl = doc.createElement('dl');
      dl.className = 'kv';
      group[1].forEach(function (pair) { row(dl, pair[0], pair[1]); });
      box.appendChild(dl);
      panel.appendChild(box);
    });

    // Abstentions and unavailable evidence, from the record's own availability list.
    var avail = rec.evidence_availability || [];
    if (avail.length) {
      var box = doc.createElement('div');
      box.className = 'twin-group';
      var title = doc.createElement('h4');
      title.textContent = 'Evidence availability';
      box.appendChild(title);
      var wrap = doc.createElement('div');
      wrap.className = 'token-row';
      avail.forEach(function (item) {
        var status = String(item.status || '').toLowerCase();
        var kind = status === 'implemented' ? 'pass'
          : (status === 'blocked' ? 'blocked'
          : (status === 'unavailable' ? 'unavailable'
          : (status === 'benchmark_only' ? 'partial' : 'abstain')));
        var b = badge((item.module || '') + ': ' + status.replace(/_/g, ' '), kind);
        b.title = item.detail || item.reason || '';
        wrap.appendChild(b);
      });
      box.appendChild(wrap);
      panel.appendChild(box);
    }
  }

  function select(norad, moveList) {
    selectedNorad = norad;
    if (globe) { globe.select(norad); }
    var obj = null;
    scene.objects.forEach(function (o) { if (o.norad === norad) { obj = o; } });
    renderGeometry(obj);
    if (moveList) { renderList(); }
    var panel = $('twin-record');
    if (panel) {
      clear(panel);
      var loading = doc.createElement('p');
      loading.className = 'panel-note';
      loading.textContent = 'reading the archived record for ' + norad + '…';
      panel.appendChild(loading);
    }
    global.fetch('/api/objects/' + encodeURIComponent(norad))
      .then(function (r) { return r.ok ? r.json() : Promise.reject(r.status); })
      .then(function (rec) { if (selectedNorad === norad) { renderRecord(rec); } })
      .catch(function (status) {
        if (!panel) { return; }
        clear(panel);
        var p = doc.createElement('p');
        p.className = 'panel-note';
        p.textContent = 'the object record could not be read (HTTP ' + status + ').';
        panel.appendChild(p);
      });
  }

  // ----------------------------------------------------------------- labels and tooltip
  function positionOverlays() {
    var tip = $('globe-tooltip');
    if (tip && tip.dataset.norad && globe) {
      var s = globe.screenPosition(Number(tip.dataset.norad));
      if (s && !s.occluded) {
        tip.style.left = Math.round(s.x) + 'px';
        tip.style.top = Math.round(s.y) + 'px';
        tip.classList.add('is-visible');
      } else {
        tip.classList.remove('is-visible');
      }
    }
    var tag = $('globe-selected-label');
    if (tag && selectedNorad !== null && globe) {
      var p = globe.screenPosition(selectedNorad);
      if (p && !p.occluded) {
        tag.style.left = Math.round(p.x) + 'px';
        tag.style.top = Math.round(p.y) + 'px';
        tag.classList.add('is-visible');
      } else {
        tag.classList.remove('is-visible');
      }
    }
  }

  function showTooltip(obj) {
    var tip = $('globe-tooltip');
    if (!tip) { return; }
    if (!obj) { tip.classList.remove('is-visible'); delete tip.dataset.norad; return; }
    clear(tip);
    var strong = doc.createElement('strong');
    strong.textContent = obj.name || ('NORAD ' + obj.norad);
    var small = doc.createElement('small');
    var d = obj.derived_elements || {}, a = obj.archived_elements || {};
    small.textContent = 'NORAD ' + obj.norad + ' · ' + (d.altitude_band || '') +
      ' · i ' + num(a.inclination_deg, 1, '°') + ' · T ' + num(d.period_min, 0, 'min');
    tip.appendChild(strong); tip.appendChild(small);
    tip.dataset.norad = String(obj.norad);
  }

  // ----------------------------------------------------------------- scene loading
  function query() {
    if (config.single) {
      return '/api/globe/object/' + encodeURIComponent(config.single);
    }
    var params = [];
    var limit = $('globe-limit');
    params.push('limit=' + encodeURIComponent((limit && limit.value) || config.limit || 120));
    var regime = $('globe-regime');
    if (regime && regime.value) { params.push('regime=' + encodeURIComponent(regime.value)); }
    var klass = $('globe-class');
    if (klass && klass.value) { params.push('object_class=' + encodeURIComponent(klass.value)); }
    if (config.include && config.include.length) {
      params.push('include=' + encodeURIComponent(config.include.join(',')));
    }
    if (config.sort) { params.push('sort=' + encodeURIComponent(config.sort)); }
    return '/api/globe/objects?' + params.join('&');
  }

  function loadScene(selectAfter) {
    var status = $('globe-status');
    text(status, 'reading archived geometry…');
    return global.fetch(query())
      .then(function (r) { return r.ok ? r.json() : Promise.reject(r.status); })
      .then(function (payload) {
        scene = payload;
        if (globe) { globe.setScene(payload); }
        renderList();
        text($('globe-drawn'), payload.object_count);
        text(status, payload.object_count + ' orbits drawn from the ' + payload.as_of +
             ' snapshot' + (payload.excluded_count ? ' · ' + payload.excluded_count +
             ' object(s) have no usable geometry and are not drawn' : ''));
        var excl = $('globe-excluded');
        if (excl) {
          clear(excl);
          (payload.excluded || []).slice(0, 12).forEach(function (e) {
            var li = doc.createElement('li');
            li.textContent = e.norad + ' — ' + e.reason;
            excl.appendChild(li);
          });
        }
        var want = selectAfter !== undefined ? selectAfter
          : (config.select !== undefined ? config.select
          : (payload.objects.length ? payload.objects[0].norad : null));
        if (want !== null && want !== undefined) { select(Number(want), true); }
      })
      .catch(function (err) {
        text(status, 'the geometry endpoint could not be read (' + err + ').');
      });
  }

  // ----------------------------------------------------------------- boot
  function boot() {
    config = readConfig();
    var canvas = $('globe-canvas');
    if (!canvas) { return; }
    globe = global.CosmosGlobe && global.CosmosGlobe.create(canvas, {
      textureUrl: config.texture || '/static/earth-land-mask.png',
      autoRotate: config.autoRotate !== false,
      onSelect: function (obj) { select(obj.norad, true); },
      onHover: showTooltip,
      onFrame: positionOverlays,
      onError: function () { showFallback('WebGL reported an error while starting.'); }
    });
    global.__cosmosGlobe = globe;
    if (!globe) {
      showFallback('This browser or session does not provide WebGL.');
    } else {
      var info = globe.info();
      var el = $('globe-renderer');
      if (el) { text(el, info.version); }
    }
    loadScene();

    on($('globe-reset'), 'click', function () { if (globe) { globe.resetCamera(); } });
    on($('globe-spin'), 'click', function () {
      if (!globe) { return; }
      var on_ = globe.setAutoRotate(!globe.autoRotate());
      $('globe-spin').textContent = on_ ? 'pause camera orbit' : 'resume camera orbit';
      $('globe-spin').setAttribute('aria-pressed', String(on_));
    });
    on($('globe-zoom-in'), 'click', function () { if (globe) { globe.zoom(0.85); } });
    on($('globe-zoom-out'), 'click', function () { if (globe) { globe.zoom(1.18); } });
    on($('globe-search'), 'input', renderList);
    ['globe-limit', 'globe-regime', 'globe-class'].forEach(function (id) {
      on($(id), 'change', function () { loadScene(selectedNorad); });
    });
  }

  function showFallback(reason) {
    var box = $('globe-fallback');
    var canvas = $('globe-canvas');
    if (canvas) { canvas.style.display = 'none'; }
    if (!box) { return; }
    box.hidden = false;
    var why = $('globe-fallback-reason');
    if (why) { text(why, reason); }
  }

  if (doc.readyState === 'loading') { doc.addEventListener('DOMContentLoaded', boot); }
  else { boot(); }

  // Exposed so the screenshot driver (scripts/capture_console_screenshots.py) can assert that the
  // canvas is really drawing, rather than inferring it from a picture.
  global.CosmosExplorer = {
    select: select, reload: loadScene,
    globe: function () { return globe; },
    scene: function () { return scene; },
    diagnostics: function () {
      return {
        webgl: !!globe,
        info: globe ? globe.info() : null,
        objects: (scene.objects || []).length,
        selected: selectedNorad,
        fallbackVisible: !!($('globe-fallback') && !$('globe-fallback').hidden)
      };
    }
  };
})(window);
