from fastapi import FastAPI
from fastapi.testclient import TestClient

from monitoring.api.app import _register_base_routes


def test_network_equipment_page_serves_current_inventory_markup():
    app = FastAPI()
    _register_base_routes(app)

    response = TestClient(app).get("/network-equipment?embed=portal")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert 'id="inventory-scan-button"' in response.text
