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
from rag import build_context, load_property_data


class EmptyOpenAI:
    def __init__(self, api_key=None):
        self.chat = SimpleNamespace(
            completions=SimpleNamespace(
                create=lambda **kwargs: SimpleNamespace(
                    choices=[SimpleNamespace(message=SimpleNamespace(content=None))]
                )
            )
        )


class CaptureOpenAI:
    last_kwargs = None

    def __init__(self, api_key=None):
        self.chat = SimpleNamespace(
            completions=SimpleNamespace(create=self._create)
        )

    def _create(self, **kwargs):
        CaptureOpenAI.last_kwargs = kwargs
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="Claro, te ayudo con ese repuesto."))]
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
            if restaurant.get("has_own_restaurant"):
                self.assertNotIn("directions_url", restaurant)
            else:
                self.assertTrue(restaurant["directions_url"].startswith("https://"))
            self.assertNotIn("map_url", restaurant)
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

    def test_new_food_question_ignores_stale_business_context(self):
        response = main.ask(
            main.AskRequest(
                property_id="hotel_demo",
                question="comer",
                language="es",
                conversation_context={
                    "type": "last_action",
                    "action_type": "nearby_businesses",
                    "topic": "servicios cercanos",
                    "item": {
                        "name": {"es": "Tiendas de ropa", "en": "Clothing stores"},
                        "type": "clothing",
                    },
                },
            )
        )

        self.assertIn("restaurant_options", response)
        self.assertNotIn("business_options", response)

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

        clothing_response = main.ask(
            main.AskRequest(
                property_id="hotel_demo",
                question="donde ir a comprar ropa",
                language="es",
            )
        )
        self.assertIn("business_options", clothing_response)
        self.assertNotIn("place_options", clothing_response)
        self.assertEqual(len(clothing_response["business_options"]), 1)
        self.assertEqual(clothing_response["business_options"][0]["type"], "clothing")

    def test_professional_report_can_be_rendered(self):
        report = build_report(demo_records(), property_id="hotel_demo")
        html = render_html_report(report)

        self.assertEqual(report["total_questions"], 4)
        self.assertEqual(report["lead_count"], 2)
        self.assertIn("Reporte ejecutivo del asistente", html)
        self.assertIn("Preguntas más frecuentes", html)

    def test_auto_parts_entity_loads_catalog_and_sales_context(self):
        entity = load_property_data("auto_parts_demo")
        context = build_context(entity)

        self.assertEqual(entity["type"], "auto_parts_store")
        self.assertGreaterEqual(len(entity["catalog"]), 5)
        self.assertIn("Pastillas de freno delanteras", context)
        self.assertIn("Active offers", context)
        self.assertIn("Preventive wear suggestions", context)

    def test_hardware_entity_loads_guided_sales_data(self):
        entity = load_property_data("ferreteria_demo")
        context = build_context(entity)
        property_response = main.get_property("ferreteria_demo")

        self.assertEqual(entity["type"], "hardware_store")
        self.assertGreaterEqual(len(entity["catalog"]), 5)
        self.assertIn("Pasillo 4", context)
        self.assertIn("Serrucho para madera", context)
        self.assertIn("DIY guides", context)
        self.assertIn("Workshops and talks", context)
        self.assertIn("Semana de pintura", context)
        self.assertIn("hardware", property_response)
        self.assertGreaterEqual(len(property_response["hardware"]["store_sections"]), 5)
        self.assertGreaterEqual(len(property_response["hardware"]["workshops"]), 3)

    @patch.object(main, "log_question")
    @patch.object(main, "OpenAI", CaptureOpenAI)
    def test_general_answer_followup_can_continue_context(self, log_question):
        context = {
            "type": "last_action",
            "action_type": "general_answer",
            "topic": "serrucho",
            "item": {
                "name": "serrucho",
                "summary": {
                    "es": "El serrucho esta en el Pasillo 2, seccion de sierras manuales."
                },
            },
        }

        response = main.ask(
            main.AskRequest(
                property_id="ferreteria_demo",
                question="algo mas",
                language="es",
                conversation_context=context,
            )
        )

        user_message = CaptureOpenAI.last_kwargs["messages"][-1]["content"]

        self.assertIn("serrucho", user_message)
        self.assertIn("sin empezar desde cero", user_message)
        self.assertEqual(response["answer"], "Claro, te ayudo con ese repuesto.")

    @patch.object(main, "log_question")
    @patch.object(main, "OpenAI", CaptureOpenAI)
    def test_hardware_followup_keeps_guided_context(self, log_question):
        context = {
            "type": "hardware_search",
            "action_type": "hardware_search",
            "topic": "Pintura",
            "item": {
                "name": "Pintura latex blanca 1 galon",
                "category": "pintura",
                "sku": "PNT-LTX-BLANCO-GL",
                "aisle": "Pasillo 4",
                "bay": "Seccion 4B",
                "related_parts": ["rodillo", "brocha", "cinta masking"],
            },
            "options": [
                {"name": "Pintura latex blanca 1 galon"},
                {"title": {"es": "Semana de pintura"}, "id": "paint_week"},
            ],
        }

        response = main.ask(
            main.AskRequest(
                property_id="ferreteria_demo",
                question="si",
                language="es",
                conversation_context=context,
            )
        )

        messages = CaptureOpenAI.last_kwargs["messages"]
        user_message = messages[-1]["content"]
        system_context = "\n".join(
            message["content"] for message in messages if message["role"] == "system"
        )

        self.assertIn("Pintura latex blanca 1 galon", user_message)
        self.assertIn("Pasillo 4", user_message)
        self.assertIn("complementos utiles", user_message)
        self.assertIn("guided hardware-store sales flow", system_context)
        self.assertIn("Semana de pintura", system_context)
        self.assertEqual(response["answer"], "Claro, te ayudo con ese repuesto.")

    def test_negative_followup_offers_related_options_then_resets(self):
        context = {
            "type": "hardware_search",
            "action_type": "hardware_search",
            "topic": "Pintura",
            "item": {
                "name": "Pintura latex blanca 1 galon",
                "category": "pintura",
                "aisle": "Pasillo 4",
                "related_parts": ["rodillo", "brocha", "cinta masking"],
            },
            "options": [
                {"title": {"es": "Semana de pintura"}, "id": "paint_week"},
            ],
        }

        first_no = main.ask(
            main.AskRequest(
                property_id="ferreteria_demo",
                question="no",
                language="es",
                conversation_context=context,
            )
        )

        self.assertIn("Tambien puedo ayudarte", first_no["answer"])
        self.assertIn("rodillo", first_no["answer"])
        self.assertNotIn("reset_context", first_no)

        second_context = {**context, "decline_count": 1}
        second_no = main.ask(
            main.AskRequest(
                property_id="ferreteria_demo",
                question="no",
                language="es",
                conversation_context=second_context,
            )
        )

        self.assertIn("Quedo atento", second_no["answer"])
        self.assertTrue(second_no["reset_context"])

    @patch.object(main, "log_question")
    @patch.object(main, "OpenAI", CaptureOpenAI)
    def test_auto_parts_followup_keeps_guided_context(self, log_question):
        context = {
            "type": "auto_parts_search",
            "vehicle": {"make": "Toyota", "model": "Corolla", "year": "2012"},
            "part": {
                "name": "Pastillas de freno delanteras",
                "category": "frenos",
                "sku": "BRK-COR-09-13-F",
                "related_parts": ["discos de freno", "líquido de frenos"],
            },
            "offers": [
                {
                    "id": "brake_week",
                    "title": {"es": "Semana de frenos"},
                    "categories": ["frenos"],
                    "active": True,
                }
            ],
        }

        response = main.ask(
            main.AskRequest(
                property_id="auto_parts_demo",
                question="sí",
                language="es",
                conversation_context=context,
            )
        )

        messages = CaptureOpenAI.last_kwargs["messages"]
        user_message = messages[-1]["content"]
        system_context = "\n".join(
            message["content"] for message in messages if message["role"] == "system"
        )

        self.assertIn("Toyota Corolla 2012", user_message)
        self.assertIn("Pastillas de freno delanteras", user_message)
        self.assertIn("sin empezar desde cero", user_message)
        self.assertIn("ACTIVE CONVERSATION CONTEXT", system_context)
        self.assertIn("Semana de frenos", system_context)
        self.assertEqual(response["answer"], "Claro, te ayudo con ese repuesto.")

    @patch.object(main, "log_question")
    @patch.object(main, "OpenAI", CaptureOpenAI)
    def test_hotel_followup_keeps_last_action_context(self, log_question):
        context = {
            "type": "last_action",
            "action_type": "restaurants",
            "topic": "restaurantes",
            "item": {
                "name": "La Oveja",
                "summary": {"es": "Restaurante recomendado por el hotel."},
                "whatsapp": "50600000000",
                "map_url": "https://maps.google.com/",
            },
            "options": [
                {"name": "La Oveja", "type": "restaurant"},
                {"name": "La Barca", "type": "restaurant"},
            ],
        }

        response = main.ask(
            main.AskRequest(
                property_id="hotel_demo",
                question="si",
                language="es",
                conversation_context=context,
            )
        )

        messages = CaptureOpenAI.last_kwargs["messages"]
        user_message = messages[-1]["content"]
        system_context = "\n".join(
            message["content"] for message in messages if message["role"] == "system"
        )

        self.assertIn("La Oveja", user_message)
        self.assertIn("restaurantes", user_message)
        self.assertIn("sin empezar desde cero", user_message)
        self.assertIn("ACTIVE CONVERSATION CONTEXT", system_context)
        self.assertIn("Recently shown options: La Oveja, La Barca", system_context)
        self.assertEqual(response["answer"], "Claro, te ayudo con ese repuesto.")

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
