import os
import sys
import unittest
from unittest.mock import patch

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

import main
from reporting import build_report
from service_requests import classify_service_request, is_accommodation_entity
from rag import load_property_data


class ServiceRequestTests(unittest.TestCase):
    def test_request_without_room_requires_qr(self):
        response = main.ask(main.AskRequest(
            property_id="hotel_demo", question="Necesito dos toallas", language="es"
        ))
        self.assertTrue(response["requires_room"])

    @patch.object(main, "create_service_request")
    def test_hotel_request_uses_room_and_session(self, create):
        create.return_value = {
            "id": "AVI-SOL-TEST", "room_id": "204", "description": "Necesito agua",
            "category": "Bebidas", "status": "Pendiente",
        }
        response = main.ask(main.AskRequest(
            property_id="hotel_demo", question="Necesito dos botellas de agua",
            language="es", room_id="204", guest_session_id="guest-test",
        ))
        self.assertEqual(response["service_request"]["id"], "AVI-SOL-TEST")
        self.assertEqual(create.call_args.kwargs["room_id"], "204")
        self.assertEqual(create.call_args.kwargs["category"], "Bebidas")

    def test_transport_booking_is_not_operational_request(self):
        self.assertIsNone(classify_service_request("Necesito transporte al aeropuerto"))
        self.assertFalse(is_accommodation_entity(load_property_data("farmasi")))

    def test_report_includes_requests(self):
        report = build_report([{
            "type": "service_request", "property": "hotel_demo",
            "request_id": "AVI-SOL-1", "status": "Entregada",
            "category": "Amenidades", "guest_confirmation": "Confirmada", "rating": 5,
        }], property_id="hotel_demo")
        self.assertEqual(report["request_total"], 1)
        self.assertEqual(report["request_confirmed_rate"], 100)
        self.assertEqual(report["request_average_rating"], 5.0)


if __name__ == "__main__":
    unittest.main()