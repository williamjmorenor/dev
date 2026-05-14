---
applyTo: "**/templates/**/*.html"
---

# Transactional Form Rules

- **Structure:** Separate Header (metadata) and Grid (items). Header contains: Company, Posting Date, Currency, Series, Status. Grid is the focus.
- **Referencia:** Use `cacao_accounting/contabilidad/templates/contabilidad/journal_nuevo.html` and `cacao_accounting/contabilidad/templates/contabilidad/journal.html` as the reference pattern.
- **Line Ops:** support add (above/below), duplicate, delete, and reorder. Use clonable row templates.
- **Expansion:** Secondary fields (analytical dims, internal refs) in collapsed panels or modals. Grid only for high-speed digitizing (Account, Amount).
- **User Prefs:** Persist visible columns in backend via `UserFormPreference`. Support reset.
- **Validation:** Visual cues for required fields. Real-time totals and balance checks. Sum(Debit) == Sum(Credit).
- **No-Go:** No fixed row counts. No secondary screens for basic line capture. No local-only prefs.

# List views

- Include usefull filters in list views like Company, Status, Accounting Period, etc.
- Use badges for quick visual guidance abouts status.

# Reports 

- **Structure:** Reference report is `cacao_accounting/reportes/templates/reportes/financial_report.html`
- **User layout:** User can save personal layouts for quick access.
