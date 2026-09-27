import axios from "axios";
const http = axios.create({ baseURL: "/api/v1" });
// Intercept all errors and normalize to ErrorResponse shape
http.interceptors.response.use((res) => res, (err) => {
    const message = err.response?.data?.message ??
        err.response?.data?.detail ??
        err.message ??
        "Unknown error";
    return Promise.reject(new Error(message));
});
// ── Sessions ──────────────────────────────────────────────────────────────
export const createSession = async (body) => {
    const { data } = await http.post("/sessions", body);
    return data;
};
export const getSession = async (sessionId) => {
    const { data } = await http.get(`/sessions/${sessionId}`);
    return data;
};
// ── Repository X-Ray ──────────────────────────────────────────────────────
export const triggerXRay = async (sessionId) => {
    await http.post(`/sessions/${sessionId}/xray`);
};
export const getXRayGraph = async (sessionId) => {
    const { data } = await http.get(`/sessions/${sessionId}/xray/graph`);
    return data;
};
// ── Environment Doctor ─────────────────────────────────────────────────────
export const runEnvironment = async (sessionId) => {
    await http.post(`/sessions/${sessionId}/environment/run`);
};
export const getEnvironmentStatus = async (sessionId) => {
    const { data } = await http.get(`/sessions/${sessionId}/environment/status`);
    return data;
};
export const applyEnvironmentFix = async (sessionId, body) => {
    await http.post(`/sessions/${sessionId}/environment/fix`, body);
};
// ── ImpactScope ───────────────────────────────────────────────────────────
export const triggerImpact = async (sessionId, body) => {
    const { data } = await http.post(`/sessions/${sessionId}/impact`, body);
    return data;
};
export const getImpactGraph = async (sessionId) => {
    const { data } = await http.get(`/sessions/${sessionId}/impact/graph`);
    return data;
};
// ── Test Generator ────────────────────────────────────────────────────────
export const getTestPlan = async (sessionId) => {
    const { data } = await http.get(`/sessions/${sessionId}/tests/plan`);
    return data;
};
export const createTestPlan = async (sessionId, body) => {
    const { data } = await http.post(`/sessions/${sessionId}/tests/plan`, body);
    return data;
};
export const approveTestPlan = async (sessionId, body) => {
    const { data } = await http.post(`/sessions/${sessionId}/tests/plan/${body.plan_id}/approve`, body);
    return data;
};
export const runTests = async (sessionId, planId) => {
    await http.post(`/sessions/${sessionId}/tests/plan/${planId}/run`);
};
export const refinePlan = async (sessionId, planId, feedback) => {
    const { data } = await http.post(`/sessions/${sessionId}/tests/plan/${planId}/refine`, { feedback });
    return data;
};
export const getTestResults = async (sessionId) => {
    const { data } = await http.get(`/sessions/${sessionId}/tests/results`);
    return data;
};
// ── Verification ──────────────────────────────────────────────────────────
export const getVerificationReport = async (sessionId) => {
    const { data } = await http.get(`/sessions/${sessionId}/verification`);
    return data;
};
// ── FirstPR ───────────────────────────────────────────────────────────────
export const getStarterTasks = async (sessionId) => {
    const { data } = await http.get(`/sessions/${sessionId}/firstpr/tasks`);
    return data;
};
