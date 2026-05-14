# Flujo Documental y Relaciones
Este módulo define la trazabilidad transversal entre documentos.

## Acciones de Creación (Make/Create)
- **Ventas:** SO → Delivery → Invoice → Payment → Credit Note.
- **Compras:** PO → Receipt → Invoice → Payment → Debit/Credit Note.
- **Inventario:** Receipt → Stock Entry; Delivery → Stock Entry.

## Patrón "Actualizar Elementos"
Mecanismo para tirar líneas de documentos fuente hacia destinos:
- Factura ← Orden / Entrega / Recepción.
- Pago ← Facturas (múltiples).
- Nota de Crédito ← Factura.

## Reglas de Oro
- Mantener `pending_qty = qty - processed_qty`.
- No duplicar líneas consumidas.
- Trazabilidad bidireccional vía `DocumentRelation`.
