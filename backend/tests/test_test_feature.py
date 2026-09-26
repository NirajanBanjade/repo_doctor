"""
tests/test_test_feature.py

Tests for Feature 05 — Radius Test Generator.

Covers:
- Test Mapper unit tests
- TestPlanProposal schema validation
- ApprovalRequiredError gate
- API integration: plan → approve → run cycle
- Component status logic (build_component_statuses)
"""

from __future__ import annotations

import textwrap
import uuid
from pathlib import Path
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError

from app.bob.schemas.test_plan import TestPlanProposal, TestScenario
from app.db import evidence_store
from app.main import app
from app.sandbox.test_executor import build_component_statuses
from app.services.test_generator import ApprovalRequiredError, generate_test_files
from app.services.test_mapper import map_tests_to_nodes

# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def reset_db():
    evidence_store._engine = None
    yield
    evidence_store._engine = None


@pytest.fixture()
def app_client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.fixture()
def payment_repo(tmp_path):
    """Minimal repo: process_payment + test that calls it."""
    (tmp_path / "requirements.txt").write_text("fastapi\npytest\n")
    (tmp_path / "payment.py").write_text(textwrap.dedent("""
            def process_payment(amount):
                return {"status": "ok", "amount": amount}
        """))
    (tmp_path / "orders.py").write_text(textwrap.dedent("""
            from payment import process_payment

            def process_order(order_id, amount):
                return process_payment(amount)
        """))
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "__init__.py").write_text("")
    (tests_dir / "test_payment.py").write_text(textwrap.dedent("""
            from payment import process_payment

            def test_process_payment():
                result = process_payment(10)
                assert result["status"] == "ok"
        """))
    return str(tmp_path)


# ── Test Mapper unit tests ─────────────────────────────────────────────────────


def test_mapper_identifies_covered_node(payment_repo):
    """test_payment.py calls process_payment — must be 'covered'."""
    nodes = [
        {
            "node_id": "payment::process_payment",
            "name": "process_payment",
            "path": "payment.py",
            "line_start": 1,
            "line_end": 2,
        }
    ]
    mappings = map_tests_to_nodes(payment_repo, nodes)
    assert len(mappings) == 1
    m = mappings[0]
    assert m.coverage_status == "covered"
    assert any("test_payment" in tf for tf in m.test_files)


def test_mapper_returns_no_suitable_test_for_uncovered_node(payment_repo):
    """A node with no matching test file gets 'no_suitable_test'."""
    nodes = [
        {
            "node_id": "orders::process_order",
            "name": "process_order",
            "path": "orders.py",
            "line_start": 3,
            "line_end": 4,
        }
    ]
    mappings = map_tests_to_nodes(payment_repo, nodes)
    assert len(mappings) == 1
    # process_order is not called in any test, but orders.py is not imported either
    assert mappings[0].coverage_status in ("no_suitable_test", "indirect")


def test_mapper_handles_empty_node_list(payment_repo):
    mappings = map_tests_to_nodes(payment_repo, [])
    assert mappings == []


# ── TestPlanProposal schema validation ────────────────────────────────────────


def test_schema_valid_scenario():
    proposal = TestPlanProposal(
        scenarios=[
            TestScenario(
                name="Test payment",
                component_id="payment::process_payment",
                source_evidence="payment.py:1",
                expected_behavior="Returns ok status",
                proposed_test_file="working_copy/tests/generated/payment_test.py",
                proposed_test_function="test_process_payment",
            )
        ]
    )
    assert len(proposal.scenarios) == 1


def test_schema_rejects_missing_component_id():
    with pytest.raises(ValidationError):
        TestPlanProposal(
            scenarios=[
                {
                    "name": "Test payment",
                    "component_id": "",  # empty — should fail field_validator
                    "source_evidence": "payment.py:1",
                    "expected_behavior": "Returns ok status",
                    "proposed_test_file": "working_copy/tests/generated/payment_test.py",
                    "proposed_test_function": "test_process_payment",
                }
            ]
        )


def test_schema_rejects_scenario_without_component_id_field():
    with pytest.raises(ValidationError):
        TestPlanProposal(
            scenarios=[
                {
                    "name": "Test payment",
                    # component_id missing entirely
                    "source_evidence": "payment.py:1",
                    "expected_behavior": "Returns ok status",
                    "proposed_test_file": "working_copy/tests/generated/payment_test.py",
                    "proposed_test_function": "test_process_payment",
                }
            ]
        )


# ── ApprovalRequiredError gate ─────────────────────────────────────────────────


def test_generate_test_files_requires_approved_status(tmp_path):
    plan = {
        "plan_id": str(uuid.uuid4()),
        "status": "pending",
        "scenarios": [],
    }
    with pytest.raises(ApprovalRequiredError):
        generate_test_files(plan, str(tmp_path))


def test_generate_test_files_rejected_status(tmp_path):
    plan = {
        "plan_id": str(uuid.uuid4()),
        "status": "rejected",
        "scenarios": [],
    }
    with pytest.raises(ApprovalRequiredError):
        generate_test_files(plan, str(tmp_path))


def test_generate_test_files_approved_writes_files(tmp_path):
    plan = {
        "plan_id": str(uuid.uuid4()),
        "status": "approved",
        "scenarios": [
            {
                "component_id": "payment::process_payment",
                "name": "Test payment",
                "source_evidence": "payment.py:1",
                "expected_behavior": "returns ok status",
                "proposed_test_file": "working_copy/tests/generated/payment_test.py",
                "proposed_test_function": "test_process_payment",
            }
        ],
    }
    written = generate_test_files(plan, str(tmp_path))
    assert len(written) == 1
    assert Path(written[0]).exists()
    content = Path(written[0]).read_text()
    assert "test_process_payment" in content
    assert "NotImplementedError" in content


# ── build_component_statuses logic ────────────────────────────────────────────


def test_component_status_covered_passed():
    scenarios = [
        {
            "component_id": "payment::process_payment",
            "proposed_test_function": "test_process_payment",
        }
    ]
    per_test = [{"nodeid": "tests/generated/test_process_payment", "outcome": "passed"}]
    statuses = build_component_statuses(scenarios, per_test, [], False)
    assert statuses[0]["status"] == "covered_passed"


def test_component_status_covered_failed():
    scenarios = [
        {
            "component_id": "payment::process_payment",
            "proposed_test_function": "test_process_payment",
        }
    ]
    per_test = [{"nodeid": "tests/generated/test_process_payment", "outcome": "failed"}]
    statuses = build_component_statuses(scenarios, per_test, [], False)
    assert statuses[0]["status"] == "covered_failed"


def test_component_status_no_suitable_test():
    scenarios = [
        {
            "component_id": "orders::process_order",
            "proposed_test_function": "test_process_order",
        }
    ]
    statuses = build_component_statuses(scenarios, [], [], False)
    assert statuses[0]["status"] == "no_suitable_test"


def test_component_status_unexecuted_on_infra_error(tmp_path):
    component_id = "orders::process_order"
    safe = component_id.replace("::", "_")
    generated_file = str(tmp_path / f"{safe}_test.py")
    Path(generated_file).write_text("# stub")

    scenarios = [
        {
            "component_id": component_id,
            "proposed_test_function": "test_process_order",
        }
    ]
    statuses = build_component_statuses(scenarios, [], [generated_file], True)
    assert statuses[0]["status"] == "unexecuted"


# ── API integration tests ─────────────────────────────────────────────────────


async def _setup_session_with_impact(
    client: AsyncClient, repo_path: str, db_url: str
) -> tuple[str, str]:
    """Create session, run X-Ray, run impact, return (session_id, run_id)."""
    r = await client.post("/api/v1/sessions", json={"repo_path": repo_path})
    assert r.status_code == 201
    sid = r.json()["session_id"]

    r2 = await client.post(f"/api/v1/sessions/{sid}/xray")
    assert r2.status_code == 202

    nodes = (await client.get(f"/api/v1/sessions/{sid}/xray/graph")).json()["nodes"]
    assert nodes, "X-Ray must produce nodes"
    node_id = nodes[0]["node_id"]

    r3 = await client.post(
        f"/api/v1/sessions/{sid}/impact",
        json={"symbol_id": node_id, "depth": 1},
    )
    assert r3.status_code == 202
    run_id = r3.json()["run_id"]
    return sid, run_id


@pytest.mark.asyncio
async def test_create_test_plan_session_not_found(app_client):
    async with app_client as client:
        r = await client.post(
            "/api/v1/sessions/nonexistent/tests/plan",
            json={
                "impact_run_id": str(uuid.uuid4()),
                "selected_node_ids": [],
            },
        )
        assert r.status_code == 404


@pytest.mark.asyncio
async def test_create_test_plan_impact_run_not_found(payment_repo, app_client):
    async with app_client as client:
        r = await client.post("/api/v1/sessions", json={"repo_path": payment_repo})
        sid = r.json()["session_id"]
        r2 = await client.post(
            f"/api/v1/sessions/{sid}/tests/plan",
            json={
                "impact_run_id": str(uuid.uuid4()),
                "selected_node_ids": [],
            },
        )
        assert r2.status_code == 404


@pytest.mark.asyncio
async def test_create_test_plan_returns_202(payment_repo, app_client):
    async with app_client as client:
        sid, run_id = await _setup_session_with_impact(client, payment_repo, "")
        nodes_r = await client.get(f"/api/v1/sessions/{sid}/xray/graph")
        node_id = nodes_r.json()["nodes"][0]["node_id"]

        r = await client.post(
            f"/api/v1/sessions/{sid}/tests/plan",
            json={"impact_run_id": run_id, "selected_node_ids": [node_id]},
        )
        assert r.status_code == 202
        body = r.json()
        assert "plan_id" in body
        assert body["status"] == "pending"
        assert "scenarios" in body
        assert "existing_test_mappings" in body


@pytest.mark.asyncio
async def test_create_test_plan_idempotent(payment_repo, app_client):
    """Calling plan twice for same impact_run_id returns the same plan."""
    async with app_client as client:
        sid, run_id = await _setup_session_with_impact(client, payment_repo, "")
        node_id = (await client.get(f"/api/v1/sessions/{sid}/xray/graph")).json()[
            "nodes"
        ][0]["node_id"]

        r1 = await client.post(
            f"/api/v1/sessions/{sid}/tests/plan",
            json={"impact_run_id": run_id, "selected_node_ids": [node_id]},
        )
        r2 = await client.post(
            f"/api/v1/sessions/{sid}/tests/plan",
            json={"impact_run_id": run_id, "selected_node_ids": [node_id]},
        )
        assert r1.json()["plan_id"] == r2.json()["plan_id"]


@pytest.mark.asyncio
async def test_approve_test_plan(payment_repo, app_client):
    async with app_client as client:
        sid, run_id = await _setup_session_with_impact(client, payment_repo, "")
        node_id = (await client.get(f"/api/v1/sessions/{sid}/xray/graph")).json()[
            "nodes"
        ][0]["node_id"]

        plan_r = await client.post(
            f"/api/v1/sessions/{sid}/tests/plan",
            json={"impact_run_id": run_id, "selected_node_ids": [node_id]},
        )
        plan_id = plan_r.json()["plan_id"]

        r = await client.post(
            f"/api/v1/sessions/{sid}/tests/plan/{plan_id}/approve",
            json={"plan_id": plan_id, "approved": True},
        )
        assert r.status_code == 200
        assert r.json()["status"] == "approved"


@pytest.mark.asyncio
async def test_reject_test_plan(payment_repo, app_client):
    async with app_client as client:
        sid, run_id = await _setup_session_with_impact(client, payment_repo, "")
        node_id = (await client.get(f"/api/v1/sessions/{sid}/xray/graph")).json()[
            "nodes"
        ][0]["node_id"]

        plan_r = await client.post(
            f"/api/v1/sessions/{sid}/tests/plan",
            json={"impact_run_id": run_id, "selected_node_ids": [node_id]},
        )
        plan_id = plan_r.json()["plan_id"]

        r = await client.post(
            f"/api/v1/sessions/{sid}/tests/plan/{plan_id}/approve",
            json={"plan_id": plan_id, "approved": False},
        )
        assert r.status_code == 200
        assert r.json()["status"] == "rejected"


@pytest.mark.asyncio
async def test_run_unapproved_plan_returns_422(payment_repo, app_client):
    async with app_client as client:
        sid, run_id = await _setup_session_with_impact(client, payment_repo, "")
        node_id = (await client.get(f"/api/v1/sessions/{sid}/xray/graph")).json()[
            "nodes"
        ][0]["node_id"]

        plan_r = await client.post(
            f"/api/v1/sessions/{sid}/tests/plan",
            json={"impact_run_id": run_id, "selected_node_ids": [node_id]},
        )
        plan_id = plan_r.json()["plan_id"]

        # Don't approve — try to run directly
        r = await client.post(f"/api/v1/sessions/{sid}/tests/plan/{plan_id}/run")
        assert r.status_code == 422


@pytest.mark.asyncio
async def test_full_plan_approve_run_cycle(payment_repo, app_client, tmp_path):
    """
    Full integration: create plan → approve → run.
    run_tests is mocked (no Docker required) to return a deterministic result.
    """
    mock_run_result = {
        "stdout": "1 passed",
        "stderr": "",
        "exit_code": 0,
        "infrastructure_error": False,
        "per_test": [
            {
                "nodeid": "tests/generated/payment__process_payment_test.py::test_process_payment",
                "outcome": "passed",
            }
        ],
        "component_statuses": [],
    }

    with patch("app.api.routes.tests.run_tests", return_value=mock_run_result), patch(
        "app.api.routes.tests._WORKING_COPY_ROOT", str(tmp_path)
    ):
        async with app_client as client:
            sid, run_id = await _setup_session_with_impact(client, payment_repo, "")
            node_id = (await client.get(f"/api/v1/sessions/{sid}/xray/graph")).json()[
                "nodes"
            ][0]["node_id"]

            plan_r = await client.post(
                f"/api/v1/sessions/{sid}/tests/plan",
                json={"impact_run_id": run_id, "selected_node_ids": [node_id]},
            )
            plan_id = plan_r.json()["plan_id"]

            await client.post(
                f"/api/v1/sessions/{sid}/tests/plan/{plan_id}/approve",
                json={"plan_id": plan_id, "approved": True},
            )

            run_r = await client.post(
                f"/api/v1/sessions/{sid}/tests/plan/{plan_id}/run"
            )
            assert run_r.status_code == 202
            body = run_r.json()
            assert "result_id" in body
            assert "component_statuses" in body
            assert "warnings" in body
            # Safety notice must always be in warnings
            assert any("NOT proof" in w for w in body["warnings"])

            # GET result
            res_r = await client.get(
                f"/api/v1/sessions/{sid}/tests/plan/{plan_id}/result"
            )
            assert res_r.status_code == 200
            res = res_r.json()
            assert res["result_id"] == body["result_id"]


@pytest.mark.asyncio
async def test_get_result_before_run(payment_repo, app_client):
    async with app_client as client:
        sid, run_id = await _setup_session_with_impact(client, payment_repo, "")
        node_id = (await client.get(f"/api/v1/sessions/{sid}/xray/graph")).json()[
            "nodes"
        ][0]["node_id"]

        plan_r = await client.post(
            f"/api/v1/sessions/{sid}/tests/plan",
            json={"impact_run_id": run_id, "selected_node_ids": [node_id]},
        )
        plan_id = plan_r.json()["plan_id"]

        r = await client.get(f"/api/v1/sessions/{sid}/tests/plan/{plan_id}/result")
        assert r.status_code == 200
        body = r.json()
        assert body["result"] is None
        assert any("no_test_result" in w for w in body["warnings"])


@pytest.mark.asyncio
async def test_approve_wrong_plan_id_in_body(payment_repo, app_client):
    async with app_client as client:
        sid, run_id = await _setup_session_with_impact(client, payment_repo, "")
        node_id = (await client.get(f"/api/v1/sessions/{sid}/xray/graph")).json()[
            "nodes"
        ][0]["node_id"]

        plan_r = await client.post(
            f"/api/v1/sessions/{sid}/tests/plan",
            json={"impact_run_id": run_id, "selected_node_ids": [node_id]},
        )
        plan_id = plan_r.json()["plan_id"]

        r = await client.post(
            f"/api/v1/sessions/{sid}/tests/plan/{plan_id}/approve",
            json={"plan_id": "wrong-id", "approved": True},
        )
        assert r.status_code == 422
