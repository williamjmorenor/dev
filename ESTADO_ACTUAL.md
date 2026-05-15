# ESTADO ACTUAL - 2026-05-15

- **Core:** Python 3.12, Flask, Alpine.js.
- **Contabilidad:** Multi-libro, multimoneda, Comprobantes Recurrentes y Cierre Mensual funcionales.
- **Módulos Operativos:** Compras, Ventas e Inventario ya usan el framework transaccional unificado para formularios con grid de ítems; Bancos mantiene formulario de pagos especializado por referencias de factura.
- **UX:** `transaction-form.js` y sus macros compartidos replican el patrón del comprobante contable con 6 columnas núcleo siempre visibles, modal de detalle por línea y panel de lectura en vistas de detalle.
- **Flujo documental:** Factura → Pago soporta relaciones documentales sin línea, reversión al cancelar y recálculo de saldo pendiente.
- **Calidad:** Base verificada con build, Flake8, Ruff, Mypy, Pytest y Mocha (`606 passed, 3 skipped` en pytest), más pruebas específicas para `transaction-form.js`.
