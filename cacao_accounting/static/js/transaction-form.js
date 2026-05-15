// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2025 - 2026 William Jose MORENO Reyes

(function () {
  function createUid() {
    if (window.crypto && window.crypto.randomUUID) return window.crypto.randomUUID();
    return Math.random().toString(36).substring(2, 10);
  }

  function toNumber(value) {
    var parsed = parseFloat(value || 0);
    if (Number.isNaN(parsed)) return 0;
    return parsed;
  }

  function normalizeAllowedUoms(source, fallback) {
    var values = Array.isArray(source) ? source.slice() : [];
    if (!values.length && fallback) values = [fallback];
    return values
      .map(function (value) {
        if (!value) return '';
        if (typeof value === 'object') return value.code || value.value || value.id || '';
        return String(value);
      })
      .filter(function (value, index, array) {
        return value && array.indexOf(value) === index;
      });
  }

  function defaultColumns(messages) {
    return [
      { field: 'item_code', label: messages.itemCode || 'Código del item', width: 2, visible: true, required: true },
      { field: 'item_name', label: messages.itemName || 'Descripción del item', width: 3, visible: true, required: true },
      { field: 'uom', label: messages.uom || 'Unidad de medida', width: 2, visible: true, required: true },
      { field: 'qty', label: messages.qty || 'Cantidad', width: 1, visible: true, required: true },
      { field: 'rate', label: messages.rate || 'Precio / Costo Unitario', width: 2, visible: true, required: true },
      { field: 'amount', label: messages.amount || 'Precio / Costo Total', width: 2, visible: true, required: true },
    ];
  }

  function normalizeColumns(columns, messages) {
    var baseColumns = defaultColumns(messages);
    var normalized = Array.isArray(columns) ? columns
      .filter(function (column) { return column && column.field; })
      .map(function (column) {
        return {
          field: String(column.field),
          label: column.label || String(column.field),
          width: Math.min(Math.max(parseInt(column.width || 1, 10), 1), 4),
          visible: column.visible !== false,
          required: Boolean(column.required),
        };
      }) : [];

    if (!normalized.length) return baseColumns;

    baseColumns.forEach(function (requiredColumn) {
      var existing = normalized.find(function (column) { return column.field === requiredColumn.field; });
      if (existing) {
        existing.label = existing.label || requiredColumn.label;
        existing.width = existing.width || requiredColumn.width;
        existing.visible = true;
        existing.required = true;
        return;
      }
      normalized.push(requiredColumn);
    });

    return normalized;
  }

  function normalizeItems(items) {
    if (!Array.isArray(items)) return [];
    return items.map(function (item) {
      var normalized = item || {};
      var defaultUom = normalized.uom || normalized.default_uom || '';
      return Object.assign({}, normalized, {
        code: normalized.code || normalized.value || '',
        name: normalized.name || normalized.item_name || normalized.label || '',
        default_uom: defaultUom,
        allowed_uoms: normalizeAllowedUoms(normalized.allowed_uoms || normalized.uoms, defaultUom),
      });
    });
  }

  document.addEventListener('alpine:init', function () {
    Alpine.data('transactionForm', function (config) {
      var messages = Object.assign({
        itemCode: 'Código del item',
        itemName: 'Descripción del item',
        uom: 'Unidad de medida',
        qty: 'Cantidad',
        rate: 'Precio / Costo Unitario',
        amount: 'Precio / Costo Total',
      }, config.messages || {});
      var initialPreferences = config.initialPreferences;
      if (!initialPreferences || !Array.isArray(initialPreferences.columns)) {
        initialPreferences = { columns: config.columns || [] };
      }

      return {
        formKey: config.formKey || '',
        viewKey: config.viewKey || 'draft',
        preferences: { columns: normalizeColumns(initialPreferences.columns, messages) },
        messages: messages,
        header: config.initialHeader || {},
        availableItems: normalizeItems(config.items),
        availableUoms: Array.isArray(config.uoms) ? config.uoms.slice() : [],
        availableWarehouses: Array.isArray(config.warehouses) ? config.warehouses.slice() : [],
        lines: [],
        sourceItems: [],
        loadingSource: false,
        activeIndex: null,
        modalLine: null,
        payload: '',

        init: function () {
          var self = this;
          this.lines = (config.initialLines || []).map(function (line) {
            return self.normalizeLine(line);
          });
          if (!this.lines.length) this.addMultipleRows(config.defaultRows || 2);
        },

        get visibleColumns() {
          return (this.preferences.columns || []).filter(function (column) {
            return column.visible !== false;
          });
        },

        get totalAmount() {
          return this.lines.reduce(function (total, line) {
            return total + toNumber(line.amount);
          }, 0);
        },

        newLine: function () {
          return Object.assign({
            uid: createUid(),
            item_code: '',
            item_name: '',
            qty: 1,
            uom: '',
            rate: 0,
            amount: 0,
            warehouse: '',
            account: '',
            cost_center: '',
            unit: '',
            project: '',
            remarks: '',
            source_type: '',
            source_id: '',
            source_item_id: '',
            allowed_uoms: [],
          }, config.linePrototype || {});
        },

        normalizeLine: function (line) {
          var base = this.newLine();
          var normalized = Object.assign({}, base, line || {});
          normalized.uid = normalized.uid || base.uid;
          normalized.allowed_uoms = normalizeAllowedUoms(normalized.allowed_uoms, normalized.uom);
          this.calcAmount(normalized);
          this.syncLineFromItem(normalized, Boolean(normalized.item_name));
          return normalized;
        },

        findItem: function (itemCode) {
          return this.availableItems.find(function (item) {
            return item.code === itemCode;
          }) || null;
        },

        getLineUoms: function (line) {
          var item = this.findItem(line.item_code);
          var allowed = normalizeAllowedUoms(
            (item && item.allowed_uoms) || line.allowed_uoms,
            (item && item.default_uom) || line.uom
          );
          if (!allowed.length) {
            return this.availableUoms.slice();
          }
          return allowed.map(function (code) {
            return this.availableUoms.find(function (uom) { return uom.code === code; }) || { code: code, name: code };
          }, this);
        },

        syncLineFromItem: function (line, keepCustomName) {
          var item = this.findItem(line.item_code);
          if (!item) {
            line.allowed_uoms = normalizeAllowedUoms(line.allowed_uoms, line.uom);
            return;
          }
          if (!keepCustomName || !line.item_name) line.item_name = item.name || line.item_name;
          line.allowed_uoms = normalizeAllowedUoms(item.allowed_uoms, item.default_uom);
          if (line.allowed_uoms.length && line.allowed_uoms.indexOf(line.uom) === -1) {
            line.uom = line.allowed_uoms[0];
          }
          if (!line.uom && item.default_uom) line.uom = item.default_uom;
        },

        onItemChange: function (line) {
          this.syncLineFromItem(line, false);
          this.calcAmount(line);
        },

        addRow: function () {
          this.lines.push(this.newLine());
        },

        addMultipleRows: function (count) {
          for (var index = 0; index < count; index += 1) this.addRow();
        },

        insertRow: function (index, direction) {
          var target = direction < 0 ? index : index + 1;
          this.lines.splice(target, 0, this.newLine());
        },

        moveRow: function (index, direction) {
          var target = index + direction;
          if (target < 0 || target >= this.lines.length) return;
          var current = this.lines[index];
          this.lines[index] = this.lines[target];
          this.lines[target] = current;
        },

        duplicateRow: function (index) {
          var copy = this.normalizeLine(this.lines[index]);
          copy.uid = createUid();
          this.lines.splice(index + 1, 0, copy);
        },

        removeRow: function (index) {
          if (this.lines.length === 1) {
            this.lines[index] = this.newLine();
            return;
          }
          this.lines.splice(index, 1);
        },

        calcAmount: function (line) {
          line.amount = toNumber(line.qty) * toNumber(line.rate);
        },

        openDetails: function (index) {
          this.activeIndex = index;
          this.modalLine = this.normalizeLine(this.lines[index]);
          var modalEl = document.getElementById('lineDetailModal');
          if (modalEl) bootstrap.Modal.getOrCreateInstance(modalEl).show();
        },

        saveModalLine: function () {
          if (this.activeIndex !== null && this.modalLine) {
            this.calcAmount(this.modalLine);
            this.lines[this.activeIndex] = this.normalizeLine(this.modalLine);
          }
          var modalEl = document.getElementById('lineDetailModal');
          if (modalEl) bootstrap.Modal.getOrCreateInstance(modalEl).hide();
        },

        fetchSource: function (apiUrl) {
          this.loadingSource = true;
          fetch(apiUrl, { credentials: 'same-origin' })
            .then(function (response) { return response.json(); })
            .then(function (data) {
              this.sourceItems = (data.items || []).map(function (item) {
                return Object.assign({ selected: true }, item);
              });
              this.loadingSource = false;
            }.bind(this))
            .catch(function () {
              this.loadingSource = false;
            }.bind(this));
        },

        applySource: function () {
          var self = this;
          this.sourceItems.filter(function (item) {
            return item.selected;
          }).forEach(function (item) {
            var exists = self.lines.some(function (line) {
              return line.source_type === item.source_type &&
                line.source_id === item.source_id &&
                line.source_item_id === item.source_item_id;
            });
            if (exists) return;
            var line = self.newLine();
            line.item_code = item.item_code || '';
            line.item_name = item.item_name || '';
            line.qty = toNumber(item.pending_qty || item.qty || 0);
            line.uom = item.uom || '';
            line.rate = toNumber(item.rate || 0);
            line.source_type = item.source_type || '';
            line.source_id = item.source_id || '';
            line.source_item_id = item.source_item_id || '';
            self.syncLineFromItem(line, false);
            self.calcAmount(line);
            self.lines.push(line);
          });

          this.lines = this.lines.filter(function (line) {
            return line.item_code || line.item_name || line.source_id;
          });
          if (!this.lines.length) this.addRow();
        },

        moveColumn: function (index, direction) {
          var target = index + direction;
          if (target < 0 || target >= this.preferences.columns.length) return;
          var column = this.preferences.columns.splice(index, 1)[0];
          this.preferences.columns.splice(target, 0, column);
        },

        savePreferences: function () {
          if (!this.formKey || !this.viewKey) return;
          var self = this;
          var csrfInput = document.querySelector('input[name="csrf_token"]');
          var csrfToken = csrfInput ? csrfInput.value : '';
          fetch('/api/form-preferences/' + encodeURIComponent(this.formKey) + '/' + encodeURIComponent(this.viewKey), {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
            credentials: 'same-origin',
            body: JSON.stringify(this.preferences)
          })
            .then(function (response) { return response.json(); })
            .then(function (payload) {
              self.preferences = { columns: normalizeColumns(payload.columns || [], self.messages) };
              var modalEl = document.getElementById('columnsModal');
              if (modalEl) bootstrap.Modal.getOrCreateInstance(modalEl).hide();
            });
        },

        resetPreferences: function () {
          if (!this.formKey || !this.viewKey) {
            this.preferences = { columns: defaultColumns(this.messages) };
            return;
          }
          var self = this;
          var csrfInput = document.querySelector('input[name="csrf_token"]');
          var csrfToken = csrfInput ? csrfInput.value : '';
          fetch('/api/form-preferences/' + encodeURIComponent(this.formKey) + '/' + encodeURIComponent(this.viewKey), {
            method: 'DELETE',
            headers: { 'X-CSRFToken': csrfToken },
            credentials: 'same-origin'
          })
            .then(function (response) { return response.json(); })
            .then(function (payload) {
              self.preferences = { columns: normalizeColumns(payload.columns || [], self.messages) };
            });
        },

        formatMoney: function (value) {
          return Number(value || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
        }
      };
    });
  });
}());
