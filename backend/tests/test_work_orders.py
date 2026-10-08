import os
import tempfile
import unittest
from unittest.mock import patch

from modules.work_orders.service import (
    authenticate, audit_history, convert_request, create_request, customer_decide,
    customer_tracking, list_requests, login, save_estimate, update_status,
)


class WorkOrderFlowTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        os.environ["AVI_WORKSHOP_DB"] = os.path.join(self.tempdir.name, "workshop.db")
        os.environ["AVI_WORKSHOP_ADVISOR_USER"] = "advisor-test"
        os.environ["AVI_WORKSHOP_ADVISOR_PASSWORD"] = "safe-test-password"
        self.request_payload = {
            "customer_name": "María Cliente", "phone": "88881234", "consent_to_contact": True,
            "vehicle_make": "Toyota", "vehicle_model": "Corolla", "vehicle_year": 2018,
            "plate": "ABC123", "vin": None, "mileage": 90000,
            "problem": "Ruido fuerte al aplicar los frenos", "preferred_date": "2026-09-01",
        }

    def tearDown(self):
        self.tempdir.cleanup()
        for key in ("AVI_WORKSHOP_DB", "AVI_WORKSHOP_ADVISOR_USER", "AVI_WORKSHOP_ADVISOR_PASSWORD", "AVI_WORKSHOP_WHATSAPP_NUMBER", "AVI_WORKSHOP_WHATSAPP_BY_SLUG", "AVI_WORKSHOP_APPS_SCRIPT_URL", "AVI_WORKSHOP_INTEGRATION_SECRET"):
            os.environ.pop(key, None)

    def test_whatsapp_configuration_is_sanitized_and_optional(self):
        os.environ["AVI_WORKSHOP_WHATSAPP_NUMBER"] = "+506 8000-0000"
        workshop = __import__("modules.work_orders.service", fromlist=["workshop_by_slug"]).workshop_by_slug("ruta27")
        self.assertEqual(workshop["whatsapp_number"], "50680000000")

        os.environ["AVI_WORKSHOP_WHATSAPP_NUMBER"] = "not-a-number"
        workshop = __import__("modules.work_orders.service", fromlist=["workshop_by_slug"]).workshop_by_slug("ruta27")
        self.assertIsNone(workshop["whatsapp_number"])

        os.environ["AVI_WORKSHOP_WHATSAPP_BY_SLUG"] = '{"ruta27":"50681112222","otro":"50689990000"}'
        workshop = __import__("modules.work_orders.service", fromlist=["workshop_by_slug"]).workshop_by_slug("ruta27")
        self.assertEqual(workshop["whatsapp_number"], "50681112222")

    def test_complete_persistent_audited_flow(self):
        created = create_request("ruta27", self.request_payload)
        session = login("ruta27", "advisor-test", "safe-test-password")
        self.assertIsNotNone(session)
        actor = authenticate(session["access_token"], "ruta27")
        self.assertEqual(len(list_requests("ruta27")), 1)

        order = convert_request("ruta27", created["id"], actor, {"technician": "Técnico Uno", "advisor_note": "Vehículo recibido"})
        estimate = save_estimate("ruta27", order["id"], actor, {
            "diagnosis": "Pastillas delanteras agotadas", "currency": "CRC", "tax_rate": 0.13,
            "promised_date": "2026-09-02", "lines": [
                {"kind": "part", "description": "Pastillas delanteras", "sku": "BRK-1", "quantity": 1, "unit_price": 40000},
                {"kind": "labor", "description": "Servicio de frenos", "sku": None, "quantity": 1, "unit_price": 20000},
            ],
        })
        self.assertEqual(estimate["status"], "awaiting_approval")
        self.assertEqual(estimate["total"], 67800)

        approved = customer_decide("ruta27", order["id"], created["tracking_token"], "approved", "Autorizado")
        self.assertEqual(approved["status"], "approved")
        for status in ("in_progress", "quality_check", "ready", "delivered"):
            approved = update_status("ruta27", order["id"], actor, status, f"Estado {status}")
        self.assertEqual(approved["status"], "delivered")

        tracking = customer_tracking("ruta27", created["id"], created["tracking_token"])
        self.assertEqual(tracking["work_order"]["status"], "delivered")
        self.assertGreaterEqual(len(tracking["history"]), 8)
        self.assertGreaterEqual(len(audit_history("ruta27", order["id"])), 7)

    def test_consent_and_tokens_are_enforced(self):
        invalid = dict(self.request_payload, consent_to_contact=False)
        with self.assertRaises(ValueError): create_request("ruta27", invalid)
        created = create_request("ruta27", self.request_payload)
        with self.assertRaises(PermissionError): customer_tracking("ruta27", created["id"], "wrong-token")
        self.assertIsNone(login("ruta27", "advisor-test", "wrong-password"))

    def test_invalid_transition_is_rejected(self):
        created = create_request("ruta27", self.request_payload)
        session = login("ruta27", "advisor-test", "safe-test-password")
        actor = authenticate(session["access_token"], "ruta27")
        order = convert_request("ruta27", created["id"], actor, {})
        with self.assertRaises(ValueError): update_status("ruta27", order["id"], actor, "ready", None)

    @patch("modules.work_orders.service.sync_inspection", return_value=True)
    @patch("modules.work_orders.service.book_inspection", return_value={"event_id": "calendar-event-test"})
    def test_inspection_is_only_persisted_after_calendar_confirmation(self, book, sync):
        from modules.work_orders.service import reserve_inspection
        created = create_request("ruta27", self.request_payload)
        tracking = reserve_inspection("ruta27", created["id"], created["tracking_token"], "2026-09-01T14:00:00Z", "2026-09-01T15:00:00Z")
        self.assertEqual(tracking["request"]["status"], "scheduled")
        self.assertEqual(tracking["request"]["calendar_event_id"], "calendar-event-test")
        self.assertEqual(book.call_args.args[0]["request_code"], created["code"])
        self.assertNotIn("phone", book.call_args.args[0])
        self.assertTrue(sync.called)


if __name__ == "__main__": unittest.main()
