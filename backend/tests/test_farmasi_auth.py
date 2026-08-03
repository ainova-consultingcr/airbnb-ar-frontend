import unittest

from farmasi_auth import authenticate_seller, revoke_seller_token, validate_seller_token


class FarmasiAuthTests(unittest.TestCase):
    def test_valid_demo_credentials_create_session(self):
        session = authenticate_seller("ana", "ana", "AVI-Ana-2026")
        self.assertIsNotNone(session)
        self.assertEqual(validate_seller_token(session["access_token"])["seller_id"], "seller-ana-001")
        revoke_seller_token(session["access_token"])
        self.assertFalse(validate_seller_token(session["access_token"]))

    def test_invalid_credentials_are_rejected(self):
        self.assertIsNone(authenticate_seller("ana", "ana", "incorrecta"))


if __name__ == "__main__":
    unittest.main()
