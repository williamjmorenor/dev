# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 - 2026 William José Moreno Reyes

"""Pruebas para el sistema robusto de series e identificadores internos y externos."""

from __future__ import annotations

import unittest

from cacao_accounting import create_app
from cacao_accounting.config import configuracion


class TestNamingSeriesIsDefault(unittest.TestCase):
    """Pruebas para is_default en NamingSeries."""

    def setUp(self) -> None:
        self.app = create_app({**configuracion, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
        self.ctx = self.app.app_context()
        self.ctx.push()
        from cacao_accounting.database import database

        database.create_all()
        self.db = database

    def tearDown(self) -> None:
        self.db.session.rollback()
        self.ctx.pop()

    def _add_entity(self, code: str = "ent") -> None:
        from cacao_accounting.database import Entity

        self.db.session.add(Entity(code=code, name=code, company_name=code, tax_id="J0001", currency="NIO"))
        self.db.session.flush()

    def test_naming_series_has_is_default_field(self) -> None:
        """NamingSeries debe tener el campo is_default."""
        from cacao_accounting.database import NamingSeries

        self._add_entity()
        ns = NamingSeries(
            name="Serie Test",
            entity_type="sales_invoice",
            company="ent",
            prefix_template="ENT-SI-*YYYY*-",
            is_active=True,
            is_default=True,
        )
        self.db.session.add(ns)
        self.db.session.flush()

        self.assertTrue(ns.is_default)

    def test_enforce_single_default_series(self) -> None:
        """Solo una serie puede ser predeterminada por entity_type + company."""
        from cacao_accounting.database import NamingSeries
        from cacao_accounting.document_identifiers import enforce_single_default_series

        self._add_entity()

        ns1 = NamingSeries(
            name="Serie A",
            entity_type="sales_invoice",
            company="ent",
            prefix_template="A-SI-*YYYY*-",
            is_active=True,
            is_default=True,
        )
        ns2 = NamingSeries(
            name="Serie B",
            entity_type="sales_invoice",
            company="ent",
            prefix_template="B-SI-*YYYY*-",
            is_active=True,
            is_default=False,
        )
        self.db.session.add_all([ns1, ns2])
        self.db.session.flush()

        # Marcar ns2 como predeterminada debe desmarcar ns1
        enforce_single_default_series(entity_type="sales_invoice", company="ent", exclude_id=ns2.id)
        ns2.is_default = True
        self.db.session.flush()

        # Recargar desde la base de datos
        ns1_fresh = self.db.session.get(NamingSeries, ns1.id)
        ns2_fresh = self.db.session.get(NamingSeries, ns2.id)

        self.assertFalse(ns1_fresh.is_default)
        self.assertTrue(ns2_fresh.is_default)

    def test_pick_naming_series_prefers_is_default(self) -> None:
        """_pick_naming_series debe preferir la serie marcada como predeterminada."""
        from datetime import date

        from cacao_accounting.database import NamingSeries, Sequence, SeriesSequenceMap
        from cacao_accounting.document_identifiers import _pick_naming_series

        self._add_entity()

        ns_not_default = NamingSeries(
            name="Serie No Default",
            entity_type="purchase_invoice",
            company="ent",
            prefix_template="ENT-PI-A-*YYYY*-",
            is_active=True,
            is_default=False,
        )
        ns_default = NamingSeries(
            name="Serie Default",
            entity_type="purchase_invoice",
            company="ent",
            prefix_template="ENT-PI-B-*YYYY*-",
            is_active=True,
            is_default=True,
        )
        seq = Sequence(name="test seq", current_value=0, increment=1, padding=5)
        self.db.session.add_all([ns_not_default, ns_default, seq])
        self.db.session.flush()
        self.db.session.add(SeriesSequenceMap(naming_series_id=ns_default.id, sequence_id=seq.id, priority=0))
        self.db.session.flush()

        selected = _pick_naming_series(entity_type="purchase_invoice", company="ent", naming_series_id=None)
        self.assertEqual(selected.id, ns_default.id)


class TestExternalCounter(unittest.TestCase):
    """Pruebas para ExternalCounter y ExternalCounterAuditLog."""

    def setUp(self) -> None:
        self.app = create_app({**configuracion, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
        self.ctx = self.app.app_context()
        self.ctx.push()
        from cacao_accounting.database import database

        database.create_all()
        self.db = database
        self._add_entity()

    def tearDown(self) -> None:
        self.db.session.rollback()
        self.ctx.pop()

    def _add_entity(self, code: str = "ent") -> None:
        from cacao_accounting.database import Entity

        self.db.session.add(Entity(code=code, name=code, company_name=code, tax_id="J0001", currency="NIO"))
        self.db.session.flush()

    def _create_counter(self, last_used: int = 0) -> object:
        from cacao_accounting.database import ExternalCounter

        counter = ExternalCounter(
            company="ent",
            name="Chequera BANPRO",
            counter_type="checkbook",
            prefix="CHK-",
            last_used=last_used,
            padding=5,
            is_active=True,
        )
        self.db.session.add(counter)
        self.db.session.flush()
        return counter

    def test_external_counter_next_suggested(self) -> None:
        """next_suggested debe ser last_used + 1."""
        counter = self._create_counter(last_used=10542)
        self.assertEqual(counter.next_suggested, 10543)  # type: ignore[union-attr]

    def test_external_counter_next_suggested_formatted(self) -> None:
        """next_suggested_formatted debe incluir prefijo y padding."""
        counter = self._create_counter(last_used=10542)
        self.assertEqual(counter.next_suggested_formatted, "CHK-10543")  # type: ignore[union-attr]

    def test_suggest_next_external_number(self) -> None:
        """suggest_next_external_number debe devolver el siguiente formateado."""
        from cacao_accounting.document_identifiers import suggest_next_external_number

        counter = self._create_counter(last_used=20017)
        result = suggest_next_external_number(counter.id)  # type: ignore[union-attr]
        self.assertEqual(result, "CHK-20018")

    def test_suggest_next_raises_if_inactive(self) -> None:
        """suggest_next_external_number debe fallar si el contador esta inactivo."""
        from cacao_accounting.database import ExternalCounter
        from cacao_accounting.document_identifiers import IdentifierConfigurationError, suggest_next_external_number

        counter = ExternalCounter(
            company="ent",
            name="Chequera Inactiva",
            counter_type="checkbook",
            last_used=0,
            padding=5,
            is_active=False,
        )
        self.db.session.add(counter)
        self.db.session.flush()

        with self.assertRaises(IdentifierConfigurationError):
            suggest_next_external_number(counter.id)

    def test_adjust_external_counter_creates_audit_log(self) -> None:
        """adjust_external_counter debe crear un registro en ExternalCounterAuditLog."""
        from cacao_accounting.database import ExternalCounterAuditLog
        from cacao_accounting.document_identifiers import adjust_external_counter

        counter = self._create_counter(last_used=100)
        adjust_external_counter(
            external_counter_id=counter.id,  # type: ignore[union-attr]
            new_last_used=110,
            reason="Ajuste por anulacion de cheque 101 al 110.",
            changed_by="user-test",
        )

        log = self.db.session.execute(
            self.db.select(ExternalCounterAuditLog).filter_by(external_counter_id=counter.id)  # type: ignore[union-attr]
        ).scalar_one_or_none()

        self.assertIsNotNone(log)
        self.assertEqual(log.previous_value, 100)
        self.assertEqual(log.new_value, 110)
        self.assertEqual(log.changed_by, "user-test")
        self.assertIn("anulacion", log.reason)

    def test_adjust_external_counter_updates_last_used(self) -> None:
        """adjust_external_counter debe actualizar last_used del contador."""
        from cacao_accounting.database import ExternalCounter
        from cacao_accounting.document_identifiers import adjust_external_counter

        counter = self._create_counter(last_used=500)
        adjust_external_counter(
            external_counter_id=counter.id,  # type: ignore[union-attr]
            new_last_used=550,
            reason="Salto de chequera por cierre de ejercicio.",
        )

        refreshed = self.db.session.get(ExternalCounter, counter.id)  # type: ignore[union-attr]
        self.assertEqual(refreshed.last_used, 550)

    def test_adjust_external_counter_requires_reason(self) -> None:
        """adjust_external_counter debe fallar si el motivo esta vacio."""
        from cacao_accounting.document_identifiers import IdentifierConfigurationError, adjust_external_counter

        counter = self._create_counter(last_used=0)

        with self.assertRaises(IdentifierConfigurationError, msg="Debe indicar el motivo"):
            adjust_external_counter(
                external_counter_id=counter.id,  # type: ignore[union-attr]
                new_last_used=10,
                reason="",
            )

    def test_adjust_external_counter_requires_non_blank_reason(self) -> None:
        """adjust_external_counter debe fallar si el motivo es solo espacios."""
        from cacao_accounting.document_identifiers import IdentifierConfigurationError, adjust_external_counter

        counter = self._create_counter(last_used=0)

        with self.assertRaises(IdentifierConfigurationError):
            adjust_external_counter(
                external_counter_id=counter.id,  # type: ignore[union-attr]
                new_last_used=10,
                reason="   ",
            )

    def test_adjust_external_counter_raises_if_inactive(self) -> None:
        """adjust_external_counter debe fallar si el contador esta inactivo."""
        from cacao_accounting.database import ExternalCounter
        from cacao_accounting.document_identifiers import IdentifierConfigurationError, adjust_external_counter

        counter = ExternalCounter(
            company="ent",
            name="Contador Inactivo",
            counter_type="fiscal",
            last_used=0,
            padding=5,
            is_active=False,
        )
        self.db.session.add(counter)
        self.db.session.flush()

        with self.assertRaises(IdentifierConfigurationError):
            adjust_external_counter(
                external_counter_id=counter.id,
                new_last_used=10,
                reason="Motivo valido.",
            )

    def test_record_external_number_used(self) -> None:
        """record_external_number_used debe incrementar last_used cuando aplique."""
        from cacao_accounting.database import ExternalCounter
        from cacao_accounting.document_identifiers import record_external_number_used

        counter = self._create_counter(last_used=100)
        record_external_number_used(external_counter_id=counter.id, number_used=105)  # type: ignore[union-attr]

        refreshed = self.db.session.get(ExternalCounter, counter.id)  # type: ignore[union-attr]
        self.assertEqual(refreshed.last_used, 105)

    def test_record_external_number_used_does_not_decrease(self) -> None:
        """record_external_number_used no debe reducir last_used."""
        from cacao_accounting.database import ExternalCounter
        from cacao_accounting.document_identifiers import record_external_number_used

        counter = self._create_counter(last_used=200)
        record_external_number_used(external_counter_id=counter.id, number_used=150)  # type: ignore[union-attr]

        refreshed = self.db.session.get(ExternalCounter, counter.id)  # type: ignore[union-attr]
        self.assertEqual(refreshed.last_used, 200)

    def test_multiple_audit_log_entries(self) -> None:
        """Multiples ajustes deben generar multiples entradas en la bitacora."""
        from cacao_accounting.database import ExternalCounterAuditLog
        from cacao_accounting.document_identifiers import adjust_external_counter

        counter = self._create_counter(last_used=0)
        adjust_external_counter(
            external_counter_id=counter.id,  # type: ignore[union-attr]
            new_last_used=10,
            reason="Primer ajuste.",
        )
        adjust_external_counter(
            external_counter_id=counter.id,  # type: ignore[union-attr]
            new_last_used=20,
            reason="Segundo ajuste.",
        )

        logs = (
            self.db.session.execute(
                self.db.select(ExternalCounterAuditLog).filter_by(external_counter_id=counter.id)  # type: ignore[union-attr]
            )
            .scalars()
            .all()
        )

        self.assertEqual(len(logs), 2)


class TestSeriesExternalCounterMap(unittest.TestCase):
    """Pruebas para SeriesExternalCounterMap — GAP 4 y GAP 5."""

    def setUp(self) -> None:
        self.app = create_app({**configuracion, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
        self.ctx = self.app.app_context()
        self.ctx.push()
        from cacao_accounting.database import database

        database.create_all()
        self.db = database
        self._add_entity()

    def tearDown(self) -> None:
        self.db.session.rollback()
        self.ctx.pop()

    def _add_entity(self, code: str = "ent") -> None:
        from cacao_accounting.database import Entity

        self.db.session.add(Entity(code=code, name=code, company_name=code, tax_id="J0002", currency="NIO"))
        self.db.session.flush()

    def _make_series(self, name: str = "PAY", entity_type: str = "payment_entry") -> object:
        from cacao_accounting.database import NamingSeries, Sequence, SeriesSequenceMap

        seq = Sequence(name=f"seq-{name}", current_value=0, increment=1, padding=5)
        self.db.session.add(seq)
        self.db.session.flush()
        ns = NamingSeries(
            name=name,
            entity_type=entity_type,
            company="ent",
            prefix_template=f"ENT-{name}-*YYYY*-",
            is_active=True,
            is_default=True,
        )
        self.db.session.add(ns)
        self.db.session.flush()
        self.db.session.add(SeriesSequenceMap(naming_series_id=ns.id, sequence_id=seq.id, priority=0))
        self.db.session.flush()
        return ns

    def _make_counter(self, name: str, counter_type: str = "checkbook", last_used: int = 0) -> object:
        from cacao_accounting.database import ExternalCounter

        c = ExternalCounter(
            company="ent",
            name=name,
            counter_type=counter_type,
            prefix="CHK-",
            last_used=last_used,
            padding=5,
            is_active=True,
        )
        self.db.session.add(c)
        self.db.session.flush()
        return c

    def test_series_external_counter_map_model(self) -> None:
        """SeriesExternalCounterMap debe persistir correctamente."""
        from cacao_accounting.database import SeriesExternalCounterMap

        ns = self._make_series()
        counter = self._make_counter("Chequera BANPRO")
        mapping = SeriesExternalCounterMap(
            naming_series_id=ns.id,  # type: ignore[union-attr]
            external_counter_id=counter.id,  # type: ignore[union-attr]
            priority=0,
            condition_json='{"payment_method": "check"}',
        )
        self.db.session.add(mapping)
        self.db.session.flush()

        loaded = self.db.session.get(SeriesExternalCounterMap, mapping.id)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.naming_series_id, ns.id)  # type: ignore[union-attr]
        self.assertEqual(loaded.external_counter_id, counter.id)  # type: ignore[union-attr]
        self.assertIn("check", loaded.condition_json)  # type: ignore[union-attr]

    def test_condition_matches_exact(self) -> None:
        """_condition_matches debe devolver True cuando todas las condiciones coinciden."""
        from cacao_accounting.document_identifiers import _condition_matches

        cond = '{"payment_method": "check", "bank": "BANPRO"}'
        ctx = {"payment_method": "check", "bank": "BANPRO", "extra": "ignored"}
        self.assertTrue(_condition_matches(cond, ctx))

    def test_condition_matches_partial_fail(self) -> None:
        """_condition_matches debe devolver False si alguna condicion no coincide."""
        from cacao_accounting.document_identifiers import _condition_matches

        cond = '{"payment_method": "check", "bank": "BANPRO"}'
        ctx = {"payment_method": "check", "bank": "BDF"}
        self.assertFalse(_condition_matches(cond, ctx))

    def test_condition_matches_none(self) -> None:
        """_condition_matches con condicion None siempre es True (fallback)."""
        from cacao_accounting.document_identifiers import _condition_matches

        self.assertTrue(_condition_matches(None, {}))
        self.assertTrue(_condition_matches(None, {"payment_method": "wire"}))

    def test_resolve_external_counter_with_condition(self) -> None:
        """_resolve_external_counter debe seleccionar el contador que cumple la condicion."""
        from cacao_accounting.database import SeriesExternalCounterMap
        from cacao_accounting.document_identifiers import _resolve_external_counter

        ns = self._make_series()
        counter_check = self._make_counter("Chequera BANPRO")
        counter_wire = self._make_counter("Transferencias")

        self.db.session.add(
            SeriesExternalCounterMap(
                naming_series_id=ns.id,  # type: ignore[union-attr]
                external_counter_id=counter_check.id,  # type: ignore[union-attr]
                priority=1,
                condition_json='{"payment_method": "check"}',
            )
        )
        self.db.session.add(
            SeriesExternalCounterMap(
                naming_series_id=ns.id,  # type: ignore[union-attr]
                external_counter_id=counter_wire.id,  # type: ignore[union-attr]
                priority=2,
                condition_json=None,
            )
        )
        self.db.session.flush()

        resolved = _resolve_external_counter(
            naming_series_id=ns.id,  # type: ignore[union-attr]
            context={"payment_method": "check"},
        )
        self.assertIsNotNone(resolved)
        self.assertEqual(resolved.id, counter_check.id)  # type: ignore[union-attr]

    def test_resolve_external_counter_fallback_to_no_condition(self) -> None:
        """_resolve_external_counter debe caer al contador sin condicion si ninguna coincide."""
        from cacao_accounting.database import SeriesExternalCounterMap
        from cacao_accounting.document_identifiers import _resolve_external_counter

        ns = self._make_series()
        counter_check = self._make_counter("Chequera BDF")
        counter_default = self._make_counter("Predeterminado")

        self.db.session.add(
            SeriesExternalCounterMap(
                naming_series_id=ns.id,  # type: ignore[union-attr]
                external_counter_id=counter_check.id,  # type: ignore[union-attr]
                priority=1,
                condition_json='{"payment_method": "check"}',
            )
        )
        self.db.session.add(
            SeriesExternalCounterMap(
                naming_series_id=ns.id,  # type: ignore[union-attr]
                external_counter_id=counter_default.id,  # type: ignore[union-attr]
                priority=0,
                condition_json=None,
            )
        )
        self.db.session.flush()

        resolved = _resolve_external_counter(
            naming_series_id=ns.id,  # type: ignore[union-attr]
            context={"payment_method": "wire"},
        )
        self.assertIsNotNone(resolved)
        self.assertEqual(resolved.id, counter_default.id)  # type: ignore[union-attr]

    def test_resolve_external_counter_returns_none_if_no_mapping(self) -> None:
        """_resolve_external_counter debe retornar None si no hay mapeos."""
        from cacao_accounting.document_identifiers import _resolve_external_counter

        ns = self._make_series()
        resolved = _resolve_external_counter(naming_series_id=ns.id)  # type: ignore[union-attr]
        self.assertIsNone(resolved)

    def test_resolve_external_counter_explicit_id(self) -> None:
        """_resolve_external_counter debe usar el counter explicitamente indicado."""
        from cacao_accounting.document_identifiers import _resolve_external_counter

        ns = self._make_series()
        counter = self._make_counter("Chequera Explicita")
        resolved = _resolve_external_counter(
            naming_series_id=ns.id,  # type: ignore[union-attr]
            explicit_counter_id=counter.id,  # type: ignore[union-attr]
        )
        self.assertIsNotNone(resolved)
        self.assertEqual(resolved.id, counter.id)  # type: ignore[union-attr]


class TestExternalNumberUsage(unittest.TestCase):
    """Pruebas para ExternalNumberUsage — GAP 2 y GAP 3."""

    def setUp(self) -> None:
        self.app = create_app({**configuracion, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
        self.ctx = self.app.app_context()
        self.ctx.push()
        from cacao_accounting.database import database

        database.create_all()
        self.db = database
        self._add_entity()

    def tearDown(self) -> None:
        self.db.session.rollback()
        self.ctx.pop()

    def _add_entity(self, code: str = "ent") -> None:
        from cacao_accounting.database import Entity

        self.db.session.add(Entity(code=code, name=code, company_name=code, tax_id="J0003", currency="NIO"))
        self.db.session.flush()

    def _make_counter(self, last_used: int = 0) -> object:
        from cacao_accounting.database import ExternalCounter

        c = ExternalCounter(
            company="ent",
            name="Chequera Test",
            counter_type="checkbook",
            prefix="CHK-",
            last_used=last_used,
            padding=5,
            is_active=True,
        )
        self.db.session.add(c)
        self.db.session.flush()
        return c

    def test_external_number_usage_persists(self) -> None:
        """ExternalNumberUsage debe persistir correctamente."""
        from cacao_accounting.database import ExternalNumberUsage

        counter = self._make_counter()
        usage = ExternalNumberUsage(
            external_counter_id=counter.id,  # type: ignore[union-attr]
            external_number="CHK-00042",
            entity_type="payment_entry",
            entity_id="fake-id-001",
            sequence_value=42,
        )
        self.db.session.add(usage)
        self.db.session.flush()

        loaded = self.db.session.get(ExternalNumberUsage, usage.id)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.external_number, "CHK-00042")
        self.assertEqual(loaded.sequence_value, 42)

    def test_validate_and_register_prevents_duplicate(self) -> None:
        """_validate_and_register_external_number debe fallar ante numero duplicado."""
        from cacao_accounting.database import ExternalCounter
        from cacao_accounting.document_identifiers import (
            ExternalNumberDuplicateError,
            _validate_and_register_external_number,
        )

        counter = self._make_counter()
        _validate_and_register_external_number(
            counter=counter,  # type: ignore[arg-type]
            external_number="CHK-00099",
            entity_type="payment_entry",
            entity_id="doc-001",
        )
        self.db.session.flush()

        with self.assertRaises(ExternalNumberDuplicateError):
            _validate_and_register_external_number(
                counter=counter,  # type: ignore[arg-type]
                external_number="CHK-00099",
                entity_type="payment_entry",
                entity_id="doc-002",
            )

    def test_validate_and_register_updates_last_used(self) -> None:
        """_validate_and_register_external_number debe actualizar last_used."""
        from cacao_accounting.database import ExternalCounter
        from cacao_accounting.document_identifiers import _validate_and_register_external_number

        counter = self._make_counter(last_used=100)
        _validate_and_register_external_number(
            counter=counter,  # type: ignore[arg-type]
            external_number="CHK-00150",
            entity_type="payment_entry",
            entity_id="doc-003",
        )
        refreshed = self.db.session.get(ExternalCounter, counter.id)  # type: ignore[union-attr]
        self.assertEqual(refreshed.last_used, 150)

    def test_docbase_has_external_fields(self) -> None:
        """PaymentEntry (DocBase) debe tener external_counter_id y external_number."""
        from cacao_accounting.database import PaymentEntry

        pe = PaymentEntry(payment_type="pay", docstatus=0)
        # Verificar que los atributos existen en la clase (GAP 2)
        self.assertTrue(hasattr(pe, "external_counter_id"))
        self.assertTrue(hasattr(pe, "external_number"))


if __name__ == "__main__":
    unittest.main()
