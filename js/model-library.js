(function () {
  'use strict';
  if (window.__freevModelLibraryEngineLoaded) return;
  window.__freevModelLibraryEngineLoaded = true;

  var CATALOG = window.FreevModelCatalog || [];
  var TYPE_LABELS = window.FreevModelTypeLabels || {};
  var BASE_MODELS = CATALOG.filter(function (m) { return !m.isVariant; });
  var esc = function (v) { return (typeof escapeHtml === 'function') ? escapeHtml(String(v == null ? '' : v)) : String(v == null ? '' : v); };
  var $ = function (id) { return document.getElementById(id); };

  var PAGE_SIZE = 24;
  var FAVORITES_KEY = 'freev_library_favorites_v2';
  var RUNTIME_KEY = 'freev_library_runtime_v2';
  var INSTALLED_RUNTIME_KEY = 'freev_local_runtime_v2';

  var ACTIVE_TAB = 'px-4 py-2 rounded-full text-xs sm:text-sm font-bold bg-gradient-to-r from-fuchsia-500 to-purple-600 text-white';
  var IDLE_TAB = 'px-4 py-2 rounded-full text-xs sm:text-sm font-bold bg-slate-800 text-gray-400 hover:text-white border border-white/10';
  var ACTIVE_PILL = 'px-3 py-1.5 rounded-full font-bold bg-fuchsia-500 text-white';
  var IDLE_PILL = 'px-3 py-1.5 rounded-full font-bold bg-slate-800 text-gray-400 hover:text-white border border-white/10';

  function loadFavorites() {
    try {
      var raw = JSON.parse(localStorage.getItem(FAVORITES_KEY) || '[]');
      return new Set(Array.isArray(raw) ? raw : []);
    } catch (e) { return new Set(); }
  }
  function saveFavorites() {
    try { localStorage.setItem(FAVORITES_KEY, JSON.stringify(Array.from(state.favorites))); } catch (e) {}
  }

  var state = {
    runtime: (function () { try { return localStorage.getItem(RUNTIME_KEY) === 'lmstudio' ? 'lmstudio' : 'ollama'; } catch (e) { return 'ollama'; } })(),
    installRuntime: 'ollama',
    tab: 'recommended',
    page: 1,
    favorites: loadFavorites(),
    deviceSpecs: null,
    installIndex: null,
    installedRuntime: (function () { try { return localStorage.getItem(INSTALLED_RUNTIME_KEY) === 'lmstudio' ? 'lmstudio' : 'ollama'; } catch (e) { return 'ollama'; } })(),
    installedModels: { ollama: [], lmstudio: [] },
    installedRequestId: 0,
    installedController: null,
    lastFocused: null,
    searchDebounce: null
  };

  function catalogModel(idx) { return CATALOG[idx]; }

  // ── Détection appareil ────────────────────────────────────────────────
  function detectDevice() {
    if (state.deviceSpecs) return state.deviceSpecs;
    var cores = navigator.hardwareConcurrency || null;
    var ramGB = navigator.deviceMemory || null;
    var gpuRenderer = null;
    try {
      var c = document.createElement('canvas');
      var gl = c.getContext('webgl') || c.getContext('experimental-webgl');
      if (gl) { var d = gl.getExtension('WEBGL_debug_renderer_info'); if (d) gpuRenderer = gl.getParameter(d.UNMASKED_RENDERER_WEBGL); }
    } catch (e) {}
    state.deviceSpecs = { cores: cores, ramGB: ramGB, gpuRenderer: gpuRenderer, isMobile: /Mobi|Android|iPhone|iPad/i.test(navigator.userAgent) };
    return state.deviceSpecs;
  }

  function renderDeviceBanner() {
    var el = $('device-info-banner'); if (!el) return;
    var s = detectDevice();
    var ramText = s.ramGB ? (s.ramGB + ' Go' + (s.ramGB >= 8 ? ' ou plus (limite navigateur)' : ' de RAM détectée')) : 'RAM non détectable';
    el.innerHTML = '<div class="flex flex-wrap gap-x-4 gap-y-1">' +
      '<span><i class="fa-solid fa-microchip mr-1 text-fuchsia-400"></i>' + (s.cores ? s.cores + ' cœurs CPU' : 'CPU non détecté') + '</span>' +
      '<span><i class="fa-solid fa-memory mr-1 text-fuchsia-400"></i>' + ramText + '</span>' +
      '<span><i class="fa-solid fa-display mr-1 text-fuchsia-400"></i>' + (s.gpuRenderer ? esc(s.gpuRenderer) : 'GPU non détecté') + '</span>' +
      '</div>' + (s.isMobile ? '<p class="text-yellow-400 mt-1">Mobile détecté : préfère les modèles très légers ou l’IA en ligne.</p>' : '');
  }

  function recommendedModels() {
    var s = detectDevice();
    var cap = s.isMobile ? 4 : (s.ramGB ? (s.ramGB >= 8 ? 16 : s.ramGB * 2) : 8);
    return CATALOG.filter(function (m) { return m.ramGB <= cap && (!m.isVariant || /Q4_K_M|Q5_K_M|Q6_K|Q8_0|MLX 4-bit/.test(m.variant || '')); })
      .sort(function (a, b) { return b.ramGB - a.ramGB; }).slice(0, 30);
  }

  // ── Recherche intelligente & filtres ─────────────────────────────────────
  function normalize(v) { return String(v || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase(); }

  function parseSmartSearch(raw) {
    var q = normalize(raw).trim();
    var tokens = q.match(/(?:[^\s"]+|"[^"]*")+/g) || [];
    var rules = { terms: [], family: null, type: null, quant: null, ramMax: null, ramMin: null, size: null };
    tokens.forEach(function (t) {
      var token = t.replace(/^"|"$/g, '');
      var parts = token.split(':');
      var key = parts[0], value = parts.slice(1).join(':');
      if (value && (key === 'famille' || key === 'family')) { rules.family = normalize(value); return; }
      if (value && (key === 'type' || key === 'usage')) { rules.type = normalize(value); return; }
      if (value && (key === 'quant' || key === 'format')) { rules.quant = normalize(value); return; }
      if (value && (key === 'taille' || key === 'size')) { rules.size = normalize(value); return; }
      var cmp = token.match(/^ram\s*(<=|>=|<|>)\s*(\d+(?:[.,]\d+)?)$/i);
      if (cmp) { var n = Number(cmp[2].replace(',', '.')); if (cmp[1].indexOf('<') !== -1) rules.ramMax = n; else rules.ramMin = n; return; }
      rules.terms.push(normalize(token));
    });
    return rules;
  }

  function modelFormat(m) { return m.isVariant ? (m.format || 'GGUF') : 'official'; }
  function sizeBucket(m) { return m.ramGB <= 4 ? 'tiny' : m.ramGB <= 8 ? 'small' : m.ramGB <= 16 ? 'medium' : 'large'; }
  function haystack(m) { return normalize(m.name + ' ' + m.model + ' ' + m.family + ' ' + m.type + ' ' + m.desc + ' ' + m.tag + ' ' + (m.variant || '')); }

  function matchesModel(m, rules, filters) {
    if (filters.family !== 'all' && m.family !== filters.family) return false;
    if (filters.type !== 'all' && m.type !== filters.type) return false;
    if (filters.quant !== 'all' && modelFormat(m) !== filters.quant) return false;
    if (filters.size !== 'all' && sizeBucket(m) !== filters.size) return false;
    var hay = haystack(m);
    if (rules.family && normalize(m.family).indexOf(rules.family) === -1) return false;
    if (rules.type) {
      var typeLabel = normalize(TYPE_LABELS[m.type] || '');
      if ((normalize(m.type) + ' ' + typeLabel).indexOf(rules.type) === -1) return false;
    }
    if (rules.quant && (normalize(modelFormat(m)) + ' ' + hay).indexOf(rules.quant) === -1) return false;
    if (rules.size && normalize(sizeBucket(m)).indexOf(rules.size) === -1 && normalize(m.tag).indexOf(rules.size) === -1) return false;
    if (rules.ramMax !== null && m.ramGB > rules.ramMax) return false;
    if (rules.ramMin !== null && m.ramGB < rules.ramMin) return false;
    return rules.terms.every(function (t) { return hay.indexOf(t) !== -1; });
  }

  function scoreModel(m, rules) {
    var hay = haystack(m);
    var score = 0;
    rules.terms.forEach(function (t) {
      if (hay.indexOf(t) !== -1) score += 10;
      if (normalize(m.name).indexOf(t) === 0) score += 8;
      if (normalize(m.family) === t) score += 12;
    });
    return score + (m.popular ? 2 : 0) + (m.recent ? 1 : 0);
  }

  function sortModels(list, sort, rules) {
    return list.sort(function (a, b) {
      if (sort === 'ramAsc') return a.ramGB - b.ramGB || a.name.localeCompare(b.name);
      if (sort === 'ramDesc') return b.ramGB - a.ramGB || a.name.localeCompare(b.name);
      if (sort === 'diskAsc') return a.sizeGB - b.sizeGB || a.name.localeCompare(b.name);
      if (sort === 'name') return a.name.localeCompare(b.name, 'fr');
      if (sort === 'family') return a.family.localeCompare(b.family, 'fr') || a.name.localeCompare(b.name, 'fr');
      return scoreModel(b, rules) - scoreModel(a, rules) || a.ramGB - b.ramGB || a.name.localeCompare(b.name, 'fr');
    });
  }

  function currentFilters() {
    return {
      family: ($('model-library-family') || {}).value || 'all',
      type: ($('model-library-type') || {}).value || 'all',
      quant: ($('model-library-quant') || {}).value || 'all',
      size: ($('model-library-size') || {}).value || 'all',
      sort: ($('model-library-sort') || {}).value || 'relevance'
    };
  }

  function modelsForTab() {
    if (state.tab === 'recommended') return recommendedModels();
    if (state.tab === 'popular') return CATALOG.filter(function (m) { return m.popular; });
    if (state.tab === 'recent') return CATALOG.filter(function (m) { return m.recent; });
    if (state.tab === 'favorites') return CATALOG.filter(function (m, i) { return state.favorites.has(i); });
    return CATALOG;
  }

  function populateFamilyFilter() {
    var select = $('model-library-family');
    if (!select || select.dataset.ready) return;
    var families = Array.from(new Set(BASE_MODELS.map(function (m) { return m.family; }))).sort(function (a, b) { return a.localeCompare(b, 'fr'); });
    families.forEach(function (f) { select.insertAdjacentHTML('beforeend', '<option value="' + esc(f) + '">' + esc(f) + '</option>'); });
    select.dataset.ready = '1';
  }

  // ── Commandes selon le runtime sélectionné ───────────────────────────────
  function commandFor(m, runtime) {
    if (runtime === 'lmstudio') return 'lms get "' + String(m.baseModelName || m.name).replace(/"/g, '') + '"';
    return 'ollama pull ' + m.model;
  }
  function commandLabel(runtime) { return runtime === 'lmstudio' ? 'COMMANDE LM STUDIO' : 'COMMANDE OLLAMA'; }
  function linkFor(m, runtime) {
    if (runtime === 'ollama' && !m.isVariant) return 'https://ollama.com/library/' + encodeURIComponent(String(m.model).split(':')[0].toLowerCase());
    return 'https://huggingface.co/models?search=' + encodeURIComponent(m.baseModelName || m.name);
  }
  function linkLabel(m, runtime) { return (runtime === 'ollama' && !m.isVariant) ? 'Voir la fiche Ollama' : 'Rechercher sur Hugging Face'; }

  var FORMAT_BADGE = {
    official: 'bg-emerald-500/10 text-emerald-200 border-emerald-500/20',
    GGUF: 'bg-cyan-500/10 text-cyan-200 border-cyan-500/20',
    AWQ: 'bg-amber-500/10 text-amber-200 border-amber-500/20',
    GPTQ: 'bg-orange-500/10 text-orange-200 border-orange-500/20',
    EXL2: 'bg-indigo-500/10 text-indigo-200 border-indigo-500/20',
    MLX: 'bg-purple-500/10 text-purple-200 border-purple-500/20',
    BF16: 'bg-rose-500/10 text-rose-200 border-rose-500/20'
  };

  function card(m, idx) {
    var official = !m.isVariant;
    var format = modelFormat(m);
    var isFav = state.favorites.has(idx);
    var command = commandFor(m, state.runtime);
    var link = linkFor(m, state.runtime);
    var badgeColor = FORMAT_BADGE[format] || 'bg-white/5 text-gray-300 border-white/10';
    return (
      '<article class="p-4 bg-slate-800/70 rounded-xl border border-white/10 hover:border-fuchsia-400/50 transition-all flex flex-col shadow-lg shadow-black/10">' +
        '<div class="flex justify-between gap-2">' +
          '<div class="min-w-0"><p class="text-[10px] uppercase tracking-wider text-fuchsia-300">' + esc(m.family) + ' · ' + esc(TYPE_LABELS[m.type] || m.type) + '</p>' +
          '<h4 class="font-bold text-white text-sm mt-0.5 truncate" title="' + esc(m.name) + '">' + esc(m.name) + '</h4></div>' +
          '<button type="button" data-action="favorite" data-index="' + idx + '" title="' + (isFav ? 'Retirer des favoris' : 'Ajouter aux favoris') + '" class="shrink-0 h-7 w-7 rounded-full flex items-center justify-center ' + (isFav ? 'text-amber-300' : 'text-gray-500 hover:text-amber-200') + '"><i class="fa-solid fa-star"></i></button>' +
        '</div>' +
        '<div class="mt-2 flex gap-1 flex-wrap">' +
          '<span class="text-[9px] px-1.5 py-0.5 rounded border ' + badgeColor + '">' + esc(official ? 'OFFICIEL' : format) + '</span>' +
          (m.popular ? '<span class="text-[9px] px-1.5 py-0.5 rounded bg-orange-400/10 text-orange-200">POPULAIRE</span>' : '') +
          (m.recent ? '<span class="text-[9px] px-1.5 py-0.5 rounded bg-cyan-400/10 text-cyan-200">NOUVEAU</span>' : '') +
        '</div>' +
        '<div class="mt-2 rounded-lg border border-cyan-400/10 bg-black/20 px-2 py-1.5">' +
          '<p class="text-[9px] text-gray-500 mb-0.5">' + commandLabel(state.runtime) + '</p>' +
          '<code class="block text-[11px] text-cyan-300 overflow-x-auto">' + esc(command) + '</code>' +
        '</div>' +
        (m.isVariant ? '<p class="mt-1 text-[10px] text-amber-300"><i class="fa-solid fa-cube mr-1"></i>' + esc(m.variant) + '</p>' : '') +
        '<p class="text-xs text-gray-400 flex-grow mt-2 mb-3 line-clamp-3">' + esc(m.desc) + '</p>' +
        '<div class="flex items-center gap-3 text-[10px] text-gray-500 mb-3">' +
          '<span><i class="fa-solid fa-hard-drive mr-1"></i>~' + m.sizeGB + ' Go</span>' +
          '<span><i class="fa-solid fa-memory mr-1"></i>~' + m.ramGB + ' Go RAM</span>' +
        '</div>' +
        '<div class="grid grid-cols-2 gap-2 mt-auto">' +
          '<button type="button" data-action="install" data-index="' + idx + '" class="px-3 py-2 bg-fuchsia-500 hover:bg-fuchsia-400 rounded-lg text-xs font-bold text-white transition-all"><i class="fa-solid fa-download mr-1"></i> Installer</button>' +
          '<button type="button" data-action="use" data-index="' + idx + '" class="px-3 py-2 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg text-xs font-bold text-gray-200 transition-all"><i class="fa-solid fa-sliders mr-1"></i> Configurer</button>' +
        '</div>' +
        '<a href="' + esc(link) + '" target="_blank" rel="noopener noreferrer" class="mt-2 text-center text-[10px] text-fuchsia-300 hover:text-fuchsia-200"><i class="fa-solid fa-arrow-up-right-from-square mr-1"></i>' + esc(linkLabel(m, state.runtime)) + '</a>' +
      '</article>'
    );
  }

  function render() {
    var grid = $('model-explorer-grid'); if (!grid) return;
    var searchInput = $('model-library-search');
    var raw = searchInput ? searchInput.value : '';
    var rules = parseSmartSearch(raw);
    var filters = currentFilters();
    var list = modelsForTab().filter(function (m) { return matchesModel(m, rules, filters); });
    list = sortModels(list, filters.sort, rules);
    var total = list.length;
    var totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
    if (state.page > totalPages) state.page = totalPages;
    var start = (state.page - 1) * PAGE_SIZE;
    var visible = list.slice(start, start + PAGE_SIZE);

    var countEl = $('model-library-count');
    if (countEl) countEl.textContent = total.toLocaleString('fr-FR') + ' résultat' + (total > 1 ? 's' : '') + ' · ' + CATALOG.length.toLocaleString('fr-FR') + ' configurations consultables';
    var pageInfo = $('model-library-page-info');
    if (pageInfo) pageInfo.textContent = total ? ('Résultats ' + (start + 1) + '–' + Math.min(start + PAGE_SIZE, total) + ' sur ' + total.toLocaleString('fr-FR') + ' · page ' + state.page + '/' + totalPages) : 'Aucun résultat';
    var prev = $('model-page-prev'), next = $('model-page-next');
    if (prev) prev.disabled = state.page <= 1 || !total;
    if (next) next.disabled = state.page >= totalPages || !total;

    if (!total) {
      var emptyHint = state.tab === 'favorites'
        ? 'Aucun favori pour le moment. Clique sur l’étoile d’un modèle pour l’ajouter ici.'
        : 'Aucun modèle avec ces filtres. Essaie <strong class="text-fuchsia-300">famille:qwen</strong>, <strong class="text-fuchsia-300">type:code</strong>, <strong class="text-fuchsia-300">ram&lt;=8</strong>, ou réinitialise les filtres.';
      grid.innerHTML = '<p class="text-gray-500 text-sm col-span-full rounded-xl border border-white/10 bg-slate-800/40 p-5">' + emptyHint + '</p>';
      return;
    }
    grid.innerHTML = visible.map(function (m) { return card(m, CATALOG.indexOf(m)); }).join('');
  }

  // ── Suggestions de recherche ──────────────────────────────────────────
  function searchSuggestions(raw) {
    if (!raw || !raw.trim()) return [];
    var rules = parseSmartSearch(raw);
    var seen = {}, out = [];
    BASE_MODELS.forEach(function (m) {
      var h = normalize(m.name + ' ' + m.family + ' ' + m.type);
      var matches = (rules.terms.length && rules.terms.every(function (t) { return h.indexOf(t) !== -1; })) ||
        normalize(m.family).indexOf(normalize(raw)) !== -1 || normalize(m.name).indexOf(normalize(raw)) !== -1;
      if (matches) {
        var label = m.name + ' · ' + m.family;
        if (!seen[label]) { seen[label] = true; out.push({ label: label, value: 'famille:' + m.family, hint: 'Filtrer la famille ' + m.family }); }
      }
    });
    ['general', 'reasoning', 'code', 'vision', 'embedding', 'translate', 'audio'].forEach(function (type) {
      var label = TYPE_LABELS[type];
      if (normalize(label).indexOf(normalize(raw)) !== -1 || normalize(type).indexOf(normalize(raw)) !== -1) {
        out.push({ label: 'Usage : ' + label, value: 'type:' + type, hint: 'Filtrer par usage' });
      }
    });
    ['Q4_K_M', 'Q5_K_M', 'Q6_K', 'Q8_0', 'AWQ', 'GPTQ', 'EXL2', 'MLX'].forEach(function (q) {
      if (normalize(q).indexOf(normalize(raw)) !== -1) out.push({ label: 'Format : ' + q, value: 'quant:' + q, hint: 'Filtrer les formats' });
    });
    return out.slice(0, 8);
  }

  function renderSuggestions() {
    var input = $('model-library-search'), box = $('model-search-suggestions');
    if (!input || !box) return;
    var suggestions = searchSuggestions(input.value);
    if (!suggestions.length) { box.classList.add('hidden'); box.innerHTML = ''; return; }
    box.innerHTML = suggestions.map(function (s) {
      return '<button type="button" data-suggestion="' + esc(s.value) + '" class="w-full text-left px-3 py-2 rounded-lg hover:bg-white/10 flex items-center justify-between gap-3"><span class="text-xs text-white">' + esc(s.label) + '</span><span class="text-[10px] text-gray-500">' + esc(s.hint) + '</span></button>';
    }).join('');
    box.classList.remove('hidden');
  }

  // ── Copie presse-papiers (avec repli) ────────────────────────────────────
  function copyText(text, btn) {
    function done() {
      if (!btn) return;
      var original = btn.dataset.originalHtml || btn.innerHTML;
      btn.dataset.originalHtml = original;
      btn.innerHTML = '<i class="fa-solid fa-check mr-1"></i> Copié';
      setTimeout(function () { btn.innerHTML = btn.dataset.originalHtml; }, 1600);
    }
    function fallback() {
      var area = document.createElement('textarea');
      area.value = text; area.style.position = 'fixed'; area.style.opacity = '0';
      document.body.appendChild(area); area.select();
      try { document.execCommand('copy'); done(); } catch (e) { window.prompt('Copie cette commande :', text); }
      area.remove();
    }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(done).catch(fallback);
    } else fallback();
  }

  // ── Actions principales de l'explorateur ─────────────────────────────────
  function refreshExplorerRuntimeButtons() {
    var o = $('explorer-runtime-ollama'), l = $('explorer-runtime-lmstudio');
    if (o) o.className = state.runtime === 'ollama' ? ACTIVE_PILL : IDLE_PILL;
    if (l) l.className = state.runtime === 'lmstudio' ? ACTIVE_PILL : IDLE_PILL;
  }

  function openModelExplorer() {
    var modal = $('model-explorer-modal'); if (!modal) return;
    state.lastFocused = document.activeElement;
    modal.classList.remove('hidden');
    populateFamilyFilter();
    renderDeviceBanner();
    refreshExplorerRuntimeButtons();
    selectExplorerTab(state.tab || 'recommended');
    var input = $('model-library-search');
    if (input) setTimeout(function () { input.focus(); }, 60);
  }
  function closeModelExplorer() {
    var modal = $('model-explorer-modal'); if (!modal) return;
    modal.classList.add('hidden');
    var box = $('model-search-suggestions'); if (box) box.classList.add('hidden');
    if (state.lastFocused && state.lastFocused.focus) { try { state.lastFocused.focus(); } catch (e) {} }
  }
  function setExplorerRuntime(runtime) {
    state.runtime = runtime === 'lmstudio' ? 'lmstudio' : 'ollama';
    try { localStorage.setItem(RUNTIME_KEY, state.runtime); } catch (e) {}
    refreshExplorerRuntimeButtons();
    render();
  }
  function selectExplorerTab(tab) {
    state.tab = tab; state.page = 1;
    ['recommended', 'all', 'popular', 'recent', 'favorites'].forEach(function (t) {
      var b = $('explorer-tab-' + t);
      if (b) b.className = t === tab ? ACTIVE_TAB : IDLE_TAB;
    });
    render();
  }
  function handleModelSearch() {
    renderSuggestions();
    clearTimeout(state.searchDebounce);
    state.searchDebounce = setTimeout(function () { state.page = 1; render(); }, 120);
  }
  function handleModelSearchKey(ev) {
    var box = $('model-search-suggestions');
    if (ev.key === 'Enter') {
      var first = box && box.querySelector('[data-suggestion]');
      if (first && !box.classList.contains('hidden')) { ev.preventDefault(); applyModelSearch(first.dataset.suggestion); }
    }
    if (ev.key === 'Escape' && box) box.classList.add('hidden');
  }
  function applyModelSearch(value) {
    var input = $('model-library-search'); if (input) input.value = value;
    var box = $('model-search-suggestions'); if (box) box.classList.add('hidden');
    state.page = 1; render();
  }
  function clearModelSearchOnly() {
    var input = $('model-library-search'); if (input) { input.value = ''; input.focus(); }
    var box = $('model-search-suggestions'); if (box) box.classList.add('hidden');
    state.page = 1; render();
  }
  function clearModelFilters() {
    ['model-library-search', 'model-library-family', 'model-library-type', 'model-library-quant', 'model-library-size', 'model-library-sort'].forEach(function (id) {
      var el = $(id); if (!el) return;
      el.value = id === 'model-library-search' ? '' : (id === 'model-library-sort' ? 'relevance' : 'all');
    });
    var box = $('model-search-suggestions'); if (box) box.classList.add('hidden');
    state.page = 1; selectExplorerTab('recommended');
  }
  function changeModelPage(delta) {
    state.page = Math.max(1, state.page + delta);
    render();
    var grid = $('model-explorer-grid'); if (grid) grid.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
  function toggleFavorite(idx) {
    if (state.favorites.has(idx)) state.favorites.delete(idx); else state.favorites.add(idx);
    saveFavorites();
    render();
  }
  function useModel(idx) {
    var m = catalogModel(idx); if (!m) return;
    var presetSel = $('custom-provider-preset');
    if (presetSel) { presetSel.value = state.runtime; if (typeof window.applyCustomPreset === 'function') window.applyCustomPreset(); }
    var nameInput = $('custom-model-name');
    if (nameInput) nameInput.value = state.runtime === 'lmstudio' ? (m.baseModelName || m.name) : m.model;
    var hint = $('local-model-cmd-hint');
    if (hint) hint.textContent = commandFor(m, state.runtime);
    closeModelExplorer();
    closeInstallGuide();
    if (typeof window.setAiMode === 'function') window.setAiMode('custom');
    var panel = $('api-settings-custom');
    if (panel) { panel.classList.remove('hidden'); panel.scrollIntoView({ behavior: 'smooth', block: 'center' }); }
  }
  function toggleInstallQuickGuide() {
    var guide = $('install-quick-guide'), icon = $('install-quick-guide-icon');
    var btn = document.querySelector('[aria-controls="install-quick-guide"]');
    if (!guide) return;
    guide.classList.toggle('hidden');
    var expanded = !guide.classList.contains('hidden');
    if (icon) icon.className = expanded ? 'fa-solid fa-chevron-up text-xs text-fuchsia-300' : 'fa-solid fa-chevron-down text-xs text-fuchsia-300';
    if (btn) btn.setAttribute('aria-expanded', String(expanded));
  }

  // ── Guide d'installation ─────────────────────────────────────────────────
  function ollamaLibraryUrl(model) { return 'https://ollama.com/library/' + encodeURIComponent(String(model || '').split(':')[0].trim().toLowerCase()); }
  function hfSearchUrl(m) { return 'https://huggingface.co/models?search=' + encodeURIComponent(((m.baseModelName || m.name) + ' ' + (m.format || modelFormat(m)) + ' ' + (m.variant || '')).trim()); }

  function refreshInstallRuntimeButtons() {
    var o = $('install-guide-ollama'), l = $('install-guide-lmstudio');
    var active = 'rounded-xl px-3 py-2 text-xs font-bold bg-fuchsia-500 text-white';
    var idle = 'rounded-xl px-3 py-2 text-xs font-bold border border-white/10 bg-slate-800 text-gray-300 hover:text-white';
    if (o) o.className = state.installRuntime === 'ollama' ? active : idle;
    if (l) l.className = state.installRuntime === 'lmstudio' ? active : idle;
  }

  function renderInstallGuide() {
    var m = catalogModel(state.installIndex); if (!m) return;
    var title = $('install-guide-title'), meta = $('install-guide-meta'), content = $('install-guide-content');
    if (title) title.textContent = m.name;
    if (meta) meta.textContent = m.family + ' · ' + (TYPE_LABELS[m.type] || m.type) + ' · environ ' + m.sizeGB + ' Go disque · ' + m.ramGB + ' Go RAM conseillés';
    if (!content) return;
    if (state.installRuntime === 'ollama') {
      var command = 'ollama run ' + m.model;
      content.innerHTML =
        '<div class="space-y-4">' +
          '<div class="rounded-xl border border-cyan-400/20 bg-cyan-500/5 p-4">' +
            '<p class="text-sm font-bold text-white"><i class="fa-solid fa-terminal text-cyan-300 mr-2"></i>Terminal — Windows, macOS, Linux</p>' +
            '<p class="mt-1 text-xs text-gray-400">Ollama télécharge automatiquement le modèle puis ouvre une discussion.</p>' +
            '<div class="mt-3 flex flex-col sm:flex-row gap-2">' +
              '<code class="flex-1 rounded-lg bg-black/40 px-3 py-2 text-sm text-cyan-300 overflow-x-auto">' + esc(command) + '</code>' +
              '<button type="button" data-copy="' + esc(command) + '" class="rounded-lg px-3 py-2 text-xs font-bold bg-cyan-400 text-slate-950 hover:bg-cyan-300"><i class="fa-regular fa-copy mr-1"></i> Copier</button>' +
            '</div>' +
          '</div>' +
          '<ol class="space-y-2 text-xs text-gray-300 list-decimal list-inside">' +
            '<li>Vérifie qu’Ollama est installé et ouvert.</li><li>Ouvre ton terminal.</li><li>Colle la commande et appuie sur Entrée.</li><li>Après le téléchargement, écris ton premier message.</li>' +
          '</ol>' +
          (m.isVariant ? '<div class="rounded-lg border border-amber-400/20 bg-amber-500/5 p-3 text-xs text-amber-100"><i class="fa-solid fa-circle-info mr-1"></i>Variante locale <strong>' + esc(m.variant || '') + '</strong> : Ollama peut utiliser un tag différent. Vérifie la fiche avant le téléchargement.</div>' : '') +
          '<div class="flex flex-wrap gap-2">' +
            '<a target="_blank" rel="noopener noreferrer" href="' + esc(ollamaLibraryUrl(m.model)) + '" class="rounded-lg px-3 py-2 text-xs font-bold border border-fuchsia-400/30 text-fuchsia-200 hover:bg-fuchsia-500/10"><i class="fa-solid fa-arrow-up-right-from-square mr-1"></i> Voir sur Ollama</a>' +
            '<button type="button" data-use="1" class="rounded-lg px-3 py-2 text-xs font-bold bg-fuchsia-500 text-white hover:bg-fuchsia-400"><i class="fa-solid fa-plug mr-1"></i> Configurer Freev</button>' +
          '</div>' +
        '</div>';
    } else {
      var url = hfSearchUrl(m);
      var lmsCmd = 'lms get "' + String(m.baseModelName || m.name).replace(/"/g, '') + '"';
      content.innerHTML =
        '<div class="space-y-4">' +
          '<div class="rounded-xl border border-amber-400/20 bg-amber-500/5 p-4">' +
            '<p class="text-sm font-bold text-white"><i class="fa-solid fa-window-maximize text-amber-300 mr-2"></i>Installation dans LM Studio</p>' +
            '<p class="mt-1 text-xs text-gray-400">LM Studio télécharge les modèles depuis Hugging Face. Sur Windows, commence en GGUF Q4_K_M.</p>' +
            '<div class="mt-3 flex flex-col sm:flex-row gap-2">' +
              '<code class="flex-1 rounded-lg bg-black/40 px-3 py-2 text-sm text-amber-200 overflow-x-auto">' + esc(lmsCmd) + '</code>' +
              '<button type="button" data-copy="' + esc(lmsCmd) + '" class="rounded-lg px-3 py-2 text-xs font-bold bg-amber-300 text-slate-950 hover:bg-amber-200"><i class="fa-regular fa-copy mr-1"></i> Copier</button>' +
            '</div>' +
            '<div class="mt-3 flex flex-wrap gap-2">' +
              '<a target="_blank" rel="noopener noreferrer" href="' + esc(url) + '" class="rounded-lg px-3 py-2 text-xs font-bold border border-amber-300/40 text-amber-100 hover:bg-amber-500/10"><i class="fa-solid fa-magnifying-glass mr-1"></i> Ouvrir Hugging Face</a>' +
            '</div>' +
          '</div>' +
          '<ol class="space-y-2 text-xs text-gray-300 list-decimal list-inside">' +
            '<li>Dans LM Studio, ouvre <strong class="text-white">Discover</strong> (ou utilise <code>lms get</code> dans un terminal).</li>' +
            '<li>Cherche le nom du modèle ou colle le lien Hugging Face.</li>' +
            '<li>Choisis un fichier <strong class="text-fuchsia-200">GGUF Q4_K_M</strong> adapté à ta RAM (ou <strong class="text-white">MLX</strong> sur Mac Apple Silicon).</li>' +
            '<li>Télécharge-le puis charge-le dans l’onglet Chat.</li>' +
          '</ol>' +
          '<div class="flex flex-wrap gap-2"><button type="button" data-use="1" class="rounded-lg px-3 py-2 text-xs font-bold bg-fuchsia-500 text-white hover:bg-fuchsia-400"><i class="fa-solid fa-plug mr-1"></i> Configurer Freev avec ce modèle</button></div>' +
        '</div>';
    }
  }
  function openInstallGuide(idx) {
    if (!catalogModel(idx)) return;
    state.installIndex = idx;
    state.installRuntime = state.runtime;
    var modal = $('model-install-modal'); if (modal) modal.classList.remove('hidden');
    refreshInstallRuntimeButtons();
    renderInstallGuide();
  }
  function closeInstallGuide() {
    var modal = $('model-install-modal'); if (modal) modal.classList.add('hidden');
  }
  function setInstallRuntime(runtime) {
    state.installRuntime = runtime === 'lmstudio' ? 'lmstudio' : 'ollama';
    refreshInstallRuntimeButtons();
    renderInstallGuide();
  }

  // ── Détection des modèles installés (Ollama / LM Studio, localhost only) ──
  function endpointFor(runtime) { return runtime === 'ollama' ? 'http://localhost:11434/v1' : 'http://localhost:1234/v1'; }
  function bytesLabel(n) {
    var v = Number(n);
    return (isFinite(v) && v > 0) ? (v / 1024 / 1024 / 1024).toLocaleString('fr-FR', { maximumFractionDigits: 2 }) + ' Go' : 'Taille inconnue';
  }
  function fetchJSON(url, controller, timeout) {
    timeout = timeout || 4500;
    var timer = setTimeout(function () { try { controller.abort(); } catch (e) {} }, timeout);
    return fetch(url, { signal: controller.signal, headers: { Accept: 'application/json' } })
      .then(function (res) { clearTimeout(timer); if (!res.ok) throw new Error('HTTP ' + res.status); return res.json(); })
      .catch(function (err) { clearTimeout(timer); throw err; });
  }
  function tryEndpoints(endpoints, normalizeFn, controller) {
    var i = 0;
    function attempt() {
      if (i >= endpoints.length) return Promise.reject(new Error('service local non détecté'));
      var url = endpoints[i]; i += 1;
      return fetchJSON(url, controller).then(normalizeFn).catch(function (err) {
        if (controller.signal.aborted) throw err;
        return attempt();
      });
    }
    return attempt();
  }
  function normalizeOllamaModels(data) {
    var list = Array.isArray(data && data.models) ? data.models : [];
    return list.map(function (m) {
      return { id: String(m.name || m.model || ''), name: String(m.name || m.model || ''), runtime: 'ollama', size: Number(m.size || 0), format: String((m.details && (m.details.format || m.details.family)) || 'Modèle Ollama') };
    }).filter(function (m) { return m.id; });
  }
  function normalizeLMStudioModels(data) {
    var raw = Array.isArray(data && data.data) ? data.data : (Array.isArray(data) ? data : []);
    var seen = {}, out = [];
    raw.forEach(function (m) {
      var id = String(m.id || m.model_key || m.key || m.name || '');
      if (!id || seen[id]) return;
      seen[id] = true;
      out.push({ id: id, name: id, runtime: 'lmstudio', size: Number(m.size_bytes || m.size || 0), format: String(m.format || m.architecture || m.publisher || 'Modèle LM Studio') });
    });
    return out;
  }
  function fetchOllamaModels(controller) {
    return tryEndpoints(['http://localhost:11434/api/tags', 'http://127.0.0.1:11434/api/tags'], normalizeOllamaModels, controller);
  }
  function fetchLMStudioModels(controller) {
    return tryEndpoints(['http://localhost:1234/api/v0/models', 'http://localhost:1234/v1/models', 'http://127.0.0.1:1234/api/v0/models', 'http://127.0.0.1:1234/v1/models'], normalizeLMStudioModels, controller);
  }
  function setInstalledStatus(message, tone) {
    var el = $('freev-local-status'); if (!el) return;
    var styles = { error: 'border-red-400/25 bg-red-500/5 text-red-100', ok: 'border-emerald-400/25 bg-emerald-500/5 text-emerald-50', warn: 'border-amber-400/25 bg-amber-500/5 text-amber-50', normal: 'border-white/10 bg-slate-900/70 text-gray-300' };
    el.className = 'rounded-xl border p-3 text-xs ' + (styles[tone] || styles.normal);
    el.innerHTML = message;
  }
  function refreshInstalledRuntimeButtons() {
    var a = $('freev-local-runtime-ollama'), b = $('freev-local-runtime-lmstudio');
    var active = 'rounded-xl px-3 py-2 text-xs font-bold bg-emerald-500 text-slate-950';
    var idle = 'rounded-xl border border-white/10 bg-slate-800 px-3 py-2 text-xs font-bold text-gray-300 hover:text-white';
    if (a) a.className = state.installedRuntime === 'ollama' ? active : idle;
    if (b) b.className = state.installedRuntime === 'lmstudio' ? active : idle;
  }
  function visibleInstalledModels() {
    var q = String(($('freev-local-search') || {}).value || '').trim().toLocaleLowerCase('fr');
    var list = (state.installedModels[state.installedRuntime] || []).slice().sort(function (a, b) { return a.name.localeCompare(b.name, 'fr', { numeric: true }); });
    return q ? list.filter(function (m) { return (m.name + ' ' + m.format).toLocaleLowerCase('fr').indexOf(q) !== -1; }) : list;
  }
  function renderInstalledList() {
    var host = $('freev-installed-list'); if (!host) return;
    var all = state.installedModels[state.installedRuntime] || [];
    var list = visibleInstalledModels();
    if (!all.length) {
      host.innerHTML = '<div class="rounded-xl border border-dashed border-white/10 p-6 text-center text-sm text-gray-500"><i class="fa-solid fa-box-open mb-2 text-lg block"></i>Aucun modèle détecté. Clique sur <strong class="text-gray-300">Actualiser</strong>.</div>';
      return;
    }
    if (!list.length) {
      host.innerHTML = '<div class="rounded-xl border border-dashed border-white/10 p-5 text-center text-sm text-gray-500">Aucun modèle ne correspond à cette recherche.</div>';
      return;
    }
    host.innerHTML = list.map(function (m) {
      return '<article class="rounded-xl border border-white/10 bg-slate-900/70 p-3 flex items-center justify-between gap-3">' +
        '<div class="min-w-0"><p class="truncate font-bold text-sm text-white"><i class="fa-solid ' + (m.runtime === 'ollama' ? 'fa-terminal text-cyan-300' : 'fa-window-maximize text-amber-300') + ' mr-2"></i>' + esc(m.name) + '</p>' +
        '<p class="mt-1 text-[11px] text-gray-500">' + (m.runtime === 'ollama' ? 'Ollama' : 'LM Studio') + ' · ' + esc(m.format) + ' · ' + bytesLabel(m.size) + '</p></div>' +
        '<button type="button" data-select-id="' + esc(m.id) + '" class="shrink-0 rounded-lg bg-fuchsia-500 px-3 py-2 text-xs font-bold text-white hover:bg-fuchsia-400"><i class="fa-solid fa-plug mr-1"></i> Utiliser</button>' +
      '</article>';
    }).join('');
  }
  function selectInstalledModel(id) {
    var list = state.installedModels[state.installedRuntime] || [];
    var m = null;
    for (var i = 0; i < list.length; i++) { if (list[i].id === id) { m = list[i]; break; } }
    if (!m) return;
    var payload = { id: m.id, name: m.name, runtime: m.runtime, endpoint: endpointFor(m.runtime), selectedAt: new Date().toISOString() };
    try { localStorage.setItem('freev_active_local_model', JSON.stringify(payload)); } catch (e) {}
    var presetSel = $('custom-provider-preset');
    if (presetSel) { presetSel.value = m.runtime; if (typeof window.applyCustomPreset === 'function') window.applyCustomPreset(); }
    var nameInput = $('custom-model-name'); if (nameInput) nameInput.value = m.id;
    var hint = $('local-model-cmd-hint'); if (hint) hint.textContent = m.id;
    var selectedBox = $('freev-installed-selected');
    if (selectedBox) { selectedBox.classList.remove('hidden'); selectedBox.innerHTML = '<i class="fa-solid fa-circle-check mr-1 text-fuchsia-300"></i><strong>' + esc(m.name) + '</strong> est connecté à Freev via <strong>' + (m.runtime === 'ollama' ? 'Ollama' : 'LM Studio') + '</strong>.'; }
    setInstalledStatus('<strong>' + esc(m.name) + '</strong> est maintenant configuré. Ferme cette fenêtre pour discuter.', 'ok');
  }
  function openInstalledModels() {
    var modal = $('freev-installed-models-modal'); if (!modal) return;
    modal.classList.remove('hidden');
    refreshInstalledRuntimeButtons();
    renderInstalledList();
    refreshInstalledModels();
  }
  function closeInstalledModels() {
    var modal = $('freev-installed-models-modal'); if (modal) modal.classList.add('hidden');
    if (state.installedController) { try { state.installedController.abort(); } catch (e) {} }
  }
  function setInstalledRuntime(runtime) {
    state.installedRuntime = runtime === 'lmstudio' ? 'lmstudio' : 'ollama';
    try { localStorage.setItem(INSTALLED_RUNTIME_KEY, state.installedRuntime); } catch (e) {}
    refreshInstalledRuntimeButtons();
    renderInstalledList();
    setInstalledStatus('Moteur sélectionné : <strong>' + (state.installedRuntime === 'ollama' ? 'Ollama' : 'LM Studio') + '</strong>. Clique sur Actualiser pour lire les modèles installés.', 'normal');
  }
  function filterInstalledModels() { renderInstalledList(); }
  function refreshInstalledModels() {
    var runtime = state.installedRuntime;
    var button = $('freev-local-refresh');
    if (state.installedController) { try { state.installedController.abort(); } catch (e) {} }
    var controller = new AbortController();
    state.installedController = controller;
    var requestId = ++state.installedRequestId;
    if (button) { button.disabled = true; button.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin mr-1"></i> Recherche…'; }
    setInstalledStatus('<i class="fa-solid fa-spinner fa-spin mr-1"></i>Lecture des modèles ' + (runtime === 'ollama' ? 'Ollama' : 'LM Studio') + ' sur ton ordinateur…', 'normal');
    var fetchFn = runtime === 'ollama' ? fetchOllamaModels : fetchLMStudioModels;
    fetchFn(controller).then(function (models) {
      if (requestId !== state.installedRequestId) return;
      state.installedModels[runtime] = models;
      renderInstalledList();
      setInstalledStatus(models.length ? (models.length + ' modèle' + (models.length > 1 ? 's' : '') + ' détecté' + (models.length > 1 ? 's' : '') + '.') : 'Aucun modèle trouvé sur ce moteur.', models.length ? 'ok' : 'warn');
    }).catch(function () {
      if (requestId !== state.installedRequestId || controller.signal.aborted) return;
      var target = runtime === 'ollama' ? 'Ollama (port 11434)' : 'LM Studio (port 1234)';
      var hint = runtime === 'ollama' ? '<code class="text-red-100">ollama serve</code> puis actualise.' : 'Dans LM Studio : <strong>Developer → Start Server</strong>, puis actualise.';
      setInstalledStatus('Impossible de joindre ' + target + '. ' + hint, 'error');
    }).then(function () {
      if (button) { button.disabled = false; button.innerHTML = '<i class="fa-solid fa-rotate-right mr-1"></i> Actualiser'; }
    });
  }

  // ── Liaisons d'événements (une seule fois, sur des conteneurs stables) ────
  var grid = $('model-explorer-grid');
  if (grid) grid.addEventListener('click', function (ev) {
    var btn = ev.target.closest('[data-action]'); if (!btn) return;
    var idx = Number(btn.dataset.index);
    var action = btn.dataset.action;
    if (action === 'favorite') toggleFavorite(idx);
    else if (action === 'install') openInstallGuide(idx);
    else if (action === 'use') useModel(idx);
  });

  var suggestBox = $('model-search-suggestions');
  if (suggestBox) suggestBox.addEventListener('click', function (ev) {
    var btn = ev.target.closest('[data-suggestion]'); if (!btn) return;
    applyModelSearch(btn.dataset.suggestion);
  });

  var installContent = $('install-guide-content');
  if (installContent) installContent.addEventListener('click', function (ev) {
    var copyBtn = ev.target.closest('[data-copy]');
    if (copyBtn) { copyText(copyBtn.getAttribute('data-copy'), copyBtn); return; }
    var useBtn = ev.target.closest('[data-use]');
    if (useBtn) useModel(state.installIndex);
  });

  var installedList = $('freev-installed-list');
  if (installedList) installedList.addEventListener('click', function (ev) {
    var btn = ev.target.closest('[data-select-id]'); if (!btn) return;
    selectInstalledModel(btn.getAttribute('data-select-id'));
  });

  document.addEventListener('click', function (ev) {
    var btn = ev.target.closest && ev.target.closest('[data-freev-copy-command]');
    if (btn) copyText(btn.getAttribute('data-freev-copy-command'), btn);
  });

  document.addEventListener('keydown', function (ev) {
    if (ev.key !== 'Escape') return;
    var installedModal = $('freev-installed-models-modal');
    var installModal = $('model-install-modal');
    var explorerModal = $('model-explorer-modal');
    if (installedModal && !installedModal.classList.contains('hidden')) { closeInstalledModels(); return; }
    if (installModal && !installModal.classList.contains('hidden')) { closeInstallGuide(); return; }
    if (explorerModal && !explorerModal.classList.contains('hidden')) closeModelExplorer();
  });

  // ── Exposition globale (compatible avec les attributs onclick existants) ─
  window.openModelExplorer = openModelExplorer;
  window.closeModelExplorer = closeModelExplorer;
  window.setExplorerRuntime = setExplorerRuntime;
  window.selectExplorerTab = selectExplorerTab;
  window.handleModelSearch = handleModelSearch;
  window.handleModelSearchKey = handleModelSearchKey;
  window.clearModelSearchOnly = clearModelSearchOnly;
  window.applyModelSearch = applyModelSearch;
  window.clearModelFilters = clearModelFilters;
  window.changeModelPage = changeModelPage;
  window.renderModelGrid = render;
  window.toggleInstallQuickGuide = toggleInstallQuickGuide;
  window.openInstallGuide = openInstallGuide;
  window.closeInstallGuide = closeInstallGuide;
  window.setInstallRuntime = setInstallRuntime;
  window.openInstalledModels = openInstalledModels;
  window.closeInstalledModels = closeInstalledModels;
  window.setInstalledRuntime = setInstalledRuntime;
  window.refreshInstalledModels = refreshInstalledModels;
  window.filterInstalledModels = filterInstalledModels;
})();
