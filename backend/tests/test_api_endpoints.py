"""Integration tests for FastAPI HTTP adapter (Seam 3)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from ran_city.api.app import create_app


@pytest.fixture(scope="module")
def client() -> TestClient:
    app = create_app()
    return TestClient(app)


def test_get_health(client: TestClient):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "0.1.0"}


def test_get_city_jaen_and_404(client: TestClient):
    response = client.get("/api/cities/jaen")
    assert response.status_code == 200
    data = response.json()

    assert data["city_id"] == "jaen"
    assert data["city_name"] == "Jaén"
    assert len(data["bbox_wgs84"]) == 4
    assert len(data["bbox_utm30"]) == 4
    assert len(data["zones"]) >= 3
    assert len(data["operators"]) >= 3
    assert len(data["sites"]) == 18

    for site in data["sites"]:
        assert -3.84 <= site["lon"] <= -3.75
        assert 37.75 <= site["lat"] <= 37.81
        assert "ground_z_m" in site
        assert "source" in site
        assert len(site["sectors"]) >= 1
        for sector in site["sectors"]:
            assert "azimuth_deg" in sector
            assert "ant_height_m" in sector
            assert len(sector["cells"]) >= 1

    # Unknown city returns 404
    not_found_res = client.get("/api/cities/unknown")
    assert not_found_res.status_code == 404


def test_post_city_coverage_and_whatif_immutability(client: TestClient):
    # Using environment="rural" for fast test execution (resolution=50m)
    payload = {
        "network_alias": "Red A",
        "n_band": 78,
        "metric": "rsrp",
        "environment": "rural",
    }
    response = client.post("/api/cities/jaen/coverage", json=payload)
    assert response.status_code == 200
    body = response.json()

    assert body["png_base64"].startswith("data:image/png;base64,")
    assert len(body["bounds_wgs84"]) == 4
    assert len(body["grid_shape"]) == 2
    assert body["resolution_m"] == 50.0

    stats = body["stats"]
    assert stats["unit"] == "dBm"
    orig_median = stats["median_val"]
    assert isinstance(orig_median, float)
    assert -140.0 < orig_median < 0.0

    # Test metric="sinr"
    sinr_res = client.post("/api/cities/jaen/coverage", json={**payload, "metric": "sinr"})
    assert sinr_res.status_code == 200
    assert sinr_res.json()["stats"]["unit"] == "dB"

    # Test metric="best_server"
    bs_res = client.post("/api/cities/jaen/coverage", json={**payload, "metric": "best_server"})
    assert bs_res.status_code == 200
    assert bs_res.json()["stats"]["unit"] == "index"

    # Fetch cells from Red A to override
    city_data = client.get("/api/cities/jaen").json()
    red_a_cells = [
        c["cell_id"]
        for s in city_data["sites"]
        if s["network_alias"] == "Red A"
        for sec in s["sectors"]
        for c in sec["cells"]
        if c["band"]["n_band"] == 78
    ]
    assert len(red_a_cells) > 0

    # What-If: Reduce tx_power_dbm across cells
    ovr_payload = {
        **payload,
        "cell_overrides": [
            {"cell_id": cid, "tx_power_dbm": 15.0}
            for cid in red_a_cells
        ],
    }
    ovr_res = client.post("/api/cities/jaen/coverage", json=ovr_payload)
    assert ovr_res.status_code == 200
    ovr_median = ovr_res.json()["stats"]["median_val"]
    assert ovr_median != orig_median

    # Subsequent request without overrides returns identical original median (no mutation)
    clean_res = client.post("/api/cities/jaen/coverage", json=payload)
    assert clean_res.status_code == 200
    assert clean_res.json()["stats"]["median_val"] == orig_median


def test_post_inspect_point(client: TestClient):
    payload = {
        "lon": -3.7903,
        "lat": 37.7750,
        "network_alias": "Red A",
        "n_band": 78,
    }
    response = client.post("/api/cities/jaen/inspect-point", json=payload)
    assert response.status_code == 200
    body = response.json()

    assert "serving_cell_id" in body
    assert "serving_rsrp_dbm" in body
    assert "sinr_db" in body
    assert "noise_per_re_dbm" in body
    assert "interference_mw" in body
    assert len(body["cells"]) > 0

    required_cell_fields = [
        "cell_id",
        "site_id",
        "d2d_m",
        "d3d_m",
        "zenith_gcs_deg",
        "azimuth_gcs_deg",
        "los_probability",
        "path_loss_db",
        "antenna_gain_dbi",
        "effective_loss_db",
        "rsrp_dbm",
    ]
    for c in body["cells"]:
        for field in required_cell_fields:
            assert field in c
            assert isinstance(c[field], (float, int, str, bool))


def test_post_antenna_pattern(client: TestClient):
    payload = {
        "n_rows": 8,
        "n_cols": 8,
        "mechanical_tilt_deg": 4.0,
        "electrical_tilt_deg": 6.0,
        "sector_azimuth_deg": 120.0,
    }
    response = client.post("/api/antenna/pattern", json=payload)
    assert response.status_code == 200
    body = response.json()

    assert len(body["azimuth_angles_deg"]) == 360
    assert len(body["horizontal_gain_dbi"]) == 360
    assert len(body["zenith_angles_deg"]) == 181
    assert len(body["vertical_gain_dbi"]) == 181
    assert isinstance(body["max_gain_dbi"], float)
    assert body["max_gain_dbi"] > 0.0
