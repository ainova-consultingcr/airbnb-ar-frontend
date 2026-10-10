import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException

from modules.asada_support import auth, monitor, routes
from modules.asada_support.monitor import admin_summary, anomaly_context, answer_question
from modules.asada_support.schemas import Login


class AsadaSupportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.original_database = auth.DATABASE_PATH
        auth.DATABASE_PATH = Path(self.temp.name) / "avi-access.sqlite3"

    def tearDown(self):
        auth.DATABASE_PATH = self.original_database
        self.temp.cleanup()

    def remote_user(self, role="FONTANERO"):
        permissions = {"ADMIN":["summary","anomalies","orders"],
                       "OPERADOR":["summary","anomalies","orders"],
                       "FONTANERO":["anomalies","orders"], "LECTOR":[]}
        return {"id":4,"entity_id":"asada_demo","username":"font1",
                "full_name":"Fontanero Uno","role":role,"active":True,
                "permissions":permissions[role]}

    def test_login_and_status_are_delegated_to_asada_monitor(self):
        session = {**self.remote_user(), "access_token":"asada-token", "token_type":"bearer"}
        with patch.object(routes, "enabled_entity", return_value={"id":"asada_demo"}), \
             patch.object(routes, "login_monitor", return_value=session) as login, \
             patch.object(routes, "require_monitor_user", return_value=self.remote_user()) as validate:
            result = routes.login("asada_demo", Login(username="font1", password="Clave-ASADA-2026"))
            state = routes.status("asada_demo", "Bearer asada-token")
        self.assertEqual(result["access_token"], "asada-token")
        self.assertEqual(state["user"]["role"], "FONTANERO")
        login.assert_called_once()
        validate.assert_called_once()
        self.assertFalse(hasattr(routes, "setup"))
        self.assertFalse(hasattr(routes, "create_user"))

    def test_asada_roles_are_mapped_to_avi_permissions(self):
        remote = {"id":9,"username":"operador1","full_name":"Operación",
                  "role":"OPERADOR","active":True,"access_token":"asada-token"}
        with patch.object(monitor, "auth_monitor", return_value=remote) as authenticate:
            session = monitor.login_monitor({"id":"asada_demo"}, "asada_demo",
                                            "operador1", "Clave-ASADA-2026")
        self.assertEqual(session["permissions"], ["summary", "anomalies", "orders"])
        self.assertEqual(session["access_token"], "asada-token")
        authenticate.assert_called_once_with(
            {"id":"asada_demo"}, "/api/auth/login", method="POST",
            payload={"username":"operador1", "password":"Clave-ASADA-2026"})
        reader = monitor.avi_user({"id":10,"username":"lector1","full_name":"Lectura",
                                   "role":"LECTOR","active":True}, "asada_demo")
        self.assertEqual(reader["permissions"], [])

    def test_fontanero_receives_unassigned_and_own_orders(self):
        user = {"username":"font1","full_name":"Fontanero Uno","role":"FONTANERO"}
        nodes = [{"node_id":"n1","sector_name":"Norte","pressure_psi":2.1,
                  "flow_lpm":13.4,"severity":"CRITICA"}]
        orders = [{"id":1,"assignee":"font1"},{"id":2,"assignee":"font2"},
                  {"id":3,"assignee":""}]
        context = anomaly_context(nodes, orders, user)
        self.assertEqual(len(context["anomalies"]), 1)
        self.assertIn("fuga", context["anomalies"][0]["explanation"].lower())
        self.assertEqual(context["orders"], [{"id":1,"assignee":"font1"},
                                              {"id":3,"assignee":""}])

    def test_fontanero_can_claim_and_update_order_through_avi(self):
        authorization = "Bearer asada-token"
        with patch.object(routes, "authenticated_user", return_value=({"id":"asada_demo"}, self.remote_user())), \
             patch.object(routes, "post_monitor", return_value={"id":7,"status":"EN ATENCION"}) as sender:
            claimed = routes.claim_order("asada_demo", 7, routes.WorkOrderClaim(
                expected_updated_at="2026-10-09T20:00:00Z"), authorization)
            updated = routes.update_order("asada_demo", 7, routes.WorkOrderUpdate(
                status="RESUELTA", diagnosis="FUGA CONFIRMADA", note="Reparada",
                expected_updated_at="2026-10-09T20:05:00Z"), authorization)
        self.assertEqual(claimed["status"], "EN ATENCION")
        self.assertEqual(updated["status"], "EN ATENCION")
        self.assertEqual(sender.call_count, 2)
        self.assertEqual(sender.call_args_list[0].args[2]["username"], "font1")

    def test_anomalies_and_orders_are_sorted_newest_first(self):
        user = {"username":"font1","full_name":"Fontanero Uno","role":"FONTANERO"}
        nodes = [
            {"node_id":"old","severity":"OFFLINE","timestamp":"2026-10-09T10:00:00Z"},
            {"node_id":"new","severity":"CRITICA","timestamp":"2026-10-09T10:00:03Z"},
        ]
        orders = [
            {"id":1,"assignee":"font1","created_at":"2026-10-09T09:00:00Z"},
            {"id":2,"assignee":"font1","created_at":"2026-10-09T09:05:00Z"},
        ]
        context = anomaly_context(nodes, orders, user)
        self.assertEqual([item["node_id"] for item in context["anomalies"]], ["new", "old"])
        self.assertEqual(context["anomalies"][0]["timestamp"], "2026-10-09T10:00:03Z")
        self.assertEqual([item["id"] for item in context["orders"]], [2, 1])

    def test_admin_summary_finds_top_sector_and_cause(self):
        nodes = [{"node_id":"n1","sector_name":"Norte"},{"node_id":"n2","sector_name":"Sur"}]
        orders = [
            {"node_id":"n1","diagnosis":"Tubería rota"},
            {"node_id":"n1","diagnosis":"Tubería rota"},
            {"node_id":"n2","diagnosis":"Válvula"},
        ]
        summary = admin_summary(nodes, orders)
        self.assertEqual(summary["top_sector"], "Norte")
        self.assertEqual(summary["main_cause"], "Tubería rota")

    def test_admin_question_is_grounded_in_period_summary(self):
        user = {"username":"admin","full_name":"Administración","role":"ADMIN"}
        nodes = [{"node_id":"n1","sector_name":"Norte"}]
        orders = [{"node_id":"n1","diagnosis":"FUGA CONFIRMADA"}]
        result = answer_question("¿Cuál sector tuvo más averías y cuál fue la causa?", user, nodes, orders, 30)
        self.assertIn("Norte", result["answer"])
        self.assertIn("FUGA CONFIRMADA", result["answer"])

    def test_quick_questions_have_distinct_grounded_answers(self):
        user = {"username":"font1","full_name":"Fontanero Uno","role":"FONTANERO"}
        nodes = [
            {"node_id":"n1","sector_name":"Norte","pressure_psi":2.1,"flow_lpm":13.4,"severity":"CRITICA"},
            {"node_id":"n2","sector_name":"Sur","pressure_psi":3.2,"flow_lpm":8.1,"severity":"NORMAL"},
            {"node_id":"n3","sector_name":"Este","pressure_psi":None,"flow_lpm":None,"severity":"OFFLINE"},
        ]
        orders = [{"id":1,"assignee":"font1"}]
        answers = [
            answer_question("¿Cómo interpreto la presión?", user, nodes, orders)["answer"],
            answer_question("¿Qué significa posible fuga?", user, nodes, orders)["answer"],
            answer_question("¿Cuándo aparece un nodo offline?", user, nodes, orders)["answer"],
            answer_question("¿Cuál es el estado actual de la red?", user, nodes, orders)["answer"],
        ]
        self.assertEqual(len(set(answers)), 4)
        self.assertIn("2.1 psi", answers[0])
        self.assertIn("1 alerta", answers[1])
        self.assertIn("1 nodo", answers[2])
        self.assertIn("3 nodo", answers[3])

    def test_fontanero_registers_push_and_event_is_idempotent(self):
        subscription = routes.PushSubscription(endpoint="https://push.example/device-1", keys={
            "p256dh":"a" * 64, "auth":"b" * 16,
        })
        with patch.dict("os.environ", {
            "AVI_PUSH_VAPID_PUBLIC_KEY":"public-key",
            "AVI_PUSH_VAPID_PRIVATE_KEY":"private-key",
            "ASADA_EVENT_SERVICE_KEY":"event-secret",
        }, clear=False):
            with patch.object(routes, "authenticated_user", return_value=({"id":"asada_demo"}, self.remote_user())):
                config = routes.push_config("asada_demo", "Bearer asada-token")
                self.assertTrue(config["enabled"])
                routes.subscribe_push("asada_demo", subscription, "Bearer asada-token")
            event = routes.AlertEvent(source_order_id=7, node_id="n1", sector="Norte",
                pressure_psi=2.0, flow_lpm=13.0, timestamp="2026-10-09T10:00:00Z",
                message="Anomalía crítica sostenida")
            with patch.object(routes, "enabled_entity", return_value={"id":"asada_demo"}), \
                 patch.object(routes, "send_event", return_value={
                "delivered":1,"failed":0,"configured":True,"subscriptions":1,
            }) as sender:
                first = routes.receive_event("asada_demo", event, "event-secret")
                second = routes.receive_event("asada_demo", event, "event-secret")
            self.assertTrue(first["accepted"])
            self.assertTrue(second["duplicate"])
            sender.assert_called_once()


if __name__ == "__main__":
    unittest.main()
