Sí. Aquí el requerimiento claro para mejorar los 3 reportes sin romper el backend común.

# Requerimiento técnico — Reportes financieros jerárquicos y navegables

## 1. Objetivo

Mejorar los reportes financieros principales de **Cacao Accounting**:

* Balanza de Comprobación
* Balance General
* Estado de Resultado

manteniendo un **framework centralizado de reportes financieros**, pero permitiendo que cada reporte tenga una **presentación especializada**, más cercana a la expectativa de contadores tradicionales.

El objetivo no es convertir cada reporte en un módulo independiente, sino separar correctamente:

* **Backend común de cálculo**
* **Modelo común de datos financieros**
* **Renderer especializado por tipo de reporte**
* **Navegación contable unificada**

---

# 2. Principio arquitectónico

La implementación actual usa el mismo backend para los cuatro reportes.
Esto debe mantenerse.

El backend común garantiza que:

* Los saldos sean consistentes.
* La Balanza, Balance General, Estado de Resultado y Detalle de Movimiento usen la misma fuente contable.
* No existan diferencias numéricas entre reportes.
* La lógica de filtros, período, compañía, libro contable, estado y moneda sea compartida.

Sin embargo, los reportes financieros no deben verse todos como tablas planas.

Debe existir una capa adicional:

```text
Financial Report Engine
        ↓
Financial Report Dataset común
        ↓
Renderer especializado
        ↓
Vista del reporte
```

---

# 3. Problema actual

Actualmente los reportes:

* Se ven demasiado técnicos.
* Presentan datos como tablas planas.
* No muestran claramente el árbol de cuentas.
* No permiten navegar naturalmente desde un saldo hasta sus movimientos.
* No reflejan el formato tradicional esperado por contadores.
* Balance General y Estado de Resultado no tienen formato financiero suficientemente legible.

---

# 4. Requerimiento principal

Los reportes de:

* Balanza de Comprobación
* Balance General
* Estado de Resultado

deben renderizarse como **estructuras jerárquicas basadas en el árbol de cuentas contables**, con nodos expandibles y colapsables.

Ejemplo:

```text
▾ 1 Activos
  ▾ 1.1 Activo corriente
    ▾ 1.1.01 Efectivo y equivalentes
        1.1.01.001 Caja
```

No deben mostrarse únicamente como una tabla plana.

---

# 5. Navegación contable obligatoria

Debe implementarse navegación real desde los reportes hacia el detalle que integra cada saldo.

## 5.1 Balance General

Flujo esperado:

```text
Balance General
→ clic en cuenta o rubro
→ abre Detalle de Movimiento Contable filtrado por cuenta
→ clic en comprobante
→ abre comprobante contable
```

## 5.2 Estado de Resultado

Flujo esperado:

```text
Estado de Resultado
→ clic en sección o rubro
→ expande cuentas relacionadas
→ clic en cuenta
→ abre Detalle de Movimiento Contable filtrado por cuenta
→ clic en comprobante
→ abre documento/comprobante contable
```

## 5.3 Balanza de Comprobación

Flujo esperado:

```text
Balanza de Comprobación
→ clic en cuenta
→ abre Detalle de Movimiento Contable filtrado por cuenta
→ clic en comprobante
→ abre comprobante contable
```

---

# 6. Formato financiero esperado

## 6.1 Balance General

Debe mostrarse en formato financiero, no como tabla técnica.

Ejemplo:

```text
ACTIVOS

Activo corriente
  Efectivo y equivalentes                     1,000.00
  Cuentas por cobrar                            500.00
TOTAL ACTIVO CORRIENTE                        1,500.00

TOTAL ACTIVOS                                 1,500.00


PASIVOS

Pasivo corriente
  Cuentas por pagar                              300.00
TOTAL PASIVO CORRIENTE                          300.00

TOTAL PASIVOS                                   300.00


PATRIMONIO

Capital en acciones comunes                   1,200.00
TOTAL PATRIMONIO                              1,200.00

TOTAL PASIVO + PATRIMONIO                     1,500.00
```

---

## 6.2 Estado de Resultado

Debe mostrarse en formato financiero:

```text
INGRESOS

Ingresos por ventas                           5,000.00
TOTAL INGRESOS                                5,000.00


COSTOS

Costo de ventas                               2,000.00
TOTAL COSTOS                                  2,000.00

UTILIDAD BRUTA                                3,000.00


GASTOS

Gastos administrativos                          800.00
Gastos de ventas                                500.00
TOTAL GASTOS                                  1,300.00

UTILIDAD NETA                                 1,700.00
```

---

## 6.3 Balanza de Comprobación

Debe conservar su naturaleza tabular, pero con jerarquía contable:

```text
▾ 1 Activos
  ▾ 1.1 Activo corriente
      1.1.01.001 Caja        0.00    1,000.00    0.00    1,000.00

▾ 3 Patrimonio
      3.1 Capital            0.00        0.00  1,000.00  (1,000.00)
```

Columnas mínimas:

* Cuenta
* Nombre de cuenta
* Saldo inicial
* Débito
* Crédito
* Saldo final
* Nivel

---

# 7. Comportamiento de jerarquías

Cada nodo del árbol debe soportar:

* Expandir
* Colapsar
* Mostrar subtotal acumulado
* Mostrar saldo propio si aplica
* Mostrar saldo consolidado de hijos
* Diferenciar visualmente secciones, grupos y cuentas finales

Los nodos padres deben calcularse a partir de sus hijos.

Las cuentas hoja deben permitir navegación hacia movimientos.

---

# 8. Reglas de interacción

## 8.1 Clic en cuenta contable

Al hacer clic en una cuenta contable, el sistema debe abrir:

```text
/reports/account-movement
```

con filtros preaplicados:

* Compañía
* Libro contable
* Período
* Cuenta contable
* Estado
* Moneda, si aplica
* Dimensiones activas, si aplica

## 8.2 Clic en comprobante desde Detalle de Movimiento

Al hacer clic en el comprobante:

```text
cacao-JOU-2026-05-00002
```

el sistema debe abrir el comprobante contable correspondiente.

---

# 9. Requerimiento de backend

El backend debe seguir siendo común.

Debe producir un dataset estructurado que permita dos modos de consumo:

## 9.1 Modo plano

Para:

* Exportar CSV
* Exportar Excel
* Detalle de Movimiento Contable
* Validaciones internas

## 9.2 Modo jerárquico

Para:

* Balanza de Comprobación
* Balance General
* Estado de Resultado

El dataset jerárquico debe incluir como mínimo:

```json
{
  "account": "1.1.01.001",
  "account_name": "Caja",
  "parent_account": "1.1.01",
  "level": 4,
  "is_group": false,
  "section": "ACTIVOS",
  "opening_balance": 0,
  "debit": 1000,
  "credit": 0,
  "final_balance": 1000,
  "has_children": false,
  "movement_url": "/reports/account-movement?...",
  "children": []
}
```

---

# 10. Requerimiento de UI

La interfaz debe conservar:

* Sidebar izquierdo del sistema
* Columna izquierda de filtros
* Área principal del reporte
* Botones de exportación

Pero el área principal del reporte debe mejorar visualmente.

Debe incluir:

* Encabezado financiero claro
* Secciones contables destacadas
* Subtotales visibles
* Totales finales destacados
* Nodos expandibles
* Cuentas clicables
* Indicador de reporte cuadrado cuando aplique
* Mejor alineación numérica
* Mejor separación visual entre secciones

---

# 11. Exportación

Los reportes deben permitir exportar:

* Excel
* CSV

La exportación debe soportar:

* Versión plana
* Versión jerárquica indentada

En Excel, debe respetarse la indentación de niveles.

Ejemplo:

```text
ACTIVOS
  Activo corriente
    Efectivo y equivalentes
      Caja
TOTAL ACTIVOS
```

---

# 12. Criterios de aceptación

## CA-001 — Backend común preservado

Los cuatro reportes deben seguir usando el mismo backend financiero base.

No debe duplicarse lógica de cálculo por reporte.

---

## CA-002 — Jerarquía visible

Balanza de Comprobación, Balance General y Estado de Resultado deben mostrar el árbol contable con niveles expandibles.

---

## CA-003 — Navegación desde saldo

Al hacer clic en una cuenta con saldo, el sistema debe abrir Detalle de Movimiento Contable filtrado por esa cuenta y contexto.

---

## CA-004 — Navegación hasta comprobante

Desde Detalle de Movimiento Contable, el usuario debe poder abrir el comprobante contable que originó el movimiento.

---

## CA-005 — Balance General con formato financiero

Balance General debe mostrarse por secciones:

* Activos
* Pasivos
* Patrimonio
* Total Pasivo + Patrimonio

---

## CA-006 — Estado de Resultado con formato financiero

Estado de Resultado debe mostrarse por secciones:

* Ingresos
* Costos
* Utilidad bruta
* Gastos
* Utilidad neta

---

## CA-007 — Balanza con árbol contable

La Balanza de Comprobación debe mantener columnas contables, pero agrupadas jerárquicamente por el árbol de cuentas.

---

## CA-008 — Totales consistentes

Los totales mostrados en:

* Balanza de Comprobación
* Balance General
* Estado de Resultado
* Detalle de Movimiento Contable

deben coincidir cuando se usan los mismos filtros.

---

## CA-009 — Filtros preservados en navegación

Al navegar de un reporte a otro, los filtros activos deben conservarse.

---

## CA-010 — Exportación jerárquica

Excel debe exportar la estructura jerárquica con indentación visual.

CSV puede exportarse plano, pero debe incluir columna `level`.

---

# 13. Resultado esperado

El sistema debe mantener una arquitectura centralizada y confiable, pero ofrecer reportes financieros con presentación profesional, navegable y entendible para contadores.

La mejora clave es esta:

```text
No cambiar el motor.
Cambiar la forma de presentar y navegar los resultados.
```

El backend debe seguir siendo único.
La experiencia visual debe adaptarse al tipo de reporte.
