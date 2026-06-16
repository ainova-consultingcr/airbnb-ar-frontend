import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException


BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

import main
from reporting import build_report, demo_records, render_html_report


class EmptyOpenAI:
    def __init__(self, api_key=None):
        self.chat = SimpleNamespace(
            completions=SimpleNamespace(
                create=lambda **kwargs: SimpleNamespace(
                    choices=[SimpleNamespace(message=SimpleNamespace(content=None))]
                )
            )
        )


class MainTests(unittest.TestCase):
    def test_property_loading_does_not_depend_on_working_directory(self):
        original_cwd = os.getcwd()
        try:
            os.chdir(os.path.dirname(BACKEND_DIR))
            response = main.get_property("hotel_demo")
        finally:
            os.chdir(original_cwd)

        self.assertEqual(response["id"], "hotel_demo")
        self.assertIn(
            "¿Qué lugares turísticos puedo visitar?", response["suggestions"]["es"]
        )
        self.assertIn(
            "¿Qué restaurantes recomiendan?", response["suggestions"]["es"]
        )
        self.assertIn(
            "¿Qué servicios y tiendas hay cerca?", response["suggestions"]["es"]
        )

    def test_missing_or_invalid_property_returns_404(self):
        for property_id in ("missing_property", "../backend"):
            with self.subTest(property_id=property_id):
                with self.assertRaises(HTTPException) as error:
                    main.get_property(property_id)
                self.assertEqual(error.exception.status_code, 404)

    def test_transport_uses_entity_configuration(self):
        response = main.ask(
            main.AskRequest(
                property_id="hotel_demo",
                question="Necesito transporte al aeropuerto",
                language="es",
            )
        )

        self.assertIn("$80", response["answer"])
        self.assertEqual(response["cta_options"][0]["type"], "transport")
        self.assertEqual(
            response["cta_options"][0]["data"]["whatsapp"], "50686380783"
        )

    def test_tourist_places_include_official_and_map_urls(self):
        response = main.ask(
            main.AskRequest(
                property_id="hotel_demo",
                question="¿Qué lugares turísticos puedo visitar?",
                language="es",
            )
        )

        self.assertGreaterEqual(len(response["place_options"]), 6)
        for place in response["place_options"]:
            self.assertTrue(place["info_url"].startswith("https://"))
            self.assertTrue(place["map_url"].startswith("https://"))

    def test_restaurants_are_returned_as_cards(self):
        response = main.ask(
            main.AskRequest(
                property_id="hotel_demo",
                question="¿Qué restaurantes recomiendan?",
                language="es",
            )
        )

        self.assertEqual(len(response["restaurant_options"]), 3)
        for restaurant in response["restaurant_options"]:
            self.assertTrue(restaurant["map_url"].startswith("https://"))
            self.assertTrue(restaurant["whatsapp"])
            self.assertTrue(restaurant["summary"]["es"])

        english_response = main.ask(
            main.AskRequest(
                property_id="hotel_demo",
                question="Which restaurants do you recommend?",
                language="en",
            )
        )
        self.assertEqual(len(english_response["restaurant_options"]), 3)

    def test_nearby_businesses_can_be_listed_or_filtered(self):
        response = main.ask(
            main.AskRequest(
                property_id="hotel_demo",
                question="¿Qué servicios y tiendas hay cerca?",
                language="es",
            )
        )
        self.assertEqual(len(response["business_options"]), 4)

        pharmacy_response = main.ask(
            main.AskRequest(
                property_id="hotel_demo",
                question="¿Dónde hay una farmacia?",
                language="es",
            )
        )
        self.assertEqual(len(pharmacy_response["business_options"]), 1)
        self.assertEqual(pharmacy_response["business_options"][0]["type"], "pharmacy")

    def test_professional_report_can_be_rendered(self):
        report = build_report(demo_records(), property_id="hotel_demo")
        html = render_html_report(report)

        self.assertEqual(report["total_questions"], 4)
        self.assertEqual(report["lead_count"], 2)
        self.assertIn("Reporte ejecutivo del asistente", html)
        self.assertIn("Preguntas más frecuentes", html)

    @patch.object(main, "log_question")
    @patch.object(main, "OpenAI", EmptyOpenAI)
    def test_empty_openai_response_returns_safe_fallback(self, log_question):
        response = main.ask(
            main.AskRequest(
                property_id="hotel_demo",
                question="¿Hay un gimnasio privado?",
                language="es",
            )
        )

        self.assertEqual(response["answer"], main.NO_INFO_MESSAGES["es"])
        log_question.assert_called_once()


if __name__ == "__main__":
    unittest.main()
