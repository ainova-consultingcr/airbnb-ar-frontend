import json
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException

import main
from core.modules import MODULE_REGISTRY, apply_module_configuration
from modules.faqs.service import build_faq_response
from modules.requests.flow import handle_service_request


FIXTURES = Path(__file__).parent / "fixtures" / "entities"


def fixture_entity(name):
    return json.loads((FIXTURES / name / "entity.json").read_text(encoding="utf-8"))


class ModularFlowTests(unittest.TestCase):
    def test_entity_a_disables_shopping_without_affecting_other_modules(self):
        entity = apply_module_configuration({
            **fixture_entity("entity_a"),
            "faqs": [{"question": "WiFi", "answer": "Disponible"}],
            "catalog": [{"sku": "A"}],
        })
        self.assertFalse(MODULE_REGISTRY.is_enabled(entity, "shopping"))
        self.assertEqual(entity["faqs"][0]["answer"], "Disponible")
        self.assertEqual(entity["catalog"][0]["sku"], "A")

    def test_entity_b_disables_requests_without_affecting_catalog(self):
        entity = apply_module_configuration({
            **fixture_entity("entity_b"),
            "catalog": [{"sku": "B"}],
            "service_requests": {"enabled": True},
        })
        self.assertFalse(entity["service_requests"]["enabled"])
        self.assertEqual(entity["catalog"][0]["sku"], "B")

    @patch("core.http.load_property_data")
    def test_disabled_request_endpoint_returns_controlled_error(self, load_entity):
        load_entity.return_value = apply_module_configuration(fixture_entity("entity_b"))
        with self.assertRaises(HTTPException) as raised:
            main.service_request_status("AVI-SOL-1", "entity_b", "guest-1")
        self.assertEqual(raised.exception.status_code, 403)

    def test_existing_entity_data_is_unchanged_without_configuration(self):
        entity = {"id": "legacy", "faqs": [{"question": "Q", "answer": "A"}], "catalog": [{"sku": "1"}]}
        self.assertEqual(apply_module_configuration(entity), entity)

    @patch("modules.requests.flow.classify_service_request")
    def test_disabled_requests_do_not_participate_in_ask_flow(self, classify):
        entity = apply_module_configuration({
            **fixture_entity("entity_b"),
            "type": "hotel",
        })
        response = handle_service_request(
            entity=entity,
            property_id="entity_b",
            question="Necesito dos toallas",
            room_id="204",
            guest_session_id="guest-1",
            lang_key="es",
            webhook_url="unused",
        )
        self.assertIsNone(response)
        classify.assert_not_called()

    def test_disabled_faqs_do_not_return_direct_answers(self):
        entity = apply_module_configuration({
            "id": "catalog_only",
            "enabled_modules": ["catalog"],
            "faqs": [{"question": "WiFi", "answer": "Disponible"}],
            "catalog": [{"sku": "A"}],
        })
        response = build_faq_response(
            "WiFi",
            entity,
            suggestions={},
            normalize=lambda value: value.lower(),
        )
        self.assertIsNone(response)
