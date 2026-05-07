// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2025 - 2026 William José Moreno Reyes
//
// Componente Alpine.js para campos de selección asistida (smart-select).
// Consulta el endpoint /api/search-select con búsqueda dinámica.

/**
 * Construye los parámetros de filtro para la URL de búsqueda.
 * Los filtros pueden ser valores estáticos o referencias a elementos DOM
 * mediante { selector: "#id" }.
 *
 * @param {Object} filters - Mapa de nombre de filtro a valor o descriptor de selector.
 * @returns {URLSearchParams} Parámetros listos para añadir a la URL.
 */
function _buildFilterParams(filters) {
  const params = new URLSearchParams();
  for (const [key, spec] of Object.entries(filters || {})) {
    if (spec && typeof spec === "object" && spec.selector) {
      const el = document.querySelector(spec.selector);
      const val = el ? (el.value || "").trim() : "";
      if (val) params.append(key, val);
    } else if (spec !== null && spec !== undefined && spec !== "") {
      params.append(key, String(spec));
    }
  }
  return params;
}

/**
 * Componente Alpine.js smartSelect.
 *
 * Uso:
 *   x-data='smartSelect({
 *     doctype: "account",
 *     name: "account",
 *     minChars: 2,
 *     filters: { company: { selector: "#company" } },
 *     filterSources: ["#company"],
 *     initialValue: "{{ value }}",
 *     initialLabel: "{{ label }}",
 *     messages: { placeholder, loading, noResults, minChars, clear, invalid, error }
 *   })'
 *
 * @param {Object} config - Configuración del componente.
 * @returns {Object} Objeto de datos Alpine.js.
 */
function smartSelect(config) {
  const {
    doctype = "",
    name = "",
    minChars = 2,
    filters = {},
    filterSources = [],
    initialValue = "",
    initialLabel = "",
    messages = {},
  } = config;

  return {
    doctype,
    name,
    minChars,
    filters,
    filterSources,
    messages: {
      placeholder: messages.placeholder || "Buscar...",
      loading: messages.loading || "Buscando...",
      noResults: messages.noResults || "Sin resultados",
      minChars: messages.minChars || "Escriba para buscar",
      clear: messages.clear || "Limpiar",
      invalid: messages.invalid || "Seleccione una opción válida",
      error: messages.error || "No se pudo buscar",
    },

    // Estado
    search: initialLabel || "",
    selectedValue: initialValue || "",
    options: [],
    open: false,
    loading: false,
    error: "",
    _debounceTimer: null,

    /**
     * Inicializa el componente y registra escuchas en los filterSources.
     */
    init() {
      for (const selector of filterSources) {
        const el = document.querySelector(selector);
        if (el) {
          el.addEventListener("change", () => {
            if (this.selectedValue) {
              this.clearSelection();
            }
          });
        }
      }
    },

    /**
     * Maneja el evento de entrada en el campo de búsqueda con debounce.
     */
    onInput() {
      clearTimeout(this._debounceTimer);
      this.error = "";
      if (this.search.length < this.minChars) {
        this.options = [];
        this.open = false;
        return;
      }
      this._debounceTimer = setTimeout(() => this._fetch(), 250);
    },

    /**
     * Consulta el endpoint de búsqueda y actualiza las opciones.
     */
    async _fetch() {
      this.loading = true;
      this.open = true;
      try {
        const params = new URLSearchParams({ doctype: this.doctype, q: this.search });
        const filterParams = _buildFilterParams(this.filters);
        for (const [k, v] of filterParams.entries()) {
          params.append(k, v);
        }
        const response = await fetch(`/api/search-select?${params.toString()}`, {
          headers: { "X-Requested-With": "XMLHttpRequest" },
          credentials: "same-origin",
        });
        if (!response.ok) {
          const data = await response.json().catch(() => ({}));
          this.error = data.message || this.messages.error;
          this.options = [];
        } else {
          const data = await response.json();
          this.options = data.results || [];
        }
      } catch (_err) {
        this.error = this.messages.error;
        this.options = [];
      } finally {
        this.loading = false;
      }
    },

    /**
     * Selecciona una opción del dropdown.
     * @param {Object} option - Opción seleccionada con value y display_name.
     */
    selectOption(option) {
      this.selectedValue = option.value;
      this.search = option.display_name;
      this.open = false;
      this.options = [];
      this.error = "";
      // Notificar cambio para que otros componentes reactivos se actualicen
      this.$nextTick(() => {
        const hiddenInput = this.$el.querySelector(`input[type="hidden"]`);
        if (hiddenInput) {
          hiddenInput.dispatchEvent(new Event("change", { bubbles: true }));
        }
      });
    },

    /**
     * Limpia la selección actual.
     */
    clearSelection() {
      this.selectedValue = "";
      this.search = "";
      this.options = [];
      this.open = false;
      this.error = "";
    },

    /**
     * Cierra el dropdown con un pequeño retraso para permitir clics.
     */
    closeSoon() {
      setTimeout(() => {
        this.open = false;
      }, 200);
    },
  };
}
