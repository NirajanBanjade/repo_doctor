import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getSession,
  createSession,
  triggerXRay,
  getXRayGraph,
} from "@/api/client";
import { useSessionContext } from "@/context/SessionContext";
import type { CreateSessionRequest } from "@/types";

export function useSession(sessionId: string | null) {
  return useQuery({
    queryKey: ["session", sessionId],
    queryFn: () => getSession(sessionId!),
    enabled: !!sessionId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      const running =
        status === "importing" ||
        status === "xray_running" ||
        status === "environment_running" ||
        status === "impact_running" ||
        status === "tests_running";
      return running ? 2000 : false;
    },
  });
}

export function useCreateSession() {
  const { setSession } = useSessionContext();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: CreateSessionRequest) => createSession(body),
    onSuccess: (session) => {
      setSession(session);
      qc.setQueryData(["session", session.session_id], session);
    },
  });
}

export function useTriggerXRay(sessionId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => triggerXRay(sessionId),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["session", sessionId] });
      void qc.invalidateQueries({ queryKey: ["xray", sessionId] });
    },
  });
}

export function useXRayGraph(sessionId: string | null) {
  return useQuery({
    queryKey: ["xray", sessionId],
    queryFn: () => getXRayGraph(sessionId!),
    enabled: !!sessionId,
  });
}
