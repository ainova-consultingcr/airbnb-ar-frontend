import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException

from modules.asada_support import auth, routes
from modules.asada_support.monitor import admin_summary, anomaly_context, answer_question
from modules.asada_support.schemas import Login, Setup, UserCreate


class AsadaSupportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.original_database = auth.DATABASE_PATH
        auth.DATABASE_PATH = Path(self.temp.name) / "avi-access.sqlite3"
        self.setup_key = patch.dict("os.environ", {"AVI_SETUP_KEY": "avi-initial-secret"})
        self.setup_key.start()

    def tearDown(self):
        self.setup_key.stop()
        auth.DATABASE_PATH = self.original_database
        self.temp.cleanup()

    def create_admin(self):
        return routes.setup("asada_demo", Setup(
            username="admin", full_name="Administración",
            password="Clave-AVI-2026", role="ADMIN",
        ), "avi-initial-secret")

    def test_avi_setup_login_and_roles_are_scoped_to_entity(self):
        admin = self.create_admin()
        self.assertEqual(admin["role"], "ADMIN")
        token = admin["access_token"]
        plumber = routes.create_user("asada_demo", UserCreate(
            username="font1", full_name="Fontanero Uno",
            password="Clave-font-2026", role="FONTANERO",
        ), f"Bearer {token}")
        self.assertEqual(plumber["role"], "FONTANERO")
        session = routes.login("asada_demo", Login(username="font1", password="Clave-font-2026"))
        self.assertEqual(session["entity_id"], "asada_demo")
        with self.assertRaises(HTTPException) as error:
            auth.require_user("otra_asada", f"Bearer {session['access_token']}")
        self.assertEqual(error.exception.status_code, 401)

    def test_only_admin_can_create_users(self):
        admin = self.create_admin()
        routes.create_user("asada_demo", UserCreate(
            username="font1", full_name="Fontanero Uno",
            password="Clave-font-2026", role="FONTANERO",
        ), f"Bearer {admin['access_token']}")
        plumber = routes.login("asada_demo", Login(username="font1", password="Clave-font-2026"))
        with self.assertRaises(HTTPException) as error:
            routes.create_user("asada_demo", UserCreate(
                username="otro", full_name="Otro Usuario",
                password="Clave-otro-2026", role="OPERADOR",
            ), f"Bearer {plumber['access_token']}")
        self.assertEqual(error.exception.status_code, 403)

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
        admin = self.create_admin()
        routes.create_user("asada_demo", UserCreate(
            username="font1", full_name="Fontanero Uno",
            password="Clave-font-2026", role="FONTANERO",
        ), f"Bearer {admin['access_token']}")
        plumber = routes.login("asada_demo", Login(username="font1", password="Clave-font-2026"))
        authorization = f"Bearer {plumber['access_token']}"
        with patch.object(routes, "post_monitor", return_value={"id":7,"status":"EN ATENCION"}) as sender:
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
        admin = self.create_admin()
        routes.create_user("asada_demo", UserCreate(
            username="font1", full_name="Fontanero Uno",
            password="Clave-font-2026", role="FONTANERO",
        ), f"Bearer {admin['access_token']}")
        plumber = routes.login("asada_demo", Login(username="font1", password="Clave-font-2026"))
        subscription = routes.PushSubscription(endpoint="https://push.example/device-1", keys={
            "p256dh":"a" * 64, "auth":"b" * 16,
        })
        with patch.dict("os.environ", {
            "AVI_PUSH_VAPID_PUBLIC_KEY":"public-key",
            "AVI_PUSH_VAPID_PRIVATE_KEY":"private-key",
            "ASADA_EVENT_SERVICE_KEY":"event-secret",
        }, clear=False):
            config = routes.push_config("asada_demo", f"Bearer {plumber['access_token']}")
            self.assertTrue(config["enabled"])
            routes.subscribe_push("asada_demo", subscription, f"Bearer {plumber['access_token']}")
            event = routes.AlertEvent(source_order_id=7, node_id="n1", sector="Norte",
                pressure_psi=2.0, flow_lpm=13.0, timestamp="2026-10-09T10:00:00Z",
                message="Anomalía crítica sostenida")
            with patch.object(routes, "send_event", return_value={
                "delivered":1,"failed":0,"configured":True,"subscriptions":1,
            }) as sender:
                first = routes.receive_event("asada_demo", event, "event-secret")
                second = routes.receive_event("asada_demo", event, "event-secret")
            self.assertTrue(first["accepted"])
            self.assertTrue(second["duplicate"])
            sender.assert_called_once()


if __name__ == "__main__":
    unittest.main()
