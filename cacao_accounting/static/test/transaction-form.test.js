// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2025 - 2026 William Jose MORENO Reyes

const assert = require('assert');

function loadTransactionForm() {
  const listeners = {};
  let transactionFormFactory = null;

  global.window = {
    crypto: {
      randomUUID: () => 'uuid-test',
    },
  };

  global.document = {
    addEventListener: (event, callback) => {
      listeners[event] = callback;
    },
    querySelector: () => null,
    getElementById: () => null,
  };

  global.bootstrap = {
    Modal: {
      getOrCreateInstance: () => ({
        show() {},
        hide() {},
      }),
    },
  };

  global.Alpine = {
    data: (name, factory) => {
      if (name === 'transactionForm') transactionFormFactory = factory;
    },
  };

  const modulePath = require.resolve('../js/transaction-form.js');
  delete require.cache[modulePath];
  require(modulePath);
  listeners['alpine:init']();

  return function create(config) {
    return transactionFormFactory(config);
  };
}

describe('transaction-form', function () {
  afterEach(function () {
    delete global.window;
    delete global.document;
    delete global.bootstrap;
    delete global.Alpine;
  });

  it('uses required default columns when preferences are empty', function () {
    const create = loadTransactionForm();
    const component = create({
      items: [],
      uoms: [],
      columns: [],
      defaultRows: 1,
    });

    component.init();

    assert.deepStrictEqual(
      component.visibleColumns.map((column) => column.field),
      ['item_code', 'item_name', 'uom', 'qty', 'rate', 'amount']
    );
    assert.strictEqual(component.lines.length, 1);
  });

  it('keeps required columns visible even when legacy preferences hide them', function () {
    const create = loadTransactionForm();
    const component = create({
      items: [],
      uoms: [],
      columns: [
        { field: 'item_code', label: 'Código', visible: false, width: 2 },
        { field: 'item_name', label: 'Descripción', visible: true, width: 2 },
      ],
      defaultRows: 1,
    });

    component.init();

    assert.strictEqual(component.preferences.columns.find((column) => column.field === 'item_code').visible, true);
    assert.strictEqual(component.preferences.columns.find((column) => column.field === 'item_code').required, true);
  });

  it('filters unit options based on the selected item and keeps the selected unit valid', function () {
    const create = loadTransactionForm();
    const component = create({
      items: [
        { code: 'ITEM-001', name: 'Caja de cacao', uom: 'UND', allowed_uoms: ['UND', 'CAJA'] },
        { code: 'ITEM-002', name: 'Servicio logístico', uom: 'SERV' },
      ],
      uoms: [
        { code: 'UND', name: 'Unidad' },
        { code: 'CAJA', name: 'Caja' },
        { code: 'SERV', name: 'Servicio' },
      ],
      defaultRows: 1,
    });

    component.init();
    const line = component.lines[0];
    line.item_code = 'ITEM-001';

    component.onItemChange(line);

    assert.strictEqual(line.item_name, 'Caja de cacao');
    assert.strictEqual(line.uom, 'UND');
    assert.deepStrictEqual(component.getLineUoms(line).map((uom) => uom.code), ['UND', 'CAJA']);

    line.uom = 'CAJA';
    line.item_code = 'ITEM-002';
    component.onItemChange(line);

    assert.strictEqual(line.item_name, 'Servicio logístico');
    assert.strictEqual(line.uom, 'SERV');
    assert.deepStrictEqual(component.getLineUoms(line).map((uom) => uom.code), ['SERV']);
  });
});
