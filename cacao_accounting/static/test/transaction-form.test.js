// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2025 - 2026 William Jose MORENO Reyes

const assert = require('assert');

function loadTransactionForm(overrides = {}) {
  const listeners = {};
  const elements = overrides.elements || {};
  const fetchImpl = overrides.fetch || (() => Promise.resolve({ ok: true, json: () => Promise.resolve({ items: [] }) }));
  let transactionFormFactory = null;

  global.document = {
    addEventListener: (event, callback) => {
      listeners[event] = callback;
    },
    querySelector: (selector) => {
        if (selector === 'input[name="csrf_token"]') return { value: 'test-token' };
        return elements[selector] || null;
    },
  };

  global.Alpine = {
    data: (name, factory) => {
      if (name === 'transactionForm') transactionFormFactory = factory;
    },
  };

  global.fetch = fetchImpl;
  global.window = {
      crypto: {
          randomUUID: () => 'test-uuid-' + Math.random().toString(36).substring(7)
      }
  };
  global.bootstrap = {
      Modal: {
          getOrCreateInstance: () => ({ show: () => {}, hide: () => {} })
      }
  };

  const modulePath = require.resolve('../js/transaction-form.js');
  delete require.cache[modulePath];
  require(modulePath);
  listeners['alpine:init']();

  return function create(config) {
    return transactionFormFactory(config);
  };
}

async function flushPromises() {
  await new Promise((resolve) => setImmediate(resolve));
}

describe('transaction-form', function () {
  afterEach(function () {
    delete global.document;
    delete global.Alpine;
    delete global.fetch;
    delete global.window;
    delete global.bootstrap;
  });

  it('initializes with default rows if no lines provided', function () {
    const create = loadTransactionForm();
    const component = create({ defaultRows: 3 });
    component.init();
    assert.strictEqual(component.lines.length, 3);
  });

  it('initializes with provided lines', function () {
    const create = loadTransactionForm();
    const initialLines = [
        { item_code: 'item1', qty: 10, rate: 5 },
        { item_code: 'item2', qty: 5, rate: 20 }
    ];
    const component = create({ initialLines: initialLines });
    component.init();
    assert.strictEqual(component.lines.length, 2);
    assert.strictEqual(component.lines[0].item_code, 'item1');
    assert.strictEqual(component.lines[0].amount, 50);
    assert.strictEqual(component.lines[1].item_code, 'item2');
    assert.strictEqual(component.lines[1].amount, 100);
  });

  it('addRow adds a new empty line', function () {
    const create = loadTransactionForm();
    const component = create({ defaultRows: 1 });
    component.init();
    component.addRow();
    assert.strictEqual(component.lines.length, 2);
    assert.strictEqual(component.lines[1].item_code, '');
  });

  it('removeRow removes a line or resets if last line', function () {
    const create = loadTransactionForm();
    const component = create({ defaultRows: 2 });
    component.init();
    component.lines[0].item_code = 'item1';
    component.removeRow(0);
    assert.strictEqual(component.lines.length, 1);
    assert.notStrictEqual(component.lines[0].item_code, 'item1');

    component.lines[0].item_code = 'last';
    component.removeRow(0);
    assert.strictEqual(component.lines.length, 1);
    assert.strictEqual(component.lines[0].item_code, '');
  });

  it('calcAmount calculates total correctly', function () {
    const create = loadTransactionForm();
    const component = create({ defaultRows: 1 });
    component.init();
    const line = component.lines[0];
    line.qty = 5;
    line.rate = 10.5;
    component.calcAmount(line);
    assert.strictEqual(line.amount, 52.5);
  });

  it('duplicateRow creates a copy at next index', function () {
    const create = loadTransactionForm();
    const component = create({ initialLines: [{ item_code: 'original', qty: 1 }] });
    component.init();
    component.duplicateRow(0);
    assert.strictEqual(component.lines.length, 2);
    assert.strictEqual(component.lines[1].item_code, 'original');
    assert.notStrictEqual(component.lines[0].uid, component.lines[1].uid);
  });

  it('fetchSource populates sourceItems', async function () {
    let fetchCalled = false;
    const create = loadTransactionForm({
        fetch: () => {
            fetchCalled = true;
            return Promise.resolve({
                ok: true,
                json: () => Promise.resolve({ items: [{ item_code: 'src1', qty: 10 }] })
            });
        }
    });
    const component = create({});
    component.fetchSource('/api/test');
    assert.strictEqual(component.loadingSource, true);
    await flushPromises();
    assert.strictEqual(fetchCalled, true);
    assert.strictEqual(component.loadingSource, false);
    assert.strictEqual(component.sourceItems.length, 1);
    assert.strictEqual(component.sourceItems[0].item_code, 'src1');
    assert.strictEqual(component.sourceItems[0].selected, true);
  });

  it('applySource adds selected items to lines', function () {
    const create = loadTransactionForm();
    const component = create({ defaultRows: 1 });
    component.init();
    component.sourceItems = [
        { item_code: 'src1', qty: 10, rate: 2, uom: 'unit', selected: true, source_type: 'Order', source_id: '1', source_item_id: '101' },
        { item_code: 'src2', qty: 5, rate: 3, selected: false }
    ];
    component.applySource();
    // It should have replaced the empty row or added to it
    assert.strictEqual(component.lines.length, 1);
    assert.strictEqual(component.lines[0].item_code, 'src1');
    assert.strictEqual(component.lines[0].amount, 20);
    assert.strictEqual(component.lines[0].source_id, '1');
  });

  it('formatMoney formats correctly', function () {
      const create = loadTransactionForm();
      const component = create({});
      // Note: toLocaleString depends on environment, but we check basic behavior
      const result = component.formatMoney(1234.5);
      assert.ok(result.includes('1,234.50') || result.includes('1.234,50') || result.includes('1234.50'));
  });
});
