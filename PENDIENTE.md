# PENDIENTE — Cacao Accounting (Backlog Priorizado)

## Core y Posting
- [ ] Resolver política formal de renumeración de `document_no` tras cambios en borradores.
- [ ] Implementar soporte completo para `GLEntryDimension` (dimensiones personalizadas) en posting.

## AR/AP y Terceros
- [ ] Implementar modelo `PartyGroup` y su CRUD.
- [ ] Completar edición/visualización por compañía para Cliente y Proveedor en nuevo patrón.
- [ ] Gestión de múltiples direcciones y contactos para terceros.
- [ ] Conciliación masiva de facturas contra pagos (interfaz dedicada).
- [ ] Buckets configurables por compañía en reportes de Aging.

## Inventario y Valoración
- [ ] Implementar "Stock Reconciliation" para ajuste de valuación (actualmente solo cantidad).
- [ ] Prorrateo de cargos capitalizables (fletes/seguros) en `StockValuationLayer`.

## Administración y Seguridad
- [ ] Matriz explícita de autorización Usuario ↔ Compañía/Libro.
- [ ] Implementar Workflow de aprobación configurable (estados y transiciones).
- [ ] Activar `AuditLog` automático para cambios en documentos operativos.

## Multi-Ledger y Revalorización
- [ ] Implementar `LedgerMappingRule` para diferencias automáticas entre libros.
- [ ] Implementar proceso de `ExchangeRevaluation` (revalorización cambiaria de cuentas monetarias).
- [ ] UI para gestión de `DimensionType` y `DimensionValue`.

## UI/UX y Reportes
- [ ] Filtros de búsqueda en listados de Compras, Ventas y Bancos.
- [ ] Migrar formularios operativos restantes al Smart Select Framework (la grilla unificada ya quedó alineada con el patrón de comprobante).
- [ ] Implementar árbol gráfico de trazabilidad (Diagrama de Flujo).
- [ ] Drill-down universal en el 100% de los reportes operativos.
- [ ] Exportación consistente a Excel con formato financiero en todos los reportes.

## Nota de Integración (2026-05-14)
- [ ] Verificar en CI la integración selectiva completa sobre `main`.

# PENDIENTE

- **Reportes:** Implementar más reportes operativos usando el nuevo framework.
- **Migración gradual UI:** Seguir migrando formularios operativos al patrón común sin tocar todavía pagos bancarios ni documentos con origen complejo sin cobertura funcional suficiente.
- **Localización:** Ampliar catálogos impositivos para otros países.
- **Automatización:** Webhooks para integración con sistemas externos.
- **E2E:** Ampliar cobertura de pruebas Playwright en el nuevo flujo estandarizado.
