# Módulo: Compras (Buying / Purchasing)
Rol: Gestión del flujo **Source to Pay (S2P)**.

## Principios de Diseño
- Patrón Header + Items obligatorio.
- Recepción e Invoice son eventos separados.
- Uso de cuenta puente (Bridge) para conciliación de mercancía vs. factura.
- Impacto contable automático en GL.

## Modelos Principales
- **Terceros:** `Party` (supplier), `CompanyParty` (activación).
- **Documentos:** `PurchaseOrder`, `PurchaseReceipt`, `PurchaseInvoice`.
- **Conciliación:** `PurchaseReconciliation`.
- **Maestros:** `TaxTemplate`, `PriceList`, `ItemPrice`.

## Flujo Operativo
Solicitud (Material Request) → RFQ → Cotización Proveedor → Comparativo de ofertas → Orden de Compra (PO) → Recepción (Receipt) → Factura (Invoice) → Devolucion → Nota de Debito / Credito → Pago.

### Flujo configurable:

- Permitir Orden de Compra sin Solicitud de Compra.
- Permitir Factura sin Orden de Compra.
- Permtir Recepción sin Orden de Compra.

Puede definirse a nivel global o por Proveedor, configuración de proveedor prevalece sobre configuración global.
