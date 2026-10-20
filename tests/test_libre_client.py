import hashlib
import json
import time

import httpx
import pytest

from glucowidget.libre.client import AuthError, LibreLinkUpClient, TermsError
from glucowidget.libre.models import Trend


def login_ok(user_id="user-1"):
    return {"status": 0, "data": {"user": {"id": user_id},
                                  "authTicket": {"token": "tok", "expires": time.time() + 3600, "duration": 3600}}}


GRAPH = {
    "status": 0,
    "data": {
        "connection": {
            "patientId": "p1", "firstName": "Ana", "lastName": "Silva",
            "glucoseMeasurement": {"FactoryTimestamp": "10/20/2026 12:05:00 PM", "ValueInMgPerDl": 142,
                                   "TrendArrow": 4, "Value": 142},
        },
        "graphData": [
            {"FactoryTimestamp": "10/20/2026 11:50:00 AM", "ValueInMgPerDl": 130},
            {"FactoryTimestamp": "10/20/2026 11:55:00 AM", "ValueInMgPerDl": 135},
        ],
    },
}


class FakeServer:
    def __init__(self, routes):
        self.routes = routes
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        key = (request.method, request.url.host, request.url.path)
        handler = self.routes[key]
        result = handler(request) if callable(handler) else handler
        if isinstance(result, httpx.Response):
            return result
        return httpx.Response(200, json=result)


def make_client(routes, **kw):
    server = FakeServer(routes)
    client = LibreLinkUpClient("a@b.com", "pw", transport=httpx.MockTransport(server), **kw)
    return client, server


def test_login_follows_region_redirect_and_sets_headers():
    client, server = make_client({
        ("POST", "api.libreview.io", "/llu/auth/login"): {"status": 0, "data": {"redirect": True, "region": "eu"}},
        ("POST", "api-eu.libreview.io", "/llu/auth/login"): login_ok(),
        ("GET", "api-eu.libreview.io", "/llu/connections"): {"status": 0, "data": [
            {"patientId": "p1", "firstName": "Ana", "lastName": "Silva"}]},
    })
    patients = client.connections()
    assert client.region == "eu"
    assert patients[0].id == "p1" and patients[0].name == "Ana Silva"
    login_req = server.requests[0]
    assert login_req.headers["product"] == "llu.android"
    assert json.loads(login_req.content) == {"email": "a@b.com", "password": "pw"}
    get_req = server.requests[-1]
    assert get_req.headers["Authorization"] == "Bearer tok"
    assert get_req.headers["Account-Id"] == hashlib.sha256(b"user-1").hexdigest()


def test_graph_parsing():
    client, _ = make_client({
        ("POST", "api.libreview.io", "/llu/auth/login"): login_ok(),
        ("GET", "api.libreview.io", "/llu/connections/p1/graph"): GRAPH,
    })
    data = client.graph("p1")
    assert data.current.value_mgdl == 142
    assert data.current.trend == Trend.RISING
    assert data.current.timestamp.hour == 12 and data.current.timestamp.minute == 5
    assert [r.value_mgdl for r in data.history] == [130, 135, 142]
    assert data.delta_mgdl == 7
    assert data.patient.name == "Ana Silva"


def test_bad_credentials():
    client, _ = make_client({
        ("POST", "api.libreview.io", "/llu/auth/login"): {"status": 2, "error": {"message": "notAuthenticated"}},
    })
    with pytest.raises(AuthError, match="incorretos"):
        client.login()


def test_terms_pending():
    client, _ = make_client({
        ("POST", "api.libreview.io", "/llu/auth/login"): {"status": 4, "data": {"step": {"type": "tou"}}},
    })
    with pytest.raises(TermsError):
        client.login()


def test_relogin_on_401():
    calls = {"graph": 0, "login": 0}

    def login(_):
        calls["login"] += 1
        return login_ok()

    def graph(_):
        calls["graph"] += 1
        return httpx.Response(401) if calls["graph"] == 1 else httpx.Response(200, json=GRAPH)

    client, _ = make_client({
        ("POST", "api.libreview.io", "/llu/auth/login"): login,
        ("GET", "api.libreview.io", "/llu/connections/p1/graph"): graph,
    })
    assert client.graph("p1").current.value_mgdl == 142
    assert calls == {"graph": 2, "login": 2}
