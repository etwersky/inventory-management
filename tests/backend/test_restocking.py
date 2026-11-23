"""
Tests for restocking API endpoints.
"""
import pytest

import main


@pytest.fixture(autouse=True)
def reset_restock_orders():
    """Restocking orders are held in memory, so clear them around each test."""
    main.restock_orders.clear()
    main._restock_counter = 0
    yield
    main.restock_orders.clear()
    main._restock_counter = 0


class TestRestockingEndpoints:
    """Test suite for restocking endpoints."""

    def test_recommendations_zero_budget_returns_no_items(self, client):
        """Test that a zero budget recommends nothing."""
        response = client.get("/api/restock/recommendations?budget=0")
        assert response.status_code == 200

        data = response.json()
        assert data["items"] == []
        assert data["total_cost"] == 0
        assert data["remaining_budget"] == 0

    def test_recommendations_respect_budget(self, client):
        """Test that the recommended total never exceeds the budget."""
        budget = 50000
        response = client.get(f"/api/restock/recommendations?budget={budget}")
        assert response.status_code == 200

        data = response.json()
        assert data["total_cost"] <= budget
        assert abs(data["total_cost"] + data["remaining_budget"] - budget) < 0.01
        assert data["items"]
        assert abs(sum(i["line_total"] for i in data["items"]) - data["total_cost"]) < 0.01

    def test_recommendations_structure(self, client):
        """Test that each recommended item has the expected fields and types."""
        response = client.get("/api/restock/recommendations?budget=50000")
        data = response.json()

        for item in data["items"]:
            for field in ["sku", "item_name", "trend", "forecasted_demand", "on_hand",
                          "quantity", "unit_cost", "line_total", "lead_time_days"]:
                assert field in item
            assert isinstance(item["quantity"], int)
            assert item["quantity"] > 0
            assert abs(item["quantity"] * item["unit_cost"] - item["line_total"]) < 0.01

    def test_recommendations_never_exceed_need(self, client):
        """Test that no item is recommended beyond its forecast shortfall."""
        response = client.get("/api/restock/recommendations?budget=10000000")
        data = response.json()
        forecasts = {f["item_sku"]: f for f in main.demand_forecasts}

        for item in data["items"]:
            forecast = forecasts[item["sku"]]
            assert item["quantity"] <= forecast["forecasted_demand"] - item["on_hand"]

    def test_recommendations_max_budget_covers_all_needs(self, client):
        """Test that a budget equal to max_budget recommends every shortfall."""
        max_budget = client.get("/api/restock/recommendations?budget=0").json()["max_budget"]
        data = client.get(f"/api/restock/recommendations?budget={max_budget}").json()

        assert data["max_budget"] == max_budget
        assert abs(data["total_cost"] - max_budget) < 0.01

    def test_recommendations_negative_budget_rejected(self, client):
        """Test that a negative budget returns 400."""
        response = client.get("/api/restock/recommendations?budget=-5")
        assert response.status_code == 400
        assert "detail" in response.json()

    def test_create_order_returns_201_with_lead_time(self, client):
        """Test submitting a restocking order returns the order with lead time."""
        payload = {"budget": 50000, "items": [{"sku": "FLT-405", "quantity": 10},
                                              {"sku": "GSK-203", "quantity": 5}]}
        response = client.post("/api/restock/orders", json=payload)
        assert response.status_code == 201

        order = response.json()
        assert order["order_number"].startswith("RST-")
        assert order["status"] == "Submitted"
        assert order["item_count"] == 2
        assert order["lead_time_days"] == 7  # max of FLT-405 (7) and GSK-203 (3)
        assert order["expected_delivery"] > order["submitted_at"]
        assert abs(order["total_value"] - (10 * 35.5 + 5 * 8.4)) < 0.01

    def test_create_order_rejects_over_budget(self, client):
        """Test that an order costing more than the budget returns 400."""
        payload = {"budget": 100, "items": [{"sku": "MTR-304", "quantity": 3}]}
        response = client.post("/api/restock/orders", json=payload)
        assert response.status_code == 400
        assert "exceeds budget" in response.json()["detail"]

    def test_create_order_rejects_unknown_sku(self, client):
        """Test that an unknown SKU returns 400."""
        payload = {"budget": 1000, "items": [{"sku": "NOPE-999", "quantity": 1}]}
        response = client.post("/api/restock/orders", json=payload)
        assert response.status_code == 400
        assert "Unknown SKU" in response.json()["detail"]

    def test_create_order_rejects_empty_items(self, client):
        """Test that an order with no items returns 400."""
        response = client.post("/api/restock/orders", json={"budget": 1000, "items": []})
        assert response.status_code == 400

    def test_create_order_rejects_non_positive_quantity(self, client):
        """Test that a zero quantity returns 400."""
        payload = {"budget": 1000, "items": [{"sku": "FLT-405", "quantity": 0}]}
        response = client.post("/api/restock/orders", json=payload)
        assert response.status_code == 400

    def test_create_order_rejects_duplicate_sku(self, client):
        """Test that repeating a SKU in one order returns 400."""
        payload = {"budget": 10000, "items": [{"sku": "FLT-405", "quantity": 1},
                                              {"sku": "FLT-405", "quantity": 2}]}
        response = client.post("/api/restock/orders", json=payload)
        assert response.status_code == 400

    def test_list_orders_newest_first(self, client):
        """Test that submitted orders are listed newest first."""
        client.post("/api/restock/orders", json={"budget": 1000, "items": [{"sku": "GSK-203", "quantity": 1}]})
        client.post("/api/restock/orders", json={"budget": 1000, "items": [{"sku": "BRG-102", "quantity": 1}]})

        data = client.get("/api/restock/orders").json()
        assert [o["order_number"] for o in data] == ["RST-0002", "RST-0001"]

    def test_list_orders_empty(self, client):
        """Test that no submitted orders returns an empty list."""
        response = client.get("/api/restock/orders")
        assert response.status_code == 200
        assert response.json() == []
