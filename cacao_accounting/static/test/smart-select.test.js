// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2025 - 2026 William Jose Moreno Reyes

const assert = require('assert');

function loadSmartSelect(overrides = {}) {
  const listeners = {};
  const elements = overrides.elements || {};
  const fetchImpl = overrides.fetch || (() => Promise.resolve({ ok: true, json: () => Promise.resolve({ results: [] }) }));
  let smartSelectFactory = null;

  global.document = {
    addEventListener: (event, callback) => {
      listeners[event] = callback;
    },
    querySelector: (selector) => elements[selector] || null,
  };

  global.Alpine = {
    data: (name, factory) => {
      if (name === 'smartSelect') smartSelectFactory = factory;
    },
  };

  global.fetch = fetchImpl;

  const modulePath = require.resolve('../js/smart-select.js');
  delete require.cache[modulePath];
  require(modulePath);
  listeners['alpine:init']();

  return function create(config) {
    return smartSelectFactory(config);
  };
}

async function flushPromises() {
  await new Promise((resolve) => setTimeout(resolve, 0));
  await new Promise((resolve) => setTimeout(resolve, 0));
}

describe('smart-select', function () {
  afterEach(function () {
    delete global.document;
    delete global.Alpine;
    delete global.fetch;
  });

  it('does not preload on focus when preloadOnFocus is disabled', async function () {
    let fetchCalls = 0;
    const create = loadSmartSelect({
      fetch: () => {
        fetchCalls += 1;
        return Promise.resolve({ ok: true, json: () => Promise.resolve({ results: [] }) });
      },
    });
    const component = create({
      doctype: 'naming_series',
      name: 'naming_series_id',
      preload: true,
      initialValue: 'SER-001',
      minChars: 1,
    });

    component.init();
    component.onFocus();
    await flushPromises();

    assert.strictEqual(fetchCalls, 0);
    assert.strictEqual(component.open, false);
  });

  it('allows preload on focus when explicitly enabled', async function () {
    let fetchCalls = 0;
    const create = loadSmartSelect({
      fetch: () => {
        fetchCalls += 1;
        return Promise.resolve({ ok: true, json: () => Promise.resolve({ results: [{ value: 'cafe' }] }) });
      },
    });
    const component = create({
      doctype: 'company',
      name: 'company',
      preload: true,
      preloadOnFocus: true,
      minChars: 1,
    });

    component.onFocus();
    await flushPromises();

    assert.strictEqual(fetchCalls, 1);
    assert.strictEqual(component.options.length, 1);
  });

  it('clears dependent state on filter change without fetching when preload is disabled', async function () {
    let fetchCalls = 0;
    const companyElement = { value: 'cafe', addEventListener: () => {} };
    const create = loadSmartSelect({
      elements: { '#company': companyElement },
      fetch: () => {
        fetchCalls += 1;
        return Promise.resolve({ ok: true, json: () => Promise.resolve({ results: [] }) });
      },
    });
    const component = create({
      doctype: 'naming_series',
      name: 'naming_series_id',
      filters: { company: { selector: '#company' } },
      filterSources: ['#company'],
      preload: false,
      minChars: 1,
    });

    component.init();
    component.selectedValue = 'SER-001';
    component.selectedLabel = 'Serie 001';
    component.search = 'Serie 001';
    component.options = [{ value: 'SER-001' }];
    companyElement.value = 'choco';

    component.handleFilterChange();
    await flushPromises();

    assert.strictEqual(component.selectedValue, '');
    assert.strictEqual(component.selectedLabel, '');
    assert.strictEqual(component.search, '');
    assert.deepStrictEqual(component.options, []);
    assert.strictEqual(fetchCalls, 0);
  });

  it('normalizes object filters to scalar values for backend queries', async function () {
    let requestUrl = '';
    const create = loadSmartSelect({
      fetch: (url) => {
        requestUrl = url;
        return Promise.resolve({ ok: true, json: () => Promise.resolve({ results: [] }) });
      },
    });
    const component = create({
      doctype: 'naming_series',
      name: 'naming_series_id',
      minChars: 1,
      filters: {
        company: () => ({ value: 'cafe' }),
        entity_type: { id: 'journal_entry' },
      },
    });

    component.search = 'caf';
    component.fetchOptions();
    await flushPromises();

    const queryString = decodeURIComponent(requestUrl.split('?')[1] || '');
    assert.ok(queryString.includes('company=cafe'));
    assert.ok(queryString.includes('entity_type=journal_entry'));
    assert.strictEqual(queryString.includes('[object Object]'), false);
  });
});
