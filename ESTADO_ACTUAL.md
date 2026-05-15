# ESTADO ACTUAL - 2026-05-15

- **Core:** Python 3.12, Flask, Alpine.js.
- **Contabilidad:** Multi-libro, multimoneda, Comprobantes Recurrentes y Cierre Mensual funcionales.
- **Módulos Operativos:** Compras, Ventas e Inventario usan el framework transaccional unificado en formularios de ítems; Compras conserva el flujo Solicitud de Compra → Orden de Compra y Bancos mantiene el formulario de pagos especializado por referencias.
- **UX:** `smart-select.js` y `transaction-form.js` sostienen la experiencia reutilizable; la grilla transaccional conserva 6 columnas núcleo, detalle por línea y respeta cantidades editadas al importar documentos origen.
- **Flujo documental:** Factura → Pago soporta relaciones sin línea, reversión al cancelar y recálculo de saldo pendiente, sin perder trazabilidad en los flujos S2P integrados.
- **Calidad:** Integración validada con build, Flake8, Ruff, Mypy, Pytest y Mocha (`607 passed, 3 skipped` en pytest; `17 passing` en Mocha); además se consolidaron correcciones funcionales y deduplicación de literales provenientes de la rama de FIXME.
