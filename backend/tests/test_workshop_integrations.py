import json
import os
import unittest
from unittest.mock import patch

from modules.work_orders.integrations import IntegrationUnavailable, available_slots, command


class _Response:
    status = 200
    def __init__(self, payload): self.payload = payload
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self): return json.dumps(self.payload).encode()


class WorkshopIntegrationTests(unittest.TestCase):
    def tearDown(self):
        os.environ.pop("AVI_WORKSHOP_APPS_SCRIPT_URL", None)
        os.environ.pop("AVI_WORKSHOP_INTEGRATION_SECRET", None)

    def test_unconfigured_bridge_fails_closed(self):
        with self.assertRaises(IntegrationUnavailable): command("availability")

    @patch("modules.work_orders.integrations.urllib.request.urlopen")
    def test_availability_uses_secret_without_real_google_call(self, urlopen):
        os.environ["AVI_WORKSHOP_APPS_SCRIPT_URL"] = "https://script.google.test/exec"
        os.environ["AVI_WORKSHOP_INTEGRATION_SECRET"] = "test-secret"
        urlopen.return_value = _Response({"ok": True, "slots": [{"start": "2026-09-01T14:00:00Z", "end": "2026-09-01T15:00:00Z"}]})
        slots = available_slots("2026-09-01", 7)
        self.assertEqual(len(slots), 1)
        sent = json.loads(urlopen.call_args.args[0].data.decode())
        self.assertEqual(sent["secret"], "test-secret")
        self.assertEqual(sent["action"], "availability")


if __name__ == "__main__": unittest.main()
