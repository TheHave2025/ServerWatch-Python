"""Ejercicio real de API HTTP localhost, sin conexiones externas."""

import json
import threading
from dataclasses import asdict, replace
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from serverwatch.storage import Database
from serverwatch.web import create_server


def test_web_endpoints_and_ingest(tmp_path, settings, snapshot):
    conf = replace(settings, dashboard_host="127.0.0.1", dashboard_port=0,
                   ingest_token="very-strong-test-token-with-more-than-32-characters")
    srv, _hub = create_server(conf, Database(str(tmp_path / "app.sqlite3")))
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{srv.server_port}"
    try:
        with urlopen(url + "/healthz") as response:
            assert json.load(response)["status"] == "ok"
        with urlopen(url + "/") as response:
            assert b"ServerWatch" in response.read()
        with urlopen(url + "/api/overview") as response:
            assert json.load(response)["servers"] == []
        payload = json.dumps(asdict(snapshot)).encode()
        headers = {"Content-Type": "application/json"}
        unauthorized = Request(url + "/api/ingest", data=payload, headers=headers)
        try:
            urlopen(unauthorized)
            assert False, "Bearer requerido"
        except HTTPError as exc:
            assert exc.code == 401
        headers["Authorization"] = "Bearer " + conf.ingest_token
        with urlopen(Request(url + "/api/ingest", data=payload, headers=headers)) as resp:
            assert resp.status == 202
        with urlopen(url + "/api/overview") as response:
            assert json.load(response)["servers"][0]["id"] == snapshot.hostname
        with urlopen(url + "/api/history?server=test-ubuntu") as response:
            assert len(json.load(response)["points"]) == 1
        with urlopen(url + "/api/events") as response:
            assert json.load(response)["events"] == []
    finally:
        srv.shutdown()
        srv.server_close()
        thread.join(timeout=2)


def test_dashboard_http_basic_auth(tmp_path, settings):
    conf = replace(settings, dashboard_host="127.0.0.1", dashboard_port=0,
                   dashboard_password="1234567890123456")
    srv, _ = create_server(conf, Database(str(tmp_path / "test.sqlite3")))
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{srv.server_port}"
    try:
        try:
            urlopen(url + "/api/overview")
            assert False, "Password requerido"
        except HTTPError as exc:
            assert exc.code == 401
            assert "Basic" in exc.headers["WWW-Authenticate"]
        import base64
        auth = base64.b64encode(b"serverwatch:1234567890123456").decode()
        with urlopen(Request(url + "/api/overview", headers={"Authorization": "Basic " + auth})) as r:
            assert r.status == 200
    finally:
        srv.shutdown()
        srv.server_close()
        thread.join(timeout=2)
