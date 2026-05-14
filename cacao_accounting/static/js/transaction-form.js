// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2025 - 2026 William Jose MORENO Reyes

(function () {
  document.addEventListener('alpine:init', function () {
    Alpine.data('transactionForm', function (config) {
      return {
        formKey: config.formKey,
        viewKey: config.viewKey,
        preferences: config.initialPreferences || { columns: [] },
        messages: config.messages || {},
        header: config.initialHeader || {},
        lines: [],
        sourceItems: [],
        loadingSource: false,
        activeIndex: null,
        modalLine: null,
        payload: '',

        normalizeLine: function (line) {
          var base = this.newLine();
          var normalized = Object.assign({}, base, line || { uid: window.crypto.randomUUID ? window.crypto.randomUUID() : Math.random().toString(36).substring(7) });
          this.calcAmount(normalized);
          return normalized;
        },

        init: function () {
          const self = this;
          this.lines = (config.initialLines || []).map(line => self.normalizeLine(line));
          if (this.lines.length === 0) {
            this.addMultipleRows(config.defaultRows || 2);
          }
        },

        get visibleColumns() {
          return (this.preferences.columns || []).filter(c => c.visible);
        },

        newLine: function () {
          var uid = window.crypto.randomUUID ? window.crypto.randomUUID() : Math.random().toString(36).substring(7);
          return Object.assign({
            uid: uid,
            item_code: '',
            item_name: '',
            qty: 1,
            uom: '',
            rate: 0,
            amount: 0,
            source_type: '',
            source_id: '',
            source_item_id: ''
          }, config.linePrototype || {});
        },

        addRow: function () {
          this.lines.push(this.newLine());
        },

        addMultipleRows: function (count) {
          for (var i = 0; i < count; i++) this.addRow();
        },

        insertRow: function (index) {
          this.lines.splice(index, 0, this.newLine());
        },

        duplicateRow: function (index) {
          var copy = Object.assign({}, this.lines[index]);
          copy.uid = window.crypto.randomUUID ? window.crypto.randomUUID() : Math.random().toString(36).substring(7);
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
          line.amount = parseFloat(line.qty || 0) * parseFloat(line.rate || 0);
        },

        openDetails: function (index) {
          this.activeIndex = index;
          this.modalLine = Object.assign({}, this.lines[index]);
          var modalEl = document.getElementById('lineDetailModal');
          if (modalEl) bootstrap.Modal.getOrCreateInstance(modalEl).show();
        },

        saveModalLine: function () {
          if (this.activeIndex !== null && this.modalLine) {
            this.lines[this.activeIndex] = Object.assign({}, this.modalLine);
          }
          var modalEl = document.getElementById('lineDetailModal');
          if (modalEl) bootstrap.Modal.getOrCreateInstance(modalEl).hide();
        },

        fetchSource: function (apiUrl) {
          this.loadingSource = true;
          fetch(apiUrl, { credentials: 'same-origin' })
            .then(r => r.json())
            .then(data => {
              this.sourceItems = (data.items || []).map(item => Object.assign({ selected: true }, item));
              this.loadingSource = false;
            })
            .catch(() => { this.loadingSource = false; });
        },

        applySource: function () {
          const sel = this.sourceItems.filter(i => i.selected);
          sel.forEach(i => {
            const exists = this.lines.some(row =>
              row.source_type === i.source_type &&
              row.source_id === i.source_id &&
              row.source_item_id === i.source_item_id
            );
            if (!exists) {
              this.lines.push(Object.assign(this.newLine(), {
                item_code: i.item_code,
                item_name: i.item_name,
                qty: i.pending_qty || i.qty,
                uom: i.uom,
                rate: i.rate,
                amount: (i.pending_qty || i.qty) * i.rate,
                source_type: i.source_type || '',
                source_id: i.source_id || '',
                source_item_id: i.source_item_id || ''
              }));
            }
          });
          // Remove completely empty rows if they were there as placeholders
          this.lines = this.lines.filter(l => l.item_code || l.source_id);
          if (this.lines.length === 0) this.addRow();
        },

        moveColumn: function (index, direction) {
          var target = index + direction;
          if (target < 0 || target >= this.preferences.columns.length) return;
          var column = this.preferences.columns.splice(index, 1)[0];
          this.preferences.columns.splice(target, 0, column);
        },

        savePreferences: function () {
          var self = this;
          var csrfToken = document.querySelector('input[name="csrf_token"]').value;
          fetch('/api/form-preferences/' + encodeURIComponent(this.formKey) + '/' + encodeURIComponent(this.viewKey), {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
            credentials: 'same-origin',
            body: JSON.stringify(this.preferences)
          })
            .then(r => r.json())
            .then(payload => {
              self.preferences = payload;
              var modalEl = document.getElementById('columnsModal');
              if (modalEl) bootstrap.Modal.getOrCreateInstance(modalEl).hide();
            });
        },

        resetPreferences: function () {
          var self = this;
          var csrfToken = document.querySelector('input[name="csrf_token"]').value;
          fetch('/api/form-preferences/' + encodeURIComponent(this.formKey) + '/' + encodeURIComponent(this.viewKey), {
            method: 'DELETE',
            headers: { 'X-CSRFToken': csrfToken },
            credentials: 'same-origin'
          })
            .then(r => r.json())
            .then(payload => {
              self.preferences = payload;
            });
        },

        formatMoney: function (value) {
          return Number(value || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
        }
      };
    });
  });
}());
