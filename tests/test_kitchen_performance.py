from uuid import UUID

import pytest
from fastapi import HTTPException

from app.repositories.order import OrderRepository
from app.services.order import get_kitchen_performance


TENANT_ID = UUID(
    "25291ef5-0240-4042-aabc-b92c5aa4957a"
)

BRANCH_ID = UUID(
    "6146f071-baf4-40e9-bbff-71f86e0a7770"
)

FAKE_OTHER_TENANT_ID = UUID(
    "00000000-0000-0000-0000-000000000001"
)

FAKE_OTHER_BRANCH_ID = UUID(
    "00000000-0000-0000-0000-000000000002"
)


def test_kitchen_performance_returns_preparation_metrics(
    db_session,
    monkeypatch,
):
    """
    Verify kitchen preparation performance metrics.
    """

    def fake_get_kitchen_preparation_durations(
        self,
        tenant_id,
        branch_id,
    ):
        return [
            120,
            300,
            480,
        ]

    monkeypatch.setattr(
        OrderRepository,
        "get_kitchen_preparation_durations",
        fake_get_kitchen_preparation_durations,
    )

    result = get_kitchen_performance(
        db=db_session,
        tenant_id=TENANT_ID,
        branch_id=BRANCH_ID,
    )

    assert result["branch_id"] == BRANCH_ID

    assert result["prepared_order_count"] == 3

    assert result["average_preparation_seconds"] == 300.0
    assert result["average_preparation_minutes"] == 5.0

    assert result["fastest_preparation_seconds"] == 120
    assert result["slowest_preparation_seconds"] == 480


def test_kitchen_performance_returns_none_when_no_history_exists(
    db_session,
    monkeypatch,
):
    """
    Verify empty preparation history behavior.
    """

    def fake_get_kitchen_preparation_durations(
        self,
        tenant_id,
        branch_id,
    ):
        return []

    monkeypatch.setattr(
        OrderRepository,
        "get_kitchen_preparation_durations",
        fake_get_kitchen_preparation_durations,
    )

    result = get_kitchen_performance(
        db=db_session,
        tenant_id=TENANT_ID,
        branch_id=BRANCH_ID,
    )

    assert result["branch_id"] == BRANCH_ID
    assert result["prepared_order_count"] == 0

    assert result["average_preparation_seconds"] is None
    assert result["average_preparation_minutes"] is None

    assert result["fastest_preparation_seconds"] is None
    assert result["slowest_preparation_seconds"] is None


def test_kitchen_performance_rejects_other_tenant_branch(
    db_session,
    monkeypatch,
):
    """
    Verify tenant isolation for kitchen performance.
    """

    def fake_get_kitchen_preparation_durations(
        self,
        tenant_id,
        branch_id,
    ):
        return [
            120,
            300,
            480,
        ]

    monkeypatch.setattr(
        OrderRepository,
        "get_kitchen_preparation_durations",
        fake_get_kitchen_preparation_durations,
    )

    with pytest.raises(HTTPException) as exc_info:
        get_kitchen_performance(
            db=db_session,
            tenant_id=FAKE_OTHER_TENANT_ID,
            branch_id=BRANCH_ID,
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Branch not found."


def test_kitchen_performance_rejects_other_branch(
    db_session,
    monkeypatch,
):
    """
    Verify branch isolation for kitchen performance.
    """

    def fake_get_kitchen_preparation_durations(
        self,
        tenant_id,
        branch_id,
    ):
        return [
            120,
            300,
            480,
        ]

    monkeypatch.setattr(
        OrderRepository,
        "get_kitchen_preparation_durations",
        fake_get_kitchen_preparation_durations,
    )

    with pytest.raises(HTTPException) as exc_info:
        get_kitchen_performance(
            db=db_session,
            tenant_id=TENANT_ID,
            branch_id=FAKE_OTHER_BRANCH_ID,
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Branch not found."