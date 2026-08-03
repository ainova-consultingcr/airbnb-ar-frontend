import unittest

from farmasi_orders import create_order, list_orders
from farmasi_sellers import public_seller


class FarmasiMultiSellerTests(unittest.TestCase):
    def test_public_profiles_are_distinct(self):
        self.assertNotEqual(public_seller("ana")["id"], public_seller("maria")["id"])
        self.assertIsNone(public_seller("missing"))

    def test_orders_are_isolated_by_seller_and_customer(self):
        ana = create_order({
            "property_id": "farmasi",
            "seller_id": "seller-ana-001",
            "customer_session_id": "customer-a",
            "items": [{"sku": "1", "name": "Producto A", "price": 10, "quantity": 1}],
        })
        maria = create_order({
            "property_id": "farmasi",
            "seller_id": "seller-maria-002",
            "customer_session_id": "customer-b",
            "items": [{"sku": "2", "name": "Producto B", "price": 20, "quantity": 1}],
        })
        self.assertEqual(ana["customer_session_id"], "customer-a")
        self.assertEqual(maria["customer_session_id"], "customer-b")
        self.assertTrue(all(row["seller_id"] == "seller-ana-001" for row in list_orders("farmasi", "seller-ana-001")))
        self.assertTrue(all(row["seller_id"] == "seller-maria-002" for row in list_orders("farmasi", "seller-maria-002")))
