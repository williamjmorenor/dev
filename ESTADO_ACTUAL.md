# ESTADO ACTUAL - 2026-05-15

- **Core:** Python 3.12, Flask, Alpine.js.
- **Contabilidad:** Multi-libro, multimoneda, Comprobantes Recurrentes y Cierre Mensual funcionales.
- **Módulos Operativos:** Compras (S2P avanzado), Ventas e Inventario continúan la estandarización visual; Bancos mantiene formulario de pagos especializado por referencias de factura.
- **UX:** Librerías reutilizables `smart-select.js` y `transaction-form.js`; la grilla transaccional se aplica de forma gradual y no se usa para pagos.
- **Flujo documental:** Factura → Pago soporta relaciones documentales sin línea, reversión al cancelar y recálculo de saldo pendiente.
- **Calidad:** Validación amplia local en verde con build, Flake8, Ruff, Mypy, Pytest y Mocha (`606 passed, 3 skipped` en pytest).
