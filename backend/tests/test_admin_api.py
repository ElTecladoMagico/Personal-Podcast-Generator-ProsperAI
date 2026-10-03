def test_metrics_are_for_admins_only(client, claims):
    assert client.get("/admin/metrics").status_code == 403
    claims["metadata"] = {"role": "admin"}
    r = client.get("/admin/metrics", params={"days": 7, "include_mock": False})
    assert r.status_code == 200
    body = r.json()
    assert body["range"]["days"] == 7 and body["include_mock"] is False
    assert set(body) >= {"kpis", "growth", "content", "operations"}


def test_only_the_ranges_the_dashboard_offers(client, claims):
    claims["metadata"] = {"role": "admin"}
    assert client.get("/admin/metrics", params={"days": 5}).status_code == 422
