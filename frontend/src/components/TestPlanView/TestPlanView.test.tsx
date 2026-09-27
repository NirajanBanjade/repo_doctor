import { type ReactNode } from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import TestPlanView from "./TestPlanView";
import * as client from "@/api/client";
import type { TestPlanProposal } from "@/types";

// Mock the API client
vi.mock("@/api/client");

const mockPlan: TestPlanProposal = {
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
      rationale: "Protect the application factory contract",
      edge_cases: [],
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
  selected_node_ids: ["app/main.py::create_app"],
  generated_files: [],
  analysis_notes: [],
  overall_rationale: "Protect the selected component contracts.",
};

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

beforeEach(() => {
  vi.resetAllMocks();
});

describe("TestPlanView", () => {
  it("shows spinner while loading", () => {
    vi.mocked(client.getTestPlan).mockReturnValue(new Promise(() => {}));
    render(<TestPlanView sessionId="sess-1" />, { wrapper });
    expect(screen.getByRole("status")).toBeInTheDocument();
  });

  it("renders scenarios from the plan", async () => {
    vi.mocked(client.getTestPlan).mockResolvedValue(mockPlan);
    render(<TestPlanView sessionId="sess-1" />, { wrapper });
    await screen.findByText(/Test create_app returns a FastAPI app/);
    expect(screen.getByText("Proposed Test Scenarios (1)")).toBeInTheDocument();
  });

  it("shows coverage gap", async () => {
    vi.mocked(client.getTestPlan).mockResolvedValue(mockPlan);
    render(<TestPlanView sessionId="sess-1" />, { wrapper });
    await screen.findByText(/Coverage gaps/i);
    expect(screen.getByText("app/main.py::create_app")).toBeInTheDocument();
  });

  it("shows Approve & Generate Tests button for proposed plan", async () => {
    vi.mocked(client.getTestPlan).mockResolvedValue(mockPlan);
    render(<TestPlanView sessionId="sess-1" />, { wrapper });
    await screen.findByText("Approve & Generate Tests");
    expect(screen.getByText("Approve & Generate Tests")).toBeInTheDocument();
  });

  it("opens approval modal when Approve & Generate Tests is clicked", async () => {
    vi.mocked(client.getTestPlan).mockResolvedValue(mockPlan);
    render(<TestPlanView sessionId="sess-1" />, { wrapper });
    const btn = await screen.findByText("Approve & Generate Tests");
    fireEvent.click(btn);
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText("Approve Test Plan")).toBeInTheDocument();
  });

  it("calls approveTestPlan when approval confirmed", async () => {
    vi.mocked(client.getTestPlan).mockResolvedValue(mockPlan);
    vi.mocked(client.approveTestPlan).mockResolvedValue({
      ...mockPlan,
      status: "approved",
      generated_files: ["working_copy/tests/generated/test_main.py"],
    });
    render(<TestPlanView sessionId="sess-1" />, { wrapper });
    const btn = await screen.findByText("Approve & Generate Tests");
    fireEvent.click(btn);
    const confirmBtn = screen.getByText("Approve & Generate");
    fireEvent.click(confirmBtn);
    await waitFor(() =>
      expect(client.approveTestPlan).toHaveBeenCalledWith("sess-1", {
        plan_id: "plan-1",
        approved: true,
      }),
    );
  });

  it("closes modal when Cancel is clicked without calling approve", async () => {
    vi.mocked(client.getTestPlan).mockResolvedValue(mockPlan);
    render(<TestPlanView sessionId="sess-1" />, { wrapper });
    const btn = await screen.findByText("Approve & Generate Tests");
    fireEvent.click(btn);
    const cancelBtn = screen.getByText("Cancel");
    fireEvent.click(cancelBtn);
    await waitFor(() =>
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument(),
    );
    expect(client.approveTestPlan).not.toHaveBeenCalled();
  });

  it("shows Run Tests button for approved plan", async () => {
    vi.mocked(client.getTestPlan).mockResolvedValue({
      ...mockPlan,
      status: "approved",
    });
    render(<TestPlanView sessionId="sess-1" />, { wrapper });
    await screen.findByText("Run Tests");
    expect(screen.getByText("Run Tests")).toBeInTheDocument();
  });

  it("shows empty state when no plan", async () => {
    vi.mocked(client.getTestPlan).mockRejectedValue(new Error("404"));
    render(<TestPlanView sessionId="sess-1" />, { wrapper });
    await screen.findByText(/No test plan yet/i);
  });
});
