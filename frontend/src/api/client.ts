import axios from "axios";
import type {
  Session,
  CreateSessionRequest,
  XRayResult,
  EnvironmentRunResult,
  ApplyFixRequest,
  ImpactRequest,
  ImpactRunResult,
  TestPlanProposal,
  ApprovePlanRequest,
  TestRunResult,
  VerificationReport,
  StarterTask,
} from "@/types";

const http = axios.create({ baseURL: "/api/v1" });

// Intercept all errors and normalize to ErrorResponse shape
http.interceptors.response.use(
  (res) => res,
  (err) => {
    const message: string =
      err.response?.data?.message ??
      err.response?.data?.detail ??
      err.message ??
      "Unknown error";
    return Promise.reject(new Error(message));
  },
);

// ── Sessions ──────────────────────────────────────────────────────────────
export const createSession = async (body: CreateSessionRequest): Promise<Session> => {
  const { data } = await http.post<Session>("/sessions", body);
  return data;
};

export const getSession = async (sessionId: string): Promise<Session> => {
  const { data } = await http.get<Session>(`/sessions/${sessionId}`);
  return data;
};

// ── Repository X-Ray ──────────────────────────────────────────────────────
export const triggerXRay = async (sessionId: string): Promise<void> => {
  await http.post(`/sessions/${sessionId}/xray`);
};

export const getXRayGraph = async (sessionId: string): Promise<XRayResult> => {
  const { data } = await http.get<XRayResult>(`/sessions/${sessionId}/xray/graph`);
  return data;
};

// ── Environment Doctor ─────────────────────────────────────────────────────
export const runEnvironment = async (sessionId: string): Promise<void> => {
  await http.post(`/sessions/${sessionId}/environment/run`);
};

export const getEnvironmentStatus = async (
  sessionId: string,
): Promise<EnvironmentRunResult> => {
  const { data } = await http.get<EnvironmentRunResult>(
    `/sessions/${sessionId}/environment/status`,
  );
  return data;
};

export const applyEnvironmentFix = async (
  sessionId: string,
  body: ApplyFixRequest,
): Promise<void> => {
  await http.post(`/sessions/${sessionId}/environment/fix`, body);
};

// ── ImpactScope ───────────────────────────────────────────────────────────
export const triggerImpact = async (
  sessionId: string,
  body: ImpactRequest,
): Promise<ImpactRunResult> => {
  const { data } = await http.post<ImpactRunResult>(
    `/sessions/${sessionId}/impact`,
    body,
  );
  return data;
};

export const getImpactGraph = async (sessionId: string): Promise<ImpactRunResult> => {
  const { data } = await http.get<ImpactRunResult>(
    `/sessions/${sessionId}/impact/graph`,
  );
  return data;
};

// ── Test Generator ────────────────────────────────────────────────────────
export const getTestPlan = async (sessionId: string): Promise<TestPlanProposal> => {
  const { data } = await http.get<TestPlanProposal>(
    `/sessions/${sessionId}/tests/plan`,
  );
  return data;
};

export const createTestPlan = async (
  sessionId: string,
  body: { impact_run_id: string; selected_node_ids: string[] },
): Promise<TestPlanProposal> => {
  const { data } = await http.post<TestPlanProposal>(
    `/sessions/${sessionId}/tests/plan`,
    body,
  );
  return data;
};

export const approveTestPlan = async (
  sessionId: string,
  body: ApprovePlanRequest,
): Promise<TestPlanProposal> => {
  const { data } = await http.post<TestPlanProposal>(
    `/sessions/${sessionId}/tests/plan/${body.plan_id}/approve`,
    body,
  );
  return data;
};

export const runTests = async (sessionId: string, planId: string): Promise<void> => {
  await http.post(`/sessions/${sessionId}/tests/plan/${planId}/run`);
};

export const refinePlan = async (
  sessionId: string,
  planId: string,
  feedback: string,
): Promise<TestPlanProposal> => {
  const { data } = await http.post<TestPlanProposal>(
    `/sessions/${sessionId}/tests/plan/${planId}/refine`,
    { feedback },
  );
  return data;
};

export const getTestResults = async (sessionId: string): Promise<TestRunResult> => {
  const { data } = await http.get<TestRunResult>(
    `/sessions/${sessionId}/tests/results`,
  );
  return data;
};

// ── Verification ──────────────────────────────────────────────────────────
export const getVerificationReport = async (
  sessionId: string,
): Promise<VerificationReport> => {
  const { data } = await http.get<VerificationReport>(
    `/sessions/${sessionId}/verification`,
  );
  return data;
};

// ── FirstPR ───────────────────────────────────────────────────────────────
export const getStarterTasks = async (sessionId: string): Promise<StarterTask[]> => {
  const { data } = await http.get<StarterTask[]>(
    `/sessions/${sessionId}/firstpr/tasks`,
  );
  return data;
};
