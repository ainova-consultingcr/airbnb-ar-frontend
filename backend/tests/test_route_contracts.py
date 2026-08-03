import unittest
from unittest.mock import patch

from fastapi import HTTPException

import main


class RouteContractTests(unittest.TestCase):
    def test_modular_routes_preserve_paths_and_methods_once(self):
        expected = {
            ("/service-requests/{request_id}", "GET"),
            ("/service-requests/{request_id}/confirm", "POST"),
            ("/farmasi/order-requests", "POST"),
            ("/farmasi/order-requests", "GET"),
            ("/farmasi/order-requests/{order_id}", "PATCH"),
            ("/farmasi/sellers/{seller_slug}", "GET"),
            ("/farmasi/seller/login", "POST"),
            ("/farmasi/seller/logout", "POST"),
        }
        registered = [
            (route.path, method)
            for route in main.app.routes
            for method in (route.methods or set())
            if (route.path, method) in expected
        ]
        self.assertEqual(set(registered), expected)
        self.assertEqual(len(registered), len(expected))

    def test_historical_dto_names_remain_available_from_main(self):
        self.assertEqual(main.ServiceRequestConfirmation.__name__, "ServiceRequestConfirmation")
        self.assertEqual(main.FarmasiOrderRequest.__name__, "ShoppingRequest")
        self.assertEqual(main.FarmasiOrderItem.__name__, "ShoppingItem")
        self.assertEqual(main.FarmasiOrderStatus.__name__, "ShoppingStatus")
        self.assertEqual(main.FarmasiSellerLogin.__name__, "SellerLogin")

    @patch("modules.shopping.routes.require_entity_module")
    def test_disabled_shopping_returns_controlled_error_before_execution(self, require_module):
        require_module.side_effect = HTTPException(status_code=403, detail="shopping disabled")
        payload = main.FarmasiOrderRequest(
            property_id="entity_a",
            seller_id="seller-ana-001",
            customer_session_id="guest-1",
            items=[main.FarmasiOrderItem(sku="SKU-1", name="Item", price=1, quantity=1)],
        )
        with self.assertRaises(HTTPException) as raised:
            main.create_farmasi_order_request(payload)
        self.assertEqual(raised.exception.status_code, 403)
