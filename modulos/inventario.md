# Módulo: Inventario (Stock / Inventory)
Rol: Control de existencia física y valoración de ítems.

## Principios de Diseño
- `StockLedgerEntry` (SLE) es la única fuente de verdad.
- `StockBin` actúa como snapshot/cache de saldos actuales.
- Valoración soportada: FIFO y Promedio Móvil.
- Ítems `service` no afectan inventario.

## Modelos Principales
- **Maestros:** `Item`, `UOM`, `Warehouse`.
- **Trazabilidad:** `Batch`, `SerialNumber`.
- **Transaccional:** `StockEntry`, `StockLedgerEntry`, `StockValuationLayer`.

## Propósitos de Stock Entry
`receipt`, `issue`, `transfer`, `adjustment_positive`, `adjustment_negative`, `repack`.
