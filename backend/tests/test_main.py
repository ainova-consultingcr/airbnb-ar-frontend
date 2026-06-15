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
