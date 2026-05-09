// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2025 - 2026 William Jose Moreno Reyes

'use strict';

const assert = require('assert');
const { createEnvironment, makeFetch, makeFailingFetch } = require('./setup');

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function tick() {
  return new Promise(function (resolve) { setTimeout(resolve, 0); });
}

function flushPromises() {
  return new Promise(function (resolve) { setTimeout(resolve, 10); });
}

// ---------------------------------------------------------------------------
// Test suite
// ---------------------------------------------------------------------------

describe('smartSelect', function () {
  let env;

  beforeEach(function () {
    env = createEnvironment();
    // Default global fetch: returns empty results
    env.window.fetch = makeFetch([]).fakeFetch;
  });

  // -------------------------------------------------------------------------
  // 1. fetchOptions — live search executes fetch with correct URL
  // -------------------------------------------------------------------------
  it('fetchOptions — live search: fetches server when query >= minChars and required filters present', async function () {
    // Arrange: add #company input to DOM with a selected value
    const companyInput = env.document.createElement('input');
    companyInput.type = 'hidden';
    companyInput.id = 'company';
    companyInput.value = 'cacao';
    env.document.body.appendChild(companyInput);

    const { fakeFetch, calls } = makeFetch([
      { id: '1', value: '1', label: '11.01 - Efectivo', display_name: '11.01 - Efectivo' },
    ]);
    env.window.fetch = fakeFetch;

    const comp = env.factory({
      doctype: 'account',
      name: 'account',
      minChars: 1,
      loadOnFilterChange: true,
      requiredFilters: ['company'],
      filters: { company: { selector: '#company' } },
      filterSources: [],
    });

    comp.search = '11';
    comp.fetchOptions();

    await flushPromises();

    assert.ok(calls.length === 1, 'fetch should be called once');
    assert.ok(calls[0].includes('doctype=account'), 'URL must include doctype');
    assert.ok(calls[0].includes('q=11'), 'URL must include query');
    assert.ok(calls[0].includes('company=cacao'), 'URL must include company filter');
    assert.strictEqual(comp.options.length, 1, 'options should have 1 result');
    assert.strictEqual(comp.open, true);
  });

  // -------------------------------------------------------------------------
  // 2. fetchOptions — blocked by missing required filter
  // -------------------------------------------------------------------------
  it('fetchOptions — blocked: no fetch when required filter is empty', async function () {
    const companyInput = env.document.createElement('input');
    companyInput.type = 'hidden';
    companyInput.id = 'company';
    companyInput.value = ''; // empty — required filter not present
    env.document.body.appendChild(companyInput);

    const { fakeFetch, calls } = makeFetch([{ id: '1', value: '1', display_name: 'Test' }]);
    env.window.fetch = fakeFetch;

    const comp = env.factory({
      doctype: 'account',
      name: 'account',
      minChars: 1,
      requiredFilters: ['company'],
      filters: { company: { selector: '#company' } },
      filterSources: [],
    });

    comp.search = '11';
    comp.fetchOptions();

    await flushPromises();

    assert.strictEqual(calls.length, 0, 'fetch must NOT be called when required filter empty');
    assert.strictEqual(comp.options.length, 0);
    assert.strictEqual(comp.open, false);
  });

  // -------------------------------------------------------------------------
  // 3. fetchOptions — uses preloaded cache for queries below minChars
  // -------------------------------------------------------------------------
  it('fetchOptions — uses cache: client-side filter when query shorter than minChars', async function () {
    const { fakeFetch, calls } = makeFetch([]);
    env.window.fetch = fakeFetch;

    const comp = env.factory({
      doctype: 'account',
      name: 'account',
      minChars: 2,
      filters: {},
      filterSources: [],
    });

    comp._preloadedCache = [
      { id: '1', value: '1', display_name: 'Efectivo' },
      { id: '2', value: '2', display_name: 'Bancos' },
    ];
    comp.search = 'e'; // length 1 < minChars 2 → should use cache
    comp.fetchOptions();

    await flushPromises();

    assert.strictEqual(calls.length, 0, 'fetch must NOT be called when using cache');
    assert.strictEqual(comp.options.length, 1, 'cache should be filtered');
    assert.strictEqual(comp.options[0].display_name, 'Efectivo');
    assert.strictEqual(comp.open, true);
  });

  // -------------------------------------------------------------------------
  // 4. fetchOptions — empty cache + short query clears options
  // -------------------------------------------------------------------------
  it('fetchOptions — empty cache + short query: sets options=[] and open=false', async function () {
    const { fakeFetch, calls } = makeFetch([{ id: '1', value: '1', display_name: 'Efectivo' }]);
    env.window.fetch = fakeFetch;

    const comp = env.factory({
      doctype: 'account',
      name: 'account',
      minChars: 2,
      filters: {},
      filterSources: [],
    });

    // _preloadedCache is empty by default
    comp.search = 'e'; // below minChars, no cache
    comp.fetchOptions();

    await flushPromises();

    assert.strictEqual(calls.length, 0);
    assert.strictEqual(comp.options.length, 0);
    assert.strictEqual(comp.open, false);
  });

  // -------------------------------------------------------------------------
  // 5. preloadOptions — loads results and populates _preloadedCache
  // -------------------------------------------------------------------------
  it('preloadOptions — stores results in options and _preloadedCache', async function () {
    const results = [
      { id: '1', value: '1', display_name: 'Efectivo' },
      { id: '2', value: '2', display_name: 'Bancos' },
    ];
    const { fakeFetch, calls } = makeFetch(results);
    env.window.fetch = fakeFetch;

    const comp = env.factory({
      doctype: 'account',
      name: 'account',
      preload: true,
      filters: {},
      filterSources: [],
    });

    comp.preloadOptions();
    await flushPromises();

    assert.strictEqual(calls.length, 1, 'fetch should be called once');
    assert.ok(calls[0].includes('q='), 'URL should include q param');
    assert.strictEqual(comp.options.length, 2);
    assert.strictEqual(comp._preloadedCache.length, 2, '_preloadedCache must be populated');
  });

  // -------------------------------------------------------------------------
  // 6. preloadOptions — autoSelectDefault selects the default option
  // -------------------------------------------------------------------------
  it('preloadOptions — autoSelectDefault: auto-selects is_default option', async function () {
    const results = [
      { id: '1', value: '1', display_name: 'Series A', is_default: false },
      { id: '2', value: '2', display_name: 'Series B', is_default: true },
    ];
    const { fakeFetch } = makeFetch(results);
    env.window.fetch = fakeFetch;

    const comp = env.factory({
      doctype: 'naming_series',
      name: 'naming_series_id',
      preload: true,
      autoSelectDefault: true,
      filters: {},
      filterSources: [],
    });

    comp.preloadOptions();
    await flushPromises();

    assert.strictEqual(comp.selectedValue, '2', 'default option should be selected');
    assert.strictEqual(comp.selectedLabel, 'Series B');
  });

  // -------------------------------------------------------------------------
  // 7. filterPreloadedOptions — filters by substring match
  // -------------------------------------------------------------------------
  it('filterPreloadedOptions — returns only items matching substring', function () {
    const comp = env.factory({ doctype: 'account', name: 'account', filters: {}, filterSources: [] });
    comp._preloadedCache = [
      { id: '1', value: '1', display_name: 'Efectivo' },
      { id: '2', value: '2', display_name: 'Bancos Nacionales' },
      { id: '3', value: '3', display_name: 'Fondos por Depositar' },
    ];

    const results = comp.filterPreloadedOptions('banco');
    assert.strictEqual(results.length, 1);
    assert.strictEqual(results[0].display_name, 'Bancos Nacionales');
  });

  // -------------------------------------------------------------------------
  // 8. filterPreloadedOptions — case-insensitive matching
  // -------------------------------------------------------------------------
  it('filterPreloadedOptions — case-insensitive matching', function () {
    const comp = env.factory({ doctype: 'account', name: 'account', filters: {}, filterSources: [] });
    comp._preloadedCache = [
      { id: '1', value: '1', display_name: 'EFECTIVO CAJA' },
      { id: '2', value: '2', display_name: 'Bancos' },
    ];

    const results = comp.filterPreloadedOptions('BANCO');
    assert.strictEqual(results.length, 1);
    assert.strictEqual(results[0].id, '2');
  });

  // -------------------------------------------------------------------------
  // 9. clearSelection — resets all state including _preloadedCache
  // -------------------------------------------------------------------------
  it('clearSelection — resets selectedValue, selectedLabel, search, options, _preloadedCache, open', function () {
    const comp = env.factory({ doctype: 'account', name: 'account', filters: {}, filterSources: [] });

    comp.selectedValue = 'abc';
    comp.selectedLabel = 'Test';
    comp.search = 'Te';
    comp.options = [{ id: '1', value: '1', display_name: 'Test' }];
    comp._preloadedCache = [{ id: '1', value: '1', display_name: 'Test' }];
    comp.open = true;
    comp.invalid = true;

    comp.clearSelection();

    assert.strictEqual(comp.selectedValue, '');
    assert.strictEqual(comp.selectedLabel, '');
    assert.strictEqual(comp.search, '');
    assert.strictEqual(comp.options.length, 0);
    assert.strictEqual(comp._preloadedCache.length, 0);
    assert.strictEqual(comp.open, false);
    assert.strictEqual(comp.invalid, false);
  });

  // -------------------------------------------------------------------------
  // 10. closeSoon — auto-selects option when search matches exact label
  // -------------------------------------------------------------------------
  it('closeSoon — auto-selects option on exact label match', async function () {
    const comp = env.factory({ doctype: 'account', name: 'account', filters: {}, filterSources: [] });

    comp.search = 'Efectivo';
    comp.options = [
      { id: '1', value: '1', display_name: 'Efectivo' },
      { id: '2', value: '2', display_name: 'Efectivo Caja' },
    ];
    comp.open = true;

    comp.closeSoon();
    await new Promise(function (resolve) { setTimeout(resolve, 200); });

    assert.strictEqual(comp.selectedValue, '1');
    assert.strictEqual(comp.open, false);
  });

  // -------------------------------------------------------------------------
  // 11. closeSoon — auto-selects when only one result remains
  // -------------------------------------------------------------------------
  it('closeSoon — auto-selects when only one option available', async function () {
    const comp = env.factory({ doctype: 'account', name: 'account', filters: {}, filterSources: [] });

    comp.search = 'efec';
    comp.options = [{ id: '1', value: '1', display_name: 'Efectivo' }];
    comp.open = true;

    comp.closeSoon();
    await new Promise(function (resolve) { setTimeout(resolve, 200); });

    assert.strictEqual(comp.selectedValue, '1');
    assert.strictEqual(comp.open, false);
  });

  // -------------------------------------------------------------------------
  // 12. closeSoon — marks invalid when search has text but no selection made
  // -------------------------------------------------------------------------
  it('closeSoon — marks invalid when typed text has no valid selection', async function () {
    const comp = env.factory({ doctype: 'account', name: 'account', filters: {}, filterSources: [] });

    comp.search = 'xyz';
    comp.options = [];
    comp.selectedValue = '';

    comp.closeSoon();
    await new Promise(function (resolve) { setTimeout(resolve, 200); });

    assert.strictEqual(comp.invalid, true);
  });

  // -------------------------------------------------------------------------
  // 13. handleFilterChange — same signature causes no action
  // -------------------------------------------------------------------------
  it('handleFilterChange — no action when filter signature unchanged', async function () {
    const { fakeFetch, calls } = makeFetch([{ id: '1', value: '1', display_name: 'X' }]);
    env.window.fetch = fakeFetch;

    const comp = env.factory({
      doctype: 'account',
      name: 'account',
      preload: true,
      filters: { status: 'active' },
      filterSources: [],
    });

    // Prime lastFilterSignature (same as current)
    comp.lastFilterSignature = JSON.stringify({ status: 'active' });

    comp.handleFilterChange();
    await flushPromises();

    assert.strictEqual(calls.length, 0, 'fetch must not be called when signature unchanged');
  });

  // -------------------------------------------------------------------------
  // 14. handleFilterChange — new signature triggers clearSelection + preload
  // -------------------------------------------------------------------------
  it('handleFilterChange — clear and preload when filter signature changes', async function () {
    const companyInput = env.document.createElement('input');
    companyInput.type = 'hidden';
    companyInput.id = 'company2';
    companyInput.value = 'new_co';
    env.document.body.appendChild(companyInput);

    const { fakeFetch, calls } = makeFetch([{ id: '1', value: '1', display_name: 'Account' }]);
    env.window.fetch = fakeFetch;

    const comp = env.factory({
      doctype: 'account',
      name: 'account',
      loadOnFilterChange: true,
      filters: { company: { selector: '#company2' } },
      filterSources: [],
    });

    // Force old signature
    comp.lastFilterSignature = JSON.stringify({ company: 'old_co' });
    comp.selectedValue = 'old_val';
    comp.search = 'old';

    comp.handleFilterChange();
    await flushPromises();

    assert.strictEqual(comp.selectedValue, '', 'selection should be cleared');
    assert.strictEqual(comp.search, '', 'search text should be cleared');
    assert.ok(calls.length >= 1, 'preload fetch should be triggered');
  });

  // -------------------------------------------------------------------------
  // 15. requiredFiltersPresent — returns false when any required filter empty
  // -------------------------------------------------------------------------
  it('requiredFiltersPresent — false when required filter resolves to empty string', function () {
    const emptyInput = env.document.createElement('input');
    emptyInput.type = 'hidden';
    emptyInput.id = 'co_empty';
    emptyInput.value = '';
    env.document.body.appendChild(emptyInput);

    const comp = env.factory({
      doctype: 'account',
      name: 'account',
      requiredFilters: ['company'],
      filters: { company: { selector: '#co_empty' } },
      filterSources: [],
    });

    assert.strictEqual(comp.requiredFiltersPresent(), false);
  });

  it('requiredFiltersPresent — true when required filter has a value', function () {
    const filledInput = env.document.createElement('input');
    filledInput.type = 'hidden';
    filledInput.id = 'co_filled';
    filledInput.value = 'cacao';
    env.document.body.appendChild(filledInput);

    const comp = env.factory({
      doctype: 'account',
      name: 'account',
      requiredFilters: ['company'],
      filters: { company: { selector: '#co_filled' } },
      filterSources: [],
    });

    assert.strictEqual(comp.requiredFiltersPresent(), true);
  });

  // -------------------------------------------------------------------------
  // 16. applySelection with keepOptions=true preserves options list
  // -------------------------------------------------------------------------
  it('applySelection(keepOptions=true) — keeps existing options list intact', function () {
    const comp = env.factory({ doctype: 'account', name: 'account', filters: {}, filterSources: [] });

    comp.options = [
      { id: '1', value: '1', display_name: 'Efectivo' },
      { id: '2', value: '2', display_name: 'Bancos' },
    ];

    comp.applySelection({ id: '1', value: '1', display_name: 'Efectivo' }, { keepOptions: true });

    assert.strictEqual(comp.selectedValue, '1');
    assert.strictEqual(comp.options.length, 2, 'options must be preserved');
  });

  it('applySelection without keepOptions — clears options list', function () {
    const comp = env.factory({ doctype: 'account', name: 'account', filters: {}, filterSources: [] });

    comp.options = [
      { id: '1', value: '1', display_name: 'Efectivo' },
    ];

    comp.applySelection({ id: '1', value: '1', display_name: 'Efectivo' });

    assert.strictEqual(comp.selectedValue, '1');
    assert.strictEqual(comp.options.length, 0, 'options must be cleared');
    assert.strictEqual(comp.open, false);
  });

  // -------------------------------------------------------------------------
  // 17. notifyValueChange — sets hidden input value and dispatches events
  // -------------------------------------------------------------------------
  it('notifyValueChange — sets hidden input value and dispatches change event', function () {
    // Build a root element with a hidden input
    const root = env.document.createElement('div');
    const hidden = env.document.createElement('input');
    hidden.type = 'hidden';
    hidden.name = 'account';
    root.appendChild(hidden);
    env.document.body.appendChild(root);

    const comp = env.factory({ doctype: 'account', name: 'account', filters: {}, filterSources: [] }, root);

    comp.selectedValue = 'some-uuid';

    const events = [];
    hidden.addEventListener('change', function (e) { events.push('change'); });
    hidden.addEventListener('input', function (e) { events.push('input'); });

    comp.notifyValueChange();

    assert.strictEqual(hidden.value, 'some-uuid', 'hidden input value must be set');
    assert.ok(events.includes('change'), 'change event must be dispatched');
    assert.ok(events.includes('input'), 'input event must be dispatched');
  });

  // -------------------------------------------------------------------------
  // 18. Race condition: stale preload should not overwrite live search results
  // -------------------------------------------------------------------------
  it('race condition: stale fetch does not overwrite live search results', async function () {
    let resolvePreload;
    let resolveFetch;

    // Preload fetch: delayed
    const preloadPromise = new Promise(function (r) { resolvePreload = r; });
    // Live search fetch: delayed less
    const fetchPromise = new Promise(function (r) { resolveFetch = r; });

    let callCount = 0;
    env.window.fetch = function (url) {
      callCount++;
      const currentCall = callCount;
      return new Promise(function (resolve) {
        if (currentCall === 1) {
          // preload
          preloadPromise.then(function () {
            resolve({ ok: true, json: function () { return Promise.resolve({ results: [{ id: 'p', value: 'p', display_name: 'PreloadResult' }] }); } });
          });
        } else {
          // live search — resolves first
          fetchPromise.then(function () {
            resolve({ ok: true, json: function () { return Promise.resolve({ results: [{ id: 'l', value: 'l', display_name: 'LiveSearchResult' }] }); } });
          });
        }
      });
    };

    const comp = env.factory({
      doctype: 'account',
      name: 'account',
      minChars: 1,
      filters: {},
      filterSources: [],
    });

    // Start preload
    comp.preloadOptions();

    // Start live search (increments _fetchSeq)
    comp.search = '11';
    comp.fetchOptions();

    // Resolve live search first → sets options
    resolveFetch();
    await flushPromises();

    assert.strictEqual(comp.options.length, 1);
    assert.strictEqual(comp.options[0].display_name, 'LiveSearchResult', 'live result should win');

    // Now resolve stale preload — should NOT overwrite because _fetchSeq moved
    resolvePreload();
    await flushPromises();

    assert.strictEqual(comp.options[0].display_name, 'LiveSearchResult', 'stale preload must not overwrite live result');
  });

  // -------------------------------------------------------------------------
  // 19. onFocus — opens dropdown from cache when available
  // -------------------------------------------------------------------------
  it('onFocus — opens dropdown from cache when loadOnFilterChange and cache populated', function () {
    const comp = env.factory({
      doctype: 'account',
      name: 'account',
      loadOnFilterChange: true,
      filters: {},
      filterSources: [],
    });

    comp._preloadedCache = [
      { id: '1', value: '1', display_name: 'Efectivo' },
      { id: '2', value: '2', display_name: 'Bancos' },
    ];
    comp.open = false;
    comp.loading = false;

    comp.onFocus();

    assert.strictEqual(comp.open, true);
    assert.strictEqual(comp.options.length, 2);
  });

  // -------------------------------------------------------------------------
  // 20. fetchOptions — empty query with cache shows full cache
  // -------------------------------------------------------------------------
  it('fetchOptions — empty query with cache shows full unfiltered cache', async function () {
    const { fakeFetch, calls } = makeFetch([]);
    env.window.fetch = fakeFetch;

    const comp = env.factory({
      doctype: 'account',
      name: 'account',
      minChars: 1,
      filters: {},
      filterSources: [],
    });

    comp._preloadedCache = [
      { id: '1', value: '1', display_name: 'Efectivo' },
      { id: '2', value: '2', display_name: 'Bancos' },
    ];
    comp.search = ''; // empty query

    comp.fetchOptions();
    await flushPromises();

    assert.strictEqual(calls.length, 0, 'no server call for empty query with cache');
    assert.strictEqual(comp.options.length, 2, 'all cached items shown');
    assert.strictEqual(comp.open, true);
  });
});
