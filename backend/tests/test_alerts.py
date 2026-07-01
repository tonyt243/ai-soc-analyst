from app.alerts.models import AlertType

ALL_TYPE_VALUES = {t.value for t in AlertType}


def test_list_alert_types(client):
    resp = client.get("/alerts/types")
    assert resp.status_code == 200
    assert set(resp.json()) == ALL_TYPE_VALUES


def test_generate_specific_type(client):
    resp = client.post("/alerts/generate", json={"type": "log4shell"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["type"] == "log4shell"
    assert body["id"].startswith("alert-")
    assert "jndi" in body["raw_log"].lower()


def test_generate_without_type_picks_a_random_one(client):
    resp = client.post("/alerts/generate", json={})
    assert resp.status_code == 200
    assert resp.json()["type"] in ALL_TYPE_VALUES


def test_generate_produces_a_valid_alert_for_every_type(client):
    for type_value in ALL_TYPE_VALUES:
        resp = client.post("/alerts/generate", json={"type": type_value})
        assert resp.status_code == 200
        body = resp.json()
        assert body["type"] == type_value
        assert body["source_ip"]
        assert body["raw_log"]
        assert body["title"]


def test_generated_alert_appears_in_list(client):
    created = client.post("/alerts/generate", json={"type": "port_scan"}).json()

    listed = client.get("/alerts").json()

    assert any(a["id"] == created["id"] for a in listed)


def test_list_is_empty_with_no_alerts_generated(client):
    resp = client.get("/alerts")
    assert resp.status_code == 200
    assert resp.json() == []


def test_get_alert_by_id(client):
    created = client.post("/alerts/generate", json={"type": "ssh_brute_force"}).json()

    resp = client.get(f"/alerts/{created['id']}")

    assert resp.status_code == 200
    assert resp.json() == created


def test_get_alert_not_found(client):
    resp = client.get("/alerts/does-not-exist")
    assert resp.status_code == 404
