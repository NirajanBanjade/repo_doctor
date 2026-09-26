import { jsx as _jsx } from "react/jsx-runtime";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import TestPlanView from "./TestPlanView";
import * as client from "@/api/client";
// Mock the API client
vi.mock("@/api/client");
const mockPlan = {
    plan_id: "plan-1",
    session_id: "sess-1",
    impact_run_id: "run-1",
    status: "proposed",
    scenarios: [
        {
            scenario_id: "sc-1",
            name: "Test create_app returns a FastAPI app",
            component_id: "app/main.py::create_app",
            source_evidence: "app/main.py:10",
            expected_behavior: "Returns a FastAPI application instance",
            proposed_test_file: "working_copy/tests/generated/test_main.py",
            proposed_test_function: "test_create_app_returns_fastapi",
        },
    ],
    existing_test_mappings: [
        {
            node_id: "app/routes.py::health",
            test_files: ["tests/test_routes.py"],
            coverage_status: "covered",
        },
    ],
    coverage_gaps: ["app/main.py::create_app"],
};
function wrapper({ children }) {
    const qc = new QueryClient({
        defaultOptions: { queries: { retry: false } },
    });
    return _jsx(QueryClientProvider, { client: qc, children: children });
}
beforeEach(() => {
    vi.resetAllMocks();
});
describe("TestPlanView", () => {
    it("shows spinner while loading", () => {
        vi.mocked(client.getTestPlan).mockReturnValue(new Promise(() => { }));
        render(_jsx(TestPlanView, { sessionId: "sess-1" }), { wrapper });
        expect(screen.getByRole("status")).toBeInTheDocument();
    });
    it("renders scenarios from the plan", async () => {
        vi.mocked(client.getTestPlan).mockResolvedValue(mockPlan);
        render(_jsx(TestPlanView, { sessionId: "sess-1" }), { wrapper });
        await screen.findByText("Test create_app returns a FastAPI app");
        expect(screen.getByText("Proposed Scenarios (1)")).toBeInTheDocument();
    });
    it("shows coverage gap", async () => {
        vi.mocked(client.getTestPlan).mockResolvedValue(mockPlan);
        render(_jsx(TestPlanView, { sessionId: "sess-1" }), { wrapper });
        await screen.findByText(/Coverage gaps/i);
        expect(screen.getByText("app/main.py::create_app")).toBeInTheDocument();
    });
    it("shows Approve Plan button for proposed plan", async () => {
        vi.mocked(client.getTestPlan).mockResolvedValue(mockPlan);
        render(_jsx(TestPlanView, { sessionId: "sess-1" }), { wrapper });
        await screen.findByText("Approve Plan");
        expect(screen.getByText("Approve Plan")).toBeInTheDocument();
    });
    it("opens approval modal when Approve Plan is clicked", async () => {
        vi.mocked(client.getTestPlan).mockResolvedValue(mockPlan);
        render(_jsx(TestPlanView, { sessionId: "sess-1" }), { wrapper });
        const btn = await screen.findByText("Approve Plan");
        fireEvent.click(btn);
        expect(screen.getByRole("dialog")).toBeInTheDocument();
        expect(screen.getByText("Approve Test Plan")).toBeInTheDocument();
    });
    it("calls approveTestPlan when approval confirmed", async () => {
        vi.mocked(client.getTestPlan).mockResolvedValue(mockPlan);
        vi.mocked(client.approveTestPlan).mockResolvedValue(undefined);
        render(_jsx(TestPlanView, { sessionId: "sess-1" }), { wrapper });
        const btn = await screen.findByText("Approve Plan");
        fireEvent.click(btn);
        const confirmBtn = screen.getByText("Approve & Continue");
        fireEvent.click(confirmBtn);
        await waitFor(() => expect(client.approveTestPlan).toHaveBeenCalledWith("sess-1", {
            plan_id: "plan-1",
            approved: true,
        }));
    });
    it("closes modal when Cancel is clicked without calling approve", async () => {
        vi.mocked(client.getTestPlan).mockResolvedValue(mockPlan);
        render(_jsx(TestPlanView, { sessionId: "sess-1" }), { wrapper });
        const btn = await screen.findByText("Approve Plan");
        fireEvent.click(btn);
        const cancelBtn = screen.getByText("Cancel");
        fireEvent.click(cancelBtn);
        await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
        expect(client.approveTestPlan).not.toHaveBeenCalled();
    });
    it("shows Run Tests button for approved plan", async () => {
        vi.mocked(client.getTestPlan).mockResolvedValue({
            ...mockPlan,
            status: "approved",
        });
        render(_jsx(TestPlanView, { sessionId: "sess-1" }), { wrapper });
        await screen.findByText("Run Tests");
        expect(screen.getByText("Run Tests")).toBeInTheDocument();
    });
    it("shows empty state when no plan", async () => {
        vi.mocked(client.getTestPlan).mockRejectedValue(new Error("404"));
        render(_jsx(TestPlanView, { sessionId: "sess-1" }), { wrapper });
        await screen.findByText(/No test plan yet/i);
    });
});
